"""
config.py – Quản lý tập trung toàn bộ tham số hệ thống.
"""

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
TRAIN_EPOCHS: int = 3
TRAIN_BATCH_SIZE: int = 16
EVAL_BATCH_SIZE: int = 32
TRAIN_WARMUP_STEPS: int = 100
TRAIN_EVAL_STEPS: int = 100

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
