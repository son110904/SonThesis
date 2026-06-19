"""
config.py – Quản lý tập trung toàn bộ tham số hệ thống.
"""

import os
from pathlib import Path

# ── Đường dẫn gốc ──────────────────────────────────────────────────────────
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

# Tự nạp biến môi trường từ .env (OPENAI_API_KEY, …) nếu file tồn tại.
# Không ghi đè biến đã set sẵn trong shell (override=False).
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env", override=False)
except ImportError:
    pass
DATA_DIR: Path = ROOT_DIR / "data"
MODELS_DIR: Path = ROOT_DIR / "models"
OCCUPATION_PROFILES_DIR: Path = DATA_DIR / "occupation_profiles"

# ── File dữ liệu ────────────────────────────────────────────────────────────
JD_FILE: Path = DATA_DIR / "VietJobs JD.csv"
RESUME_FIT_FILE: Path = DATA_DIR / "job_resume_fit.csv"

# ── Mô hình embedding ───────────────────────────────────────────────────────
EMBEDDING_MODEL_NAME: str = "Alibaba-NLP/gte-multilingual-base"
FINE_TUNED_MODEL_DIR: Path = MODELS_DIR / "gte_multilingual_resume_match"

# ── Tham số huấn luyện ──────────────────────────────────────────────────────
# Dataset ~2.4K dòng (≈2.1K train). Với batch=16 → ~134 step/epoch.
#   epochs=3  → ~402 step tổng.
#   eval/save mỗi 40 step → ~10 mốc đánh giá ⇒ load_best_model_at_end thực sự có
#     checkpoint để chọn (params cũ eval_steps=150 > tổng step nên KHÔNG bao giờ
#     eval/checkpoint trong lúc train — best-model selection vô nghĩa).
#   warmup=40 ≈ 10% tổng step (cũ 50 trên 134 step ≈ 37% — quá cao).
TRAIN_EPOCHS: int = 3
TRAIN_BATCH_SIZE: int = 16
EVAL_BATCH_SIZE: int = 32
TRAIN_WARMUP_STEPS: int = 40
TRAIN_EVAL_STEPS: int = 40
# fp32 trên CPU dễ diverge nếu lr cao; gte-multilingual fine-tune hợp lr nhỏ.
TRAIN_LEARNING_RATE: float = 2e-5
# max_seq_length khi train. 512 fp32 + batch 16 lấp gần kín 8GB VRAM của RTX 4060
# → driver tràn sang shared memory (RAM) ⇒ ~45s/step. Hạ xuống 256: attention giảm
# ~4× bộ nhớ, vẫn giữ phần đầu CV/JD (nơi chứa hầu hết tín hiệu match) ⇒ vừa VRAM,
# nhanh hơn nhiều. Dataset đã truncate theo ký tự nên tokenizer cắt 256 token là đủ.
TRAIN_MAX_SEQ_LENGTH: int = 256
# Mixed precision khi train trên GPU. bf16 (KHÔNG fp16): cùng dải mũ như fp32 nên
# không tràn/NaN như fp16, lại dùng tensor core của RTX 4060 ⇒ ~2-4× nhanh và giảm
# nửa bộ nhớ activation → tránh tràn VRAM 8GB sang shared memory (RAM). Lưu ý: NaN
# từng gặp là trên build PyTorch CPU (py3.14), KHÔNG phải CUDA thật ở đây; vẫn có
# guard chặn lưu model NaN nên an toàn. Đặt False để quay lại fp32 nếu cần.
TRAIN_BF16: bool = True

# ── Tham số Skill Weight ────────────────────────────────────────────────────
ALPHA: float = 0.6          # trọng số frequency
BETA: float = 0.4           # trọng số TF-IDF
CORE_SKILL_THRESHOLD: float = 0.5   # weight >= threshold → core_skill

# ── Cột văn bản trong VietJobs_JD.csv ──────────────────────────────────────
JD_TEXT_COLS: list[str] = ["description", "requirements_text", "technical_skills", "soft_skills"]
JD_CATEGORY_COL: str = "category"
JD_TITLE_COL: str = "job_title"

# ── Cột trong job_resume_fit.csv ────────────────────────────────────────────
RESUME_TEXT_COL: str = "resume_text"
JOB_TEXT_COL: str = "job_text"
MATCH_SCORE_COL: str = "ai_match_score"

# ══════════════════════════════════════════════════════════════════════════
# ONLINE PIPELINE
# ══════════════════════════════════════════════════════════════════════════

# ── Final Score: match_score = MATCH_ALPHA*semantic + MATCH_BETA*weighted ──
# (khác ALPHA/BETA ở trên — kia là trọng số frequency vs tf-idf của skill weight)
MATCH_ALPHA: float = 0.5    # trọng số semantic similarity
MATCH_BETA: float = 0.5     # trọng số weighted skill score

# ── LLM (AI Recommendation + trích experience/projects/education) ───────────
# Key đọc từ biến môi trường OPENAI_API_KEY. Thiếu key → degrade graceful.
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_TIMEOUT_SECONDS: float = 60.0
LLM_MAX_RETRIES: int = 2

# ── Text extraction giới hạn ────────────────────────────────────────────────
MAX_CV_CHARS: int = 20000   # cắt CV quá dài trước khi xử lý

# ── Database (SQLite) ───────────────────────────────────────────────────────
DB_PATH: Path = ROOT_DIR / "data" / "app.db"

# ── API ─────────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
