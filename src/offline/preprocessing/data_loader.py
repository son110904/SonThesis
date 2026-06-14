"""
data_loader.py – Đọc tất cả dataset trong thư mục data/.

Chức năng:
  - Tải VietJobs_JD.csv (Job Description chính)
  - Tải job_resume_fit.csv (dataset huấn luyện)
  - Loại bỏ các hàng thiếu dữ liệu ở các cột quan trọng
  - Trả về DataFrame thô chưa qua text cleaning
"""

import logging
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.config import (
    JD_FILE,
    RESUME_FIT_FILE,
    JD_TEXT_COLS,
    JD_CATEGORY_COL,
    JD_TITLE_COL,
    RESUME_TEXT_COL,
    JOB_TEXT_COL,
    MATCH_SCORE_COL,
)

logger = logging.getLogger(__name__)


def load_jd_dataset(path: Path = JD_FILE) -> pd.DataFrame:
    """
    Tải VietJobs_JD.csv.

    Args:
        path: Đường dẫn đến file CSV.

    Returns:
        DataFrame thô với các hàng thiếu cột quan trọng đã được loại bỏ.
    """
    logger.info(f"Đang tải JD dataset từ: {path}")
    df = pd.read_csv(path, low_memory=False)
    initial_rows = len(df)

    # Các cột bắt buộc phải có
    required_cols = [JD_CATEGORY_COL, JD_TITLE_COL, "description"]
    df = df.dropna(subset=required_cols)

    # Loại bỏ các hàng mà cả description lẫn requirements_text đều rỗng
    text_mask = df["description"].str.strip().eq("") & df["requirements_text"].fillna("").str.strip().eq("")
    df = df[~text_mask].reset_index(drop=True)

    dropped = initial_rows - len(df)
    logger.info(f"JD dataset: {initial_rows} hàng → {len(df)} hàng (đã loại {dropped} hàng thiếu dữ liệu)")
    return df


def load_resume_fit_dataset(path: Path = RESUME_FIT_FILE) -> pd.DataFrame:
    """
    Tải job_resume_fit.csv (dùng cho huấn luyện).

    Args:
        path: Đường dẫn đến file CSV.

    Returns:
        DataFrame thô với các hàng thiếu cột quan trọng đã được loại bỏ.
    """
    logger.info(f"Đang tải Resume-Fit dataset từ: {path}")
    df = pd.read_csv(path, low_memory=False)
    initial_rows = len(df)

    required_cols = [RESUME_TEXT_COL, JOB_TEXT_COL, MATCH_SCORE_COL]
    df = df.dropna(subset=required_cols)

    # Loại bỏ điểm số nằm ngoài phạm vi [0, 100]
    df = df[df[MATCH_SCORE_COL].between(0, 100)].reset_index(drop=True)

    dropped = initial_rows - len(df)
    logger.info(
        f"Resume-Fit dataset: {initial_rows} hàng → {len(df)} hàng (đã loại {dropped} hàng thiếu/lỗi dữ liệu)"
    )
    return df


def load_all_datasets() -> dict[str, pd.DataFrame]:
    """
    Tải toàn bộ dataset cần thiết.

    Returns:
        Dict với keys 'jd' và 'resume_fit'.
    """
    return {
        "jd": load_jd_dataset(),
        "resume_fit": load_resume_fit_dataset(),
    }


# ── CLI test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    datasets = load_all_datasets()

    print("\n=== JD Dataset ===")
    df_jd = datasets["jd"]
    print(f"Shape: {df_jd.shape}")
    print(f"Columns: {list(df_jd.columns)}")
    print(f"Categories ({df_jd['category'].nunique()} unique):")
    print(df_jd["category"].value_counts().head(10).to_string())

    print("\n=== Resume-Fit Dataset ===")
    df_rf = datasets["resume_fit"]
    print(f"Shape: {df_rf.shape}")
    print(f"ai_match_score – min: {df_rf['ai_match_score'].min():.2f}, "
          f"max: {df_rf['ai_match_score'].max():.2f}, "
          f"mean: {df_rf['ai_match_score'].mean():.2f}")
