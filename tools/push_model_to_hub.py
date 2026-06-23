"""
push_model_to_hub.py – Đẩy model fine-tuned local lên HuggingFace Hub.

Mục đích: khi deploy (HF Spaces) thư mục models/ không có (gitignore, quá lớn).
Đẩy model lên Hub rồi đặt biến môi trường FINETUNED_MODEL_REPO=<repo_id> để runtime
nạp đúng model fine-tuned → occupation embeddings (sinh bằng fine-tuned) vẫn khớp
không gian vector.

Cách dùng:
    # 1. Đăng nhập HuggingFace (1 lần)
    huggingface-cli login          # hoặc: export HF_TOKEN=hf_xxx

    # 2. Đẩy model
    python tools/push_model_to_hub.py <your-username>/gte-resume-match [--private]

    # 3. Trong Space settings → Variables, đặt:
    #       FINETUNED_MODEL_REPO = <your-username>/gte-resume-match
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import FINE_TUNED_MODEL_DIR


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Cách dùng: python tools/push_model_to_hub.py <repo_id> [--private]")
        sys.exit(1)

    repo_id = args[0]
    private = "--private" in args

    if not FINE_TUNED_MODEL_DIR.exists():
        print(f"❌ Không tìm thấy model local tại: {FINE_TUNED_MODEL_DIR}")
        print("   Hãy train trước (python run_train_gpu.py) hoặc kiểm tra đường dẫn.")
        sys.exit(1)

    from sentence_transformers import SentenceTransformer

    print(f"→ Load model từ {FINE_TUNED_MODEL_DIR} ...")
    model = SentenceTransformer(
        str(FINE_TUNED_MODEL_DIR), trust_remote_code=True, local_files_only=True
    )

    print(f"→ Push lên Hub: {repo_id} (private={private}) ...")
    model.push_to_hub(repo_id, private=private)

    print("✓ Hoàn tất.")
    print(f"  Đặt trong Space settings → Variables:  FINETUNED_MODEL_REPO={repo_id}")


if __name__ == "__main__":
    main()
