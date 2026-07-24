"""
text_cleaner.py – Chuẩn hóa và làm sạch văn bản.

Chức năng:
  - Chuẩn hóa Unicode (NFC)
  - Loại bỏ ký tự đặc biệt, HTML tags, URL
  - Chuẩn hóa khoảng trắng
  - Chuẩn hóa tên kỹ năng (skill alias mapping)
  - Parse cột dạng list ["A","B"] trước khi làm sạch
  - Tạo full_text từ free-text + list columns
"""

import ast
import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.config import RESUME_TEXT_COL, JOB_TEXT_COL

logger = logging.getLogger(__name__)

# Cột free text (clean bình thường)
FREE_TEXT_COLS = ["description", "requirements_text"]
# Cột dạng Python list repr (parse trước, clean từng item)
LIST_COLS = ["technical_skills", "soft_skills"]

# ── Bảng alias chuẩn hóa tên kỹ năng ────────────────────────────────────────
SKILL_ALIASES: dict[str, str] = {
    r"\bpython\s*3?\b": "Python",
    r"\bpython\s*2\b": "Python",
    r"\bjavascript\b": "JavaScript",
    r"\bjs\b": "JavaScript",
    r"\btypescript\b": "TypeScript",
    r"\bts\b": "TypeScript",
    r"\bnode\.?js\b": "Node.js",
    r"\breact\.?js\b": "React.js",
    r"\bvue\.?js\b": "Vue.js",
    r"\bangular\.?js\b": "Angular",
    r"\bpostgre(?:s|sql)?\b": "PostgreSQL",
    r"\bmysql\b": "MySQL",
    r"\bmongo(?:db)?\b": "MongoDB",
    r"\bms\s*sql\b": "SQL Server",
    r"\bsql\s*server\b": "SQL Server",
    r"\brest\s*api\b": "REST API",
    r"\brestful\b": "REST API",
    r"\bgit\s*hub\b": "GitHub",
    r"\bgit\s*lab\b": "GitLab",
    r"\bci[\/\-]?cd\b": "CI/CD",
    r"\bdocker\b": "Docker",
    r"\bkubernete?s\b": "Kubernetes",
    r"\bk8s\b": "Kubernetes",
    r"\baws\b": "AWS",
    r"\bamazon\s+web\s+services\b": "AWS",
    r"\bgoogle\s+cloud\b": "Google Cloud",
    r"\bgcp\b": "Google Cloud",
    r"\bmicrosoft\s+azure\b": "Azure",
    r"\btensorflow\b": "TensorFlow",
    r"\bpytorch\b": "PyTorch",
    r"\bscikit[\s\-]?learn\b": "scikit-learn",
    r"\bpandas\b": "Pandas",
    r"\bnumpy\b": "NumPy",
    r"\bfastapi\b": "FastAPI",
    r"\bdjango\b": "Django",
    r"\bflask\b": "Flask",
    r"\bspring\s*boot\b": "Spring Boot",
    r"\bjava\s*ee\b": "Java EE",
    r"\bc\+\+\b": "C++",
    r"\bc#\b": "C#",
    r"\b\.net\b": ".NET",
    r"\bms\s*excel\b": "Microsoft Excel",
    r"\bpower\s*bi\b": "Power BI",
    r"\btableau\b": "Tableau",
    r"\bsap\b": "SAP",
    r"\bscrum\b": "Scrum",
    r"\bagile\b": "Agile",
    r"\blinux\b": "Linux",
    r"\bwindows\s+server\b": "Windows Server",
    r"\bnlp\b": "NLP",
    r"\bnatural\s+language\s+processing\b": "NLP",
    r"\bmachine\s+learning\b": "Machine Learning",
    r"\bdeep\s+learning\b": "Deep Learning",
    r"\bphp\b": "PHP",
    r"\bgoland\b": "Go",
    r"\bgolang\b": "Go",
    r"\brust\b": "Rust",
    r"\bswift\b": "Swift",
    r"\bkotlin\b": "Kotlin",
    r"\bmatlab\b": "MATLAB",
    r"\bscala\b": "Scala",
    r"\bhadoop\b": "Hadoop",
    r"\bapache\s+spark\b": "Apache Spark",
    r"\belasticsearch\b": "Elasticsearch",
    r"\bredis\b": "Redis",
    r"\bkafka\b": "Apache Kafka",
    r"\bairflow\b": "Apache Airflow",
    r"\bjira\b": "Jira",
    r"\bconfluence\b": "Confluence",
    r"\bfigma\b": "Figma",
    r"\bphotoshop\b": "Photoshop",
    r"\billustrator\b": "Illustrator",
    r"\bautocad\b": "AutoCAD",
    r"\bsketchup\b": "SketchUp",
    r"\bgraphql\b": "GraphQL",
    r"\bmicroservices\b": "Microservices",
}

