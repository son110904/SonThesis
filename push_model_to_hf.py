"""
push_model_to_hf.py – Đẩy model fine-tuned lên Hugging Face Hub để deploy.

Vì sao cần: model `models/gte_multilingual_resume_match/` bị .gitignore (~1.2GB)
nên KHÔNG lên GitHub/Render. Đẩy lên HF Hub → lúc deploy, container tải về qua
env FINETUNED_MODEL_REPO (xem embedder.py: local dir > Hub repo > base model).

Chạy 1 LẦN ở LOCAL (nơi có sẵn model):
    1. pip install huggingface_hub
    2. huggingface-cli login          # dán Write token: huggingface.co/settings/tokens
    3. python push_model_to_hf.py

Sau đó trên Render đặt env:
    FINETUNED_MODEL_REPO = son110904/gte-resume-match
    HF_TOKEN            = <token>      # CHỈ cần nếu để repo private

Upload BỎ QUA thư mục checkpoints/ (~7GB artifact train, không cần cho inference).
"""

from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import HfApi

# ── Cấu hình ────────────────────────────────────────────────────────────────
REPO_ID = "son110904/gte-resume-match"   # <tài-khoản-HF>/<tên-repo>
PRIVATE = True                            # False = ai cũng tải được model của bạn
MODEL_DIR = Path(__file__).resolve().parent / "models" / "gte_multilingual_resume_match"

# Không upload: checkpoint train (nặng, vô dụng cho inference).
_IGNORE = ["checkpoints/*", "checkpoints/**", "checkpoints"]


def main() -> None:
    if not (MODEL_DIR / "model.safetensors").exists():
        raise SystemExit(
            f"❌ Không thấy model tại: {MODEL_DIR}\n"
            f"   Hãy chắc chắn đã train xong (có model.safetensors)."
        )

    # Token: ưu tiên env HF_TOKEN, nếu không thì dùng cache từ `huggingface-cli login`.
    token = os.getenv("HF_TOKEN") or None
    api = HfApi(token=token)

    print(f"→ Tạo/kiểm tra repo: {REPO_ID} (private={PRIVATE})")
    api.create_repo(REPO_ID, repo_type="model", private=PRIVATE, exist_ok=True)

    print(f"→ Đang upload từ {MODEL_DIR} (bỏ checkpoints/ ~7GB)…")
    api.upload_folder(
        folder_path=str(MODEL_DIR),
        repo_id=REPO_ID,
        repo_type="model",
        ignore_patterns=_IGNORE,
        commit_message="Upload fine-tuned gte-multilingual resume-match model",
    )

    print("\n✅ XONG.")
    print(f"   Kiểm tra: https://huggingface.co/{REPO_ID}")
    print(f"   Render env → FINETUNED_MODEL_REPO = {REPO_ID}")
    if PRIVATE:
        print("   (repo private → nhớ thêm env HF_TOKEN = <token> trên Render)")


if __name__ == "__main__":
    main()
