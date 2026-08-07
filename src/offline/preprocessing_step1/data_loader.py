"""
data_loader.py – Đọc tất cả dataset trong thư mục data/.

Chức năng:
  - Tải VietJobs_JD.csv (Job Description chính)
  - Tải job_resume_fit.csv (dataset huấn luyện)
  - Loại bỏ các hàng thiếu dữ liệu ở các cột quan trọng
  - Trả về DataFrame thô chưa qua text cleaning
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.config import (
    JD_FILE,
    RESUME_FIT_FILE,
    JD_CATEGORY_COL,
    JD_TITLE_COL,
    JD_EXPERIENCE_COL,
    MAX_EXPERIENCE_MONTHS,
    RESUME_TEXT_COL,
    JOB_TEXT_COL,
    MATCH_SCORE_COL,
)

logger = logging.getLogger(__name__)

# Cột experience_required là văn bản tiếng Việt tự do ("1 năm", "6 tháng",
# "Không yêu cầu"...) nên phải quy đổi về số tháng mới so sánh được.
_EXP_PATTERNS: list[tuple[re.Pattern, float]] = [
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*năm", re.IGNORECASE), 12.0),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*tháng", re.IGNORECASE), 1.0),
]
# Các cách diễn đạt "không đòi hỏi kinh nghiệm" → quy về 0 tháng.
_NO_EXP = re.compile(r"không\s*yêu\s*cầu|không\s*cần|chưa\s*có\s*kinh\s*nghiệm", re.IGNORECASE)


def parse_experience_months(value) -> Optional[float]:
    """
    Quy đổi mô tả kinh nghiệm sang SỐ THÁNG.

    Args:
        value: Giá trị thô của cột experience_required.

    Returns:
        Số tháng, 0.0 nếu không yêu cầu kinh nghiệm, None nếu không đọc được
        (để nơi gọi tự quyết định giữ hay loại).
    """
    if not isinstance(value, str) or not value.strip():
        return None
    if _NO_EXP.search(value):
        return 0.0
    for pattern, factor in _EXP_PATTERNS:
        m = pattern.search(value)
        if m:
            return float(m.group(1).replace(",", ".")) * factor
    return None


def load_jd_dataset(
    path: Path = JD_FILE,
    max_experience_months: Optional[int] = MAX_EXPERIENCE_MONTHS,
) -> pd.DataFrame:
    """
    Tải VietJobs_JD.csv.

    Args:
        path: Đường dẫn đến file CSV.
        max_experience_months: Chỉ giữ JD yêu cầu kinh nghiệm ≤ ngưỡng này
            (tính bằng tháng). None → giữ toàn bộ. Mặc định lấy từ config.

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

    if max_experience_months is not None:
        df = _filter_by_experience(df, max_experience_months)
    return df


def _filter_by_experience(df: pd.DataFrame, max_months: int) -> pd.DataFrame:
    """Giữ lại JD yêu cầu kinh nghiệm ≤ max_months (JD không đọc được mức kinh
    nghiệm sẽ bị LOẠI, để cơ sở tri thức chỉ gồm tin chắc chắn ở mức đầu vào)."""
    if JD_EXPERIENCE_COL not in df.columns:
        logger.warning(
            f"Không có cột '{JD_EXPERIENCE_COL}' → bỏ qua bước lọc theo kinh nghiệm."
        )
        return df

    before = len(df)
    months = df[JD_EXPERIENCE_COL].apply(parse_experience_months)
    unparsed = int(months.isna().sum())
    df = df[months.notna() & (months <= max_months)].reset_index(drop=True)

    logger.info(
        f"Lọc kinh nghiệm ≤ {max_months} tháng (đối tượng: sinh viên mới ra trường): "
        f"{before} → {len(df)} JD "
        f"(loại {before - len(df)}, trong đó {unparsed} JD không đọc được mức kinh nghiệm)"
    )
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
