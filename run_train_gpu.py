"""
run_train_gpu.py – Launcher fine-tune trên GPU (Python 3.12 + torch cu124).

Vì sao cần file này thay vì gọi thẳng `python -m src.training.trainer`:

  • Train GPU phải chạy bằng interpreter Python 3.12 (có torch CUDA), KHÔNG phải
    3.14 (chỉ có torch CPU).
  • Trên build pythoncore-3.12 này, chuỗi import của transformers/sentence-transformers
    quá sâu → tràn stack luồng chính ("Windows fatal exception: stack overflow")
    ngay khi `from transformers import AutoModel`. Khắc phục: chạy TOÀN BỘ phần
    import + train trong một thread có stack lớn (128MB). Do đó mọi import nặng
    phải nằm BÊN TRONG hàm chạy ở thread, không để ở top-level.

Chạy:
    <python3.12> run_train_gpu.py            # dùng tham số mặc định trong config.py
"""

import os
import sys
import threading
import logging
from pathlib import Path

# stdout/stderr của Windows mặc định cp1252 → in '─', '❌', tiếng Việt sẽ ném
# UnicodeEncodeError (làm hỏng cả lần lưu metrics dù model đã train xong). Ép UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Chống phân mảnh bộ nhớ CUDA: cho phép allocator nới đoạn đã cấp thay vì giữ
# nhiều khối rời → tránh đẩy peak vượt VRAM 8GB rồi tràn sang shared memory (RAM),
# nguyên nhân khiến step chậm dần. Phải set TRƯỚC khi import torch.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# Stack lớn cho thread import/train. Mặc định luồng ~ vài MB → tràn khi chuỗi
# import của torch/transformers/sentence-transformers quá sâu. Chọn stack hợp lệ
# lớn nhất (Windows giới hạn ~ <256MB cho build này).
for _mb in (240, 224, 208, 192, 160, 128):
    try:
        threading.stack_size(_mb * 1024 * 1024)
        _STACK_MB = _mb
        break
    except ValueError:
        continue
else:
    _STACK_MB = None  # dùng mặc định

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("run_train_gpu")

_result: dict = {}


def _run() -> None:
    # Import nặng PHẢI ở trong thread stack-lớn này, và THEO ĐÚNG THỨ TỰ:
    # warm `transformers` trước → chuỗi import của sentence-transformers nông hơn,
    # tránh tràn stack (xem giải thích đầu file). Đảo thứ tự sẽ segfault.
    logger.info("Warm imports (stack=%s MB)…", _STACK_MB)
    from transformers import AutoModel, AutoTokenizer  # noqa: F401 — warm-up
    from sentence_transformers import SentenceTransformer  # noqa: F401 — warm-up
    import torch

    sys.path.insert(0, str(Path(__file__).resolve().parent))

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA không khả dụng trong interpreter này. Hãy chạy run_train_gpu.py "
            "bằng Python 3.12 có cài torch bản CUDA (torch.__version__ kết thúc bằng "
            f"+cuXXX). Hiện tại: torch {torch.__version__}, cpu-only."
        )

    logger.info(
        "GPU: %s | torch %s | VRAM %.1f GB",
        torch.cuda.get_device_name(0),
        torch.__version__,
        torch.cuda.get_device_properties(0).total_memory / 1024**3,
    )

    from src.training.trainer import train

    model = train()  # tham số lấy từ config.py (epochs/batch/lr/eval_steps…)
    _result["ok"] = True
    logger.info("Fine-tune hoàn tất, model đã lưu.")
    return model


def main() -> int:
    t = threading.Thread(target=_wrap, name="train-bigstack")
    t.start()
    t.join()
    if _result.get("ok"):
        print("\n✅ TRAIN_GPU_DONE")
        return 0
    print("\n❌ TRAIN_GPU_FAILED")
    err = _result.get("error")
    if err:
        print(err)
    return 1


def _wrap() -> None:
    import traceback
    try:
        _run()
    except BaseException as e:  # noqa: BLE001 — bắt cả để in trace từ thread
        _result["error"] = "".join(traceback.format_exception(e))
        logger.error("Train lỗi:\n%s", _result["error"])


if __name__ == "__main__":
    raise SystemExit(main())