_COMPILED_ALIASES: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in SKILL_ALIASES.items()
]


# ── Các hàm làm sạch đơn lẻ ──────────────────────────────────────────────────

def normalize_unicode(text: str) -> str:
    """Chuẩn hóa Unicode về dạng NFC."""
    return unicodedata.normalize("NFC", text)


def remove_html_tags(text: str) -> str:
    """Xóa các HTML tag."""
    return re.sub(r"<[^>]+>", " ", text)


def remove_urls(text: str) -> str:
    """Xóa URL và email."""
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+\.\S+", " ", text)
    return text


def remove_special_characters(text: str) -> str:
    """
    Giữ lại chữ cái (Latin + Unicode), số, và ký hiệu kỹ thuật thông dụng.
    Loại bỏ các ký tự đặc biệt không cần thiết.
    """
    text = re.sub(r"[^\w\s\+\#\/\.\-\,\;\:\!\?\(\)\[\]]", " ", text, flags=re.UNICODE)
    return text


def normalize_whitespace(text: str) -> str:
    """Chuẩn hóa khoảng trắng: nhiều space/tab → một space; giữ newline."""
    text = re.sub(r"[\t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def normalize_skill_names(text: str) -> str:
    """
    Chuẩn hóa tên kỹ năng theo bảng SKILL_ALIASES.
    Ví dụ: 'nodejs' → 'Node.js', 'kubernetes' → 'Kubernetes'
    """
    for pattern, replacement in _COMPILED_ALIASES:
        text = pattern.sub(replacement, text)
    return text


def clean_text(text: Optional[str]) -> str:
    """
    Pipeline làm sạch văn bản đầy đủ.

    Args:
        text: Chuỗi văn bản đầu vào (hoặc None).

    Returns:
        Chuỗi đã được làm sạch, giữ newline để tách responsibilities.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    text = normalize_unicode(text)
    text = remove_html_tags(text)
    text = remove_urls(text)
    text = normalize_skill_names(text)
    text = remove_special_characters(text)
    text = normalize_whitespace(text)
    return text


def parse_list_column(value: Optional[str]) -> list[str]:
    """
    Parse cột dạng "['A', 'B', 'C']" → ['A', 'B', 'C'].
    Nếu không phải list thì trả về [value].
    """
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except (ValueError, SyntaxError):
        pass
    return [value.strip()] if value.strip() else []


def clean_list_column(value: Optional[str]) -> list[str]:
    """
    Parse cột list rồi clean từng phần tử.

    Returns:
        List[str] mỗi item đã được làm sạch, loại bỏ item rỗng.
    """
    raw_items = parse_list_column(value)
    cleaned = [clean_text(item) for item in raw_items]
    return [item for item in cleaned if item]


# ── DataFrame-level cleaning ──────────────────────────────────────────────────

def clean_jd_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Làm sạch toàn bộ DataFrame JD.

    Chiến lược:
      - Cột FREE_TEXT_COLS (description, requirements_text): clean_text bình thường.
      - Cột LIST_COLS (technical_skills, soft_skills): parse list → clean từng item
        → lưu vào cột mới "<col>_parsed" (kiểu List[str]).
      - Tạo cột 'full_text': ghép free-text + join(list items).

    Args:
        df: DataFrame JD thô từ data_loader.

    Returns:
        DataFrame đã làm sạch, có thêm cột *_parsed và full_text.
    """
    logger.info(f"Đang làm sạch JD DataFrame ({len(df)} hàng)...")
    df = df.copy()

    # --- Cột free text ---
    for col in FREE_TEXT_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("").apply(clean_text)
            logger.debug(f"  Đã làm sạch cột text: {col}")

    # --- Cột list: parse + clean từng item, lưu vào cột _parsed ---
    for col in LIST_COLS:
        if col in df.columns:
            parsed_col = col + "_parsed"
            df[parsed_col] = df[col].apply(clean_list_column)
            logger.debug(f"  Đã parse & làm sạch cột list: {col} → {parsed_col}")

    # --- Tạo full_text ---
    def _build_full_text(row: pd.Series) -> str:
        parts: list[str] = []
        for col in FREE_TEXT_COLS:
            if col in df.columns and row[col]:
                parts.append(row[col])
        for col in LIST_COLS:
            parsed_col = col + "_parsed"
            if parsed_col in df.columns and row[parsed_col]:
                parts.append(", ".join(row[parsed_col]))
        return "\n".join(parts)

    df["full_text"] = df.apply(_build_full_text, axis=1)

    # Loại bỏ hàng có full_text rỗng
    before = len(df)
    df = df[df["full_text"].str.strip().ne("")].reset_index(drop=True)
    logger.info(f"Sau làm sạch JD: {before} → {len(df)} hàng")
    return df


def clean_resume_fit_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Làm sạch toàn bộ DataFrame Resume-Fit.

    Args:
        df: DataFrame Resume-Fit thô từ data_loader.

    Returns:
        DataFrame đã làm sạch.
    """
    logger.info(f"Đang làm sạch Resume-Fit DataFrame ({len(df)} hàng)...")
    df = df.copy()

    for col in [RESUME_TEXT_COL, JOB_TEXT_COL]:
        if col in df.columns:
            df[col] = df[col].fillna("").apply(clean_text)

    before = len(df)
    mask = (
        df[RESUME_TEXT_COL].str.strip().ne("") &
        df[JOB_TEXT_COL].str.strip().ne("")
    )
    df = df[mask].reset_index(drop=True)
    logger.info(f"Sau làm sạch Resume-Fit: {before} → {len(df)} hàng")
    return df


# ── Data Summary Display ────────────────────────────────────────────────────

def display_data_summary(df: pd.DataFrame, dataset_name: str = "JD Dataset") -> None:
    """
    Hiển thị bảng thống kê dữ liệu sau khi làm sạch.

    Args:
        df: DataFrame đã được làm sạch.
        dataset_name: Tên dataset để hiển thị.
    """
    print("\n" + "=" * 70)
    print(f"📊 DATA SUMMARY: {dataset_name}")
    print("=" * 70)

    # 1. Overall stats
    print(f"\n📌 Total Records: {len(df):,}")
    print(f"📌 Total Columns: {len(df.columns)}")

    # 2. Category distribution (nếu có)
    if "category" in df.columns:
        print("\n📂 Category Distribution:")
        cat_counts = df["category"].value_counts()
        cat_df = pd.DataFrame({
            "Category": cat_counts.index,
            "Count": cat_counts.values,
            "Percentage": (cat_counts.values / len(df) * 100).round(1)
        })
        print(cat_df.to_string(index=False))

    # 3. Skills statistics
    print("\n🛠️ Skills Statistics:")
    for col in ["technical_skills_parsed", "soft_skills_parsed"]:
        if col in df.columns:
            all_skills = df[col].explode().dropna().tolist()
            unique_skills = set(all_skills)
            skill_name = col.replace("_parsed", "").replace("_", " ").title()
            print(f"  • {skill_name}:")
            print(f"    - Total skill mentions: {len(all_skills):,}")
            print(f"    - Unique skills: {len(unique_skills):,}")

            # Top 10 most common skills
            if all_skills:
                skill_freq = pd.Series(all_skills).value_counts().head(10)
                print(f"    - Top 10 skills:")
                for skill, count in skill_freq.items():
                    print(f"        {skill}: {count}")

    # 4. Text length statistics
    if "full_text" in df.columns:
        text_lengths = df["full_text"].str.len()
        print("\n📝 Full Text Length Statistics:")
        print(f"  • Min: {text_lengths.min():,} chars")
        print(f"  • Max: {text_lengths.max():,} chars")
        print(f"  • Mean: {text_lengths.mean():,.0f} chars")
        print(f"  • Median: {text_lengths.median():,.0f} chars")

    # 5. Sample cleaned records
    print("\n📋 Sample Cleaned Records:")
    sample_cols = ["category", "title"] if "title" in df.columns else ["category"]
    if "technical_skills_parsed" in df.columns:
        sample_cols.append("technical_skills_parsed")
    if "soft_skills_parsed" in df.columns:
        sample_cols.append("soft_skills_parsed")

    available_cols = [c for c in sample_cols if c in df.columns]
    if available_cols:
        sample_df = df[available_cols].head(3)
        for idx, row in sample_df.iterrows():
            print(f"\n  [Record {idx + 1}]")
            for col in available_cols:
                val = row[col]
                if isinstance(val, list):
                    val = ", ".join(val[:5]) + ("..." if len(val) > 5 else "")
                elif isinstance(val, str) and len(val) > 100:
                    val = val[:100] + "..."
                print(f"    {col}: {val}")

    print("\n" + "=" * 70)


def display_resume_fit_summary(df: pd.DataFrame) -> None:
    """
    Hiển thị bảng thống kê cho Resume-Fit dataset.

    Args:
        df: DataFrame đã được làm sạch.
    """
    print("\n" + "=" * 70)
    print("📊 DATA SUMMARY: Resume-Fit Dataset")
    print("=" * 70)

    print(f"\n📌 Total Records: {len(df):,}")
    print(f"📌 Total Columns: {len(df.columns)}")

    # Resume text length
    if "resume_text" in df.columns:
        resume_lengths = df["resume_text"].str.len()
        print("\n📝 Resume Text Length:")
        print(f"  • Min: {resume_lengths.min():,} chars")
        print(f"  • Max: {resume_lengths.max():,} chars")
        print(f"  • Mean: {resume_lengths.mean():,.0f} chars")
        print(f"  • Median: {resume_lengths.median():,.0f} chars")

    # Job text length
    if "job_text" in df.columns:
        job_lengths = df["job_text"].str.len()
        print("\n💼 Job Text Length:")
        print(f"  • Min: {job_lengths.min():,} chars")
        print(f"  • Max: {job_lengths.max():,} chars")
        print(f"  • Mean: {job_lengths.mean():,.0f} chars")
        print(f"  • Median: {job_lengths.median():,.0f} chars")

    # Match score distribution
    if "ai_match_score" in df.columns:
        scores = df["ai_match_score"]
        print("\n🎯 Match Score Distribution:")
        print(f"  • Min: {scores.min():.2f}")
        print(f"  • Max: {scores.max():.2f}")
        print(f"  • Mean: {scores.mean():.2f}")
        print(f"  • Median: {scores.median():.2f}")
        print(f"  • Std: {scores.std():.2f}")

    print("\n" + "=" * 70)


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    # Test clean_text
    samples = [
        "Yêu cầu: python3, nodejs, kubernetes (k8s), REST API, cicd pipeline",
        "<p>Experience with <b>Machine Learning</b> & Deep Learning</p>",
        "Visit https://example.com. Contact: hr@company.com",
        "Skills: C++, C#, .NET framework, golang, scikit-learn",
    ]
    print("=== Test clean_text ===")
    for s in samples:
        print(f"  IN : {s}")
        print(f"  OUT: {clean_text(s)}\n")

    # Test parse_list_column
    print("=== Test parse + clean list col ===")
    list_samples = [
        "['AutoCAD', 'MS Office', 'SketchUp (cơ bản)', 'PVSyst']",
        "['Python', 'Machine Learning', 'Docker', 'kubernetes']",
    ]
    for s in list_samples:
        print(f"  IN : {s}")
        print(f"  OUT: {clean_list_column(s)}\n")

    # Test với DataFrame
    from src.offline.preprocessing_step1.data_loader import load_jd_dataset, load_resume_fit_dataset

    print("=== Test clean_jd_dataframe ===")
    df_jd = load_jd_dataset()
    df_jd_clean = clean_jd_dataframe(df_jd)
    print(f"Shape: {df_jd_clean.shape}")
    print(f"Columns mới: {[c for c in df_jd_clean.columns if c not in df_jd.columns]}")

    # Hiển thị summary sau khi clean
    display_data_summary(df_jd_clean, "JD Dataset")

    # Xem IT sample
    it = df_jd_clean[df_jd_clean['category']=='công_nghệ_thông_tin_kỹ_thuật_số'].iloc[5]
    print(f"\ntechnical_skills_parsed: {it['technical_skills_parsed']}")
    print(f"soft_skills_parsed:      {it['soft_skills_parsed']}")
    print(f"full_text[:300]:\n{it['full_text'][:300]}")

    print("\n=== Test clean_resume_fit_dataframe ===")
    df_rf = load_resume_fit_dataset()
    df_rf_clean = clean_resume_fit_dataframe(df_rf)
    print(f"Shape: {df_rf_clean.shape}")
    print(f"Sample resume_text[:200]: {df_rf_clean[RESUME_TEXT_COL].iloc[0][:200]}")

    # Hiển thị summary cho Resume-Fit
    display_resume_fit_summary(df_rf_clean)
