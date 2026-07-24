"""
run_calibrate_gpu.py – Launcher chạy scripts/calibrate_skill_threshold.py trên Python 3.12.

Giống run_eval_gpu.py: chạy trong thread stack lớn để tránh stack overflow khi
import transformers/sentence-transformers trên build pythoncore-3.12.

⚠️ PHẢI chạy bằng Python 3.12 (có torch), KHÔNG dùng 3.14.

    <python3.12> run_calibrate_gpu.py [--finetuned-only]
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
    from scripts.calibrate_skill_threshold import main
    main()


def main() -> None:
    t = threading.Thread(target=_run, name="calibrate-bigstack")
    t.start()
    t.join()


if __name__ == "__main__":
    main()
