"""
config.py – Quản lý tập trung toàn bộ tham số hệ thống.
"""

import os
from pathlib import Path

# ── Đường dẫn gốc ──────────────────────────────────────────────────────────
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
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
TRAIN_EPOCHS: int = 2              # giảm từ 3
TRAIN_BATCH_SIZE: int = 32         # tăng từ 16 → xử lý nhanh hơn
EVAL_BATCH_SIZE: int = 64          # tăng từ 32
TRAIN_WARMUP_STEPS: int = 50       # giảm từ 100
TRAIN_EVAL_STEPS: int = 150        # tăng từ 100 → đánh giá ít hơn

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
