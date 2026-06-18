"""
extractor.py – Trích xuất skills, responsibilities từ Job Description.

Phương pháp:
  1. Khai thác cột structured technical_skills_parsed + soft_skills_parsed (ưu tiên cao nhất)
  2. Keyword Matching (Regex) trên full_text để bổ sung skill đặc thù

Skill lọc qua STOP_SKILLS: loại bỏ các kỹ năng quá chung (xuất hiện gần như mọi ngành).
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.config import JD_CATEGORY_COL

logger = logging.getLogger(__name__)


# ── Stop-skills: kỹ năng quá chung, xuất hiện trong mọi ngành ──────────────
# Dựa trên phân tích tần suất xuyên nghề (≥ 14/16 occupation)
STOP_SKILLS: set[str] = {
    # Kỹ năng mềm cực kỳ chung
    "giao tiếp", "làm việc nhóm", "làm việc độc lập", "chịu áp lực",
    "nhiệt tình", "chăm chỉ", "trung thực", "năng động", "chủ động",
    "cầu tiến", "ham học hỏi", "cẩn thận", "kiên nhẫn", "sáng tạo",
    "tự tin", "tỉ mỉ", "trách nhiệm", "nhanh nhẹn", "linh hoạt",
    "kỷ luật", "chịu khó", "vui vẻ", "hòa đồng", "thẳng thắn",
    "kiên trì", "tận tâm", "cởi mở", "chu đáo", "nghiêm túc",
    "tự giác", "cầu thị", "thân thiện", "quyết đoán",
    # Biến thể giao tiếp
    "kỹ năng giao tiếp", "giao tiếp tốt", "kỹ năng giao tiếp tốt",
    "khả năng giao tiếp", "khả năng giao tiếp tốt", "giao tiếp hiệu quả",
    "giao tiếp linh hoạt",
    # Biến thể teamwork
    "kỹ năng làm việc nhóm", "khả năng làm việc nhóm", "làm việc nhóm tốt",
    "làm việc nhóm hiệu quả", "teamwork", "làm việc theo nhóm",
    "làm việc nhóm hiệu quả", "có khả năng làm việc nhóm",
    # Biến thể độc lập
    "khả năng làm việc độc lập", "kỹ năng làm việc độc lập",
    "có khả năng làm việc độc lập", "làm việc độc lập và theo nhóm",
    "khả năng làm việc độc lập và theo nhóm",
    "khả năng làm việc độc lập và nhóm",
    "có khả năng làm việc độc lập và theo nhóm",
    "có khả năng làm việc độc lập và làm việc nhóm",
    # Biến thể áp lực
    "chịu áp lực công việc", "chịu được áp lực công việc",
    "chịu được áp lực", "chịu được áp lực cao", "chịu được áp lực cao trong công việc",
    "chịu áp lực tốt", "chịu được áp lực trong công việc",
    "khả năng chịu áp lực", "khả năng làm việc dưới áp lực",
    "khả năng làm việc dưới áp lực cao", "làm việc dưới áp lực",
    "chịu được áp lực doanh số",
    # Trách nhiệm
    "tinh thần trách nhiệm", "tinh thần trách nhiệm cao",
    "có tinh thần trách nhiệm", "có tinh thần trách nhiệm cao",
    "có trách nhiệm", "có trách nhiệm với công việc",
    "có trách nhiệm trong công việc", "trách nhiệm trong công việc",
    "trách nhiệm cao", "trách nhiệm cao trong công việc",
    "có trách nhiệm cao trong công việc",
    # Học hỏi
    "sẵn sàng học hỏi", "tinh thần học hỏi", "tinh thần ham học hỏi",
    "có tinh thần học hỏi", "có tinh thần cầu tiến", "tinh thần cầu tiến",
    "học hỏi nhanh", "khả năng học hỏi nhanh", "chịu khó học hỏi",
    # Quản lý thời gian / tổ chức
    "quản lý thời gian", "kỹ năng quản lý thời gian",
    "quản lý thời gian tốt", "quản lý thời gian hiệu quả",
    "sắp xếp công việc", "kỹ năng tổ chức", "kỹ năng tổ chức công việc",
    "tổ chức công việc", "kỹ năng lập kế hoạch", "kỹ năng lập kế hoạch và tổ chức",
    "lập kế hoạch",
    # Giải quyết vấn đề
    "giải quyết vấn đề", "kỹ năng giải quyết vấn đề", "xử lý vấn đề",
    "xử lý tình huống", "xử lý tình huống tốt", "xử lý tình huống linh hoạt",
    "kỹ năng xử lý tình huống", "khả năng xử lý tình huống",
    "khả năng giải quyết vấn đề", "phân tích và giải quyết vấn đề",
    "kỹ năng phân tích và giải quyết vấn đề",
    "problem-solving", "problem-solving skills",
    # Office phổ thông (không phải chuyên dụng)
    "word", "powerpoint", "excel", "ms office", "microsoft office",
    "tin học văn phòng", "tin học văn phòng cơ bản",
    "kỹ năng tin học văn phòng", "thành thạo tin học văn phòng",
    "thành thạo vi tính văn phòng", "vi tính văn phòng",
    "sử dụng thành thạo tin học văn phòng", "sử dụng thành thạo vi tính văn phòng",
    "sử dụng thành thạo word",
    "thành thạo word", "power point",
    "tin học văn phòng (word, excel, powerpoint)",
    "tin học văn phòng (word, excel)",
    "thành thạo tin học văn phòng (word, excel, powerpoint)",
    # Thái độ chung
    "thái độ tích cực", "thái độ tốt", "tác phong chuyên nghiệp",
    "tác phong làm việc chuyên nghiệp", "chuyên nghiệp",
    "tinh thần chủ động", "chủ động trong công việc",
    "có tinh thần chủ động", "tích cực",
    # Kỹ năng phổ thông khác
    "thuyết trình", "thuyết phục", "đàm phán", "lắng nghe",
    "kỹ năng thuyết trình", "kỹ năng thuyết phục", "kỹ năng đàm phán",
    "thuyết phục tốt", "thuyết phục khách hàng", "đàm phán tốt",
    "thương lượng", "khả năng đàm phán", "khả năng thuyết phục",
    "kỹ năng tổng hợp", "tổng hợp thông tin", "trình bày",
    "kỹ năng trình bày", "kỹ năng báo cáo", "báo cáo",
    "internet", "sử dụng máy tính",
    # Misc
    "sức khỏe tốt", "hoạt bát", "nhanh nhạy", "đáng tin cậy",
    "biết lắng nghe", "cần cù", "siêng năng", "khéo léo",
    "chi tiết", "chú ý đến chi tiết", "detail-oriented",
    "thật thà", "khệnh khạng", "vui vẻ", "thân thiện",
    "có tinh thần trách nhiệm cao trong công việc",
    "communication", "communication skills",
    "khả năng làm việc độc lập và làm việc nhóm",
    "khả năng làm việc theo nhóm",
}


# ── Danh sách kỹ năng keyword (kỹ năng đặc thù, có giá trị phân biệt ngành) ─
SKILL_PATTERNS: list[str] = [
    # Ngôn ngữ lập trình
    r"\bPython\b", r"\bJava\b", r"\bJavaScript\b", r"\bTypeScript\b",
    r"\bC\+\+\b", r"\bC#\b", r"\.NET\b", r"\bGo\b", r"\bRust\b",
    r"\bPHP\b", r"\bRuby\b", r"\bSwift\b", r"\bKotlin\b", r"\bScala\b",
    r"\bMATLAB\b", r"\bR\s+language\b",

    # Web Frameworks
    r"\bNode\.js\b", r"\bReact\.js\b", r"\bVue\.js\b", r"\bAngular\b",
    r"\bDjango\b", r"\bFlask\b", r"\bFastAPI\b", r"\bSpring Boot\b",
    r"\bLaravel\b", r"\bExpress\.js\b", r"\bNestJS\b",

    # Databases
    r"\bMySQL\b", r"\bPostgreSQL\b", r"\bMongoDB\b", r"\bSQL Server\b",
    r"\bOracle\b", r"\bRedis\b", r"\bElasticsearch\b", r"\bSQLite\b",
    r"\bCassandra\b", r"\bFirebase\b",

    # Cloud & DevOps
    r"\bAWS\b", r"\bAzure\b", r"\bGoogle Cloud\b",
    r"\bDocker\b", r"\bKubernetes\b", r"\bCI/CD\b", r"\bJenkins\b",
    r"\bTerraform\b", r"\bAnsible\b", r"\bGitHub Actions\b",

    # Data / ML / AI
    r"\bMachine Learning\b", r"\bDeep Learning\b", r"\bNLP\b",
    r"\bTensorFlow\b", r"\bPyTorch\b", r"\bscikit-learn\b",
    r"\bPandas\b", r"\bNumPy\b", r"\bApache Spark\b", r"\bHadoop\b",
    r"\bApache Kafka\b", r"\bApache Airflow\b",
    r"\bTableau\b", r"\bPower BI\b",

    # Tools & OS
    r"\bLinux\b", r"\bWindows Server\b", r"\bGit\b",
    r"\bGitHub\b", r"\bGitLab\b", r"\bJira\b", r"\bConfluence\b",
    r"\bFigma\b", r"\bAutoCAD\b", r"\bSketchUp\b",
    r"\bPhotoshop\b", r"\bIllustrator\b",

    # Methodologies & Architecture
    r"\bAgile\b", r"\bScrum\b", r"\bKanban\b", r"\bDevOps\b",
    r"\bREST API\b", r"\bGraphQL\b", r"\bMicroservices\b",
    r"\bSQL\b", r"\bNoSQL\b",

    # Kỹ thuật tiếng Việt – có giá trị phân biệt ngành
    r"Lập trình",
    r"Học máy", r"Trí tuệ nhân tạo",
    r"Xử lý ngôn ngữ tự nhiên",
    r"Điện toán đám mây",
    r"Bảo mật thông tin", r"An ninh mạng",
    r"Mạng máy tính", r"Hệ thống nhúng",
    r"Kiểm thử phần mềm", r"Kiểm thử tự động",
    r"Phân tích dữ liệu", r"Khai phá dữ liệu",
    r"Kế toán", r"Kiểm toán",
    r"Tài chính doanh nghiệp", r"Phân tích tài chính",
    r"Marketing kỹ thuật số", r"SEO", r"Google Ads", r"Facebook Ads",
    r"Thiết kế đồ họa", r"UI/UX",
    r"Quản lý chuỗi cung ứng", r"Logistics",
    r"Luật", r"Pháp chế",
    r"Tuyển dụng", r"C&B", r"HRBP",
    r"Quản lý sản xuất", r"Quản lý chất lượng", r"ISO",
    r"Kỹ thuật điện", r"Điện lực", r"Cơ khí", r"Tự động hóa công nghiệp",
    r"Kỹ thuật xây dựng", r"Quản lý xây dựng", r"Kiến trúc công trình", r"Quy hoạch đô thị",
    r"Nấu ăn", r"Pha chế", r"F&B",
    r"Giảng dạy", r"Phát triển chương trình đào tạo",
    r"Chăm sóc sức khỏe", r"Y tế",
    r"Nhập khẩu", r"Xuất khẩu",
    r"PLC", r"SCADA", r"AutoCAD Electrical",
    r"BIM", r"Revit", r"SketchUp",
    r"CSS", r"\bHTML\b", r"Webpack", r"Vite",
    r"Kotlin", r"Flutter", r"React Native",
    r"Unity", r"Game development",
    r"Blockchain", r"Smart contract", r"Solidity",
    r"SAP", r"Oracle ERP", r"ERP",
    r"HubSpot", r"Salesforce", r"CRM",
    r"Adobe Premiere", r"After Effects",
]

_COMPILED_SKILL_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in SKILL_PATTERNS
]

_RESP_SPLITTER = re.compile(
    r"[\n\r][-•*–\u2022]\s*"
    r"|[\n\r]\d+[.)]\s+"
    r"|[\n\r]{2,}"
)

_RESP_MARKER = re.compile(
    r"^(?:trách nhiệm|nhiệm vụ|mô tả công việc|công việc chính|"
    r"responsibilities|duties|job description|key responsibilities)[\s:]*$",
    re.IGNORECASE,
)


def _is_stop_skill(skill: str) -> bool:
    """Kiểm tra skill có nằm trong STOP_SKILLS không."""
    return skill.strip().lower() in STOP_SKILLS


def extract_skills_from_text(text: str) -> list[str]:
    """
    Trích xuất kỹ năng từ free text bằng keyword regex.

    Args:
        text: Văn bản JD đã làm sạch.

    Returns:
        List kỹ năng không trùng, theo thứ tự xuất hiện, đã lọc stop_skills.
    """
    found: list[str] = []
    seen: set[str] = set()
    for pattern in _COMPILED_SKILL_PATTERNS:
        m = pattern.search(text)
        if m:
            skill = m.group(0).strip()
            key = skill.lower()
            if key not in seen and not _is_stop_skill(skill):
                seen.add(key)
                found.append(skill)
    return found


def merge_skills(
    tech_list: list[str],
    soft_list: list[str],
    text_keywords: list[str],
) -> list[str]:
    """
    Hợp nhất skills từ 3 nguồn, ưu tiên structured, lọc stop_skills.

    Args:
        tech_list: Từ technical_skills_parsed.
        soft_list: Từ soft_skills_parsed.
        text_keywords: Từ keyword matching.

    Returns:
        List kỹ năng hợp nhất, không trùng, không chứa stop_skills.
    """
    merged: list[str] = []
    seen: set[str] = set()

    for skill in tech_list + soft_list + text_keywords:
        if not skill or len(skill.strip()) < 2:
            continue
        if _is_stop_skill(skill):
            continue
        key = skill.strip().lower()
        if key not in seen:
            seen.add(key)
            merged.append(skill.strip())
    return merged


def extract_responsibilities(description: str, requirements_text: str = "") -> list[str]:
    """
    Trích xuất danh sách responsibilities từ description.

    Args:
        description: Nội dung mô tả công việc đã làm sạch.
        requirements_text: Yêu cầu bổ sung (nếu description rỗng).

    Returns:
        List responsibilities, tối đa 20 mục.
    """
    source = description if description.strip() else requirements_text
    segments = _RESP_SPLITTER.split(source)

    result: list[str] = []
    seen: set[str] = set()

    for seg in segments:
        seg = seg.strip()
        if len(seg) >= 20 and not _RESP_MARKER.match(seg):
            dedup_key = seg.lower()[:80]
            if dedup_key not in seen:
                seen.add(dedup_key)
                result.append(seg)

    return result[:20]


def extract_from_row(row: pd.Series) -> dict:
    """
    Trích xuất thông tin từ một hàng DataFrame JD đã làm sạch.

    Args:
        row: Một hàng của df_clean (sau clean_jd_dataframe).

    Returns:
        {"occupation": str, "skills": List[str], "responsibilities": List[str]}
    """
    occupation = str(row.get(JD_CATEGORY_COL, "unknown"))
    full_text = str(row.get("full_text", ""))
    description = str(row.get("description", ""))
    requirements_text = str(row.get("requirements_text", ""))

    # Lấy skill từ cột parsed (đã clean, không cần parse lại)
    tech_list: list[str] = row.get("technical_skills_parsed") or []
    soft_list: list[str] = row.get("soft_skills_parsed") or []

    # Bổ sung từ keyword matching
    text_keywords = extract_skills_from_text(full_text)

    skills = merge_skills(tech_list, soft_list, text_keywords)
    responsibilities = extract_responsibilities(description, requirements_text)

    return {
        "occupation": occupation,
        "skills": skills,
        "responsibilities": responsibilities,
    }


def extract_all(df: pd.DataFrame) -> list[dict]:
    """
    Trích xuất thông tin từ toàn bộ DataFrame JD đã làm sạch.

    Args:
        df: DataFrame JD sau clean_jd_dataframe.

    Returns:
        List[dict] – một phần tử cho mỗi JD.
    """
    logger.info(f"Đang trích xuất skills & responsibilities từ {len(df)} JD...")
    results: list[dict] = []

    for idx, row in df.iterrows():
        try:
            results.append(extract_from_row(row))
        except Exception as e:
            logger.warning(f"Lỗi tại hàng {idx}: {e}")
            results.append({"occupation": "unknown", "skills": [], "responsibilities": []})

    total_skills = sum(len(r["skills"]) for r in results)
    logger.info(
        f"Hoàn tất trích xuất: {len(results)} JD, "
        f"trung bình {total_skills / max(len(results), 1):.1f} skills/JD"
    )
    return results


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    from src.offline.preprocessing_step1.data_loader import load_jd_dataset
    from src.offline.preprocessing_step1.text_cleaner import clean_jd_dataframe

    df_raw = load_jd_dataset()
    df_clean = clean_jd_dataframe(df_raw)
    results = extract_all(df_clean)

    skill_counts = [len(r["skills"]) for r in results]
    resp_counts  = [len(r["responsibilities"]) for r in results]
    no_skill = sum(1 for c in skill_counts if c == 0)

    print(f"\n=== Thống kê ===")
    print(f"  Tổng JD: {len(results)}")
    print(f"  Skills/JD – min:{min(skill_counts)} max:{max(skill_counts)} "
          f"avg:{sum(skill_counts)/len(skill_counts):.1f}")
    print(f"  JD không skill: {no_skill} ({no_skill/len(results)*100:.1f}%)")
    print(f"  Resps/JD  – min:{min(resp_counts)} max:{max(resp_counts)} "
          f"avg:{sum(resp_counts)/len(resp_counts):.1f}")

    for cat in ["công_nghệ", "tài_chính", "marketing"]:
        ex = next((r for r in results if cat in r["occupation"]), None)
        if ex:
            print(f"\n[{ex['occupation']}]")
            print(f"  skills ({len(ex['skills'])}): {ex['skills'][:10]}")
            print(f"  resps  ({len(ex['responsibilities'])}): {ex['responsibilities'][:1]}")
