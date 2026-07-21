"""
run_eval_gpu.py – Launcher chạy scripts/eval_baselines.py trên Python 3.12.

Vì sao cần: giống run_train_gpu.py — import chain của transformers/sentence-
transformers quá sâu, tràn stack luồng chính trên build pythoncore-3.12 → segfault.
Chạy toàn bộ trong thread stack lớn.

⚠️ PHẢI chạy bằng Python 3.12 (có torch), KHÔNG dùng 3.14 (bug position_ids làm
hỏng embedding → điểm sai lệch, xem embedder._reset_position_ids).

    <python3.12> run_eval_gpu.py [--max-pairs N]
"""

import sys
import threading
from pathlib import Path

for _mb in (240, 224, 192, 160, 128):
    try:
        threading.stack_size(_mb * 1024 * 1024)
        break
    except ValueError:
        continue

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _run() -> None:
    from transformers import AutoModel  # noqa: F401 — warm import order
    from sentence_transformers import SentenceTransformer  # noqa: F401
    from scripts.eval_baselines import main
    main()


def main() -> None:
    t = threading.Thread(target=_run, name="eval-bigstack")
    t.start()
    t.join()


if __name__ == "__main__":
    main()
