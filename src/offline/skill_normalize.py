"""
skill_normalize.py – Chuẩn hóa & gộp biến thể kỹ năng (canonicalization).

Lý do tồn tại (xử lý "Lỗ hổng chất lượng data"):
    Occupation Profile gộp skill từ cột `*_skills_parsed` (free-text do người đăng
    JD gõ) + keyword regex. Hệ quả là cùng một skill xuất hiện dưới nhiều biến thể:

        "REST API", "REST API API", "REST API APIs"   ← lỗi lặp đuôi
        "Node.js", "Node.JavaScript"                  ← lỗi thay thế chuỗi
        "erp", "erP", "ERP"                            ← lỗi hoa/thường
        "Kế toán", "kế toán", "Kế Toán"               ← hoa/thường tiếng Việt

    Mỗi biến thể là một entry riêng với trọng số riêng → vừa làm loãng trọng số,
    vừa khiến exact-match phía online trượt (ứng viên có "Node.js" không khớp
    "Node.JavaScript" trong profile).

Ba lớp chuẩn hóa, áp dụng theo thứ tự:
    1. ALIAS_MAP        – sửa lỗi chính tả / đồng nghĩa cứng (Node.JavaScript→Node.js).
    2. _collapse_suffix – gộp token đuôi lặp ("REST API APIs"→"REST API").
    3. Hợp nhất hoa/thường – gộp các biến thể cùng `.lower()`, chọn 1 display
       theo PREFERRED_DISPLAY (acronym chuẩn) hoặc theo tần suất xuất hiện trong
       corpus (data-driven, không phán đoán thủ công).

Module thuần (không phụ thuộc model), dùng được cả ở offline lẫn online.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Mapping, Optional

# ── Lớp 1: Alias cứng cho lỗi chính tả / đồng nghĩa ────────────────────────────
# Key đã lowercase + strip. Value là display chuẩn (giữ nguyên hoa/thường mong muốn).
ALIAS_MAP: dict[str, str] = {
    "node.javascript": "Node.js",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "reactjs": "React.js",
    "react js": "React.js",
    "react.javascript": "React.js",
    "vuejs": "Vue.js",
    "vue js": "Vue.js",
    "express.javascript": "Express.js",
    "expressjs": "Express.js",
    "rest api api": "REST API",
    "rest api apis": "REST API",
    "rest apis": "REST API",
    "restful api": "REST API",
    "restful apis": "REST API",
    "ci cd": "CI/CD",
    "ui ux": "UI/UX",
    "ux ui": "UI/UX",
    "ui/ux design": "UI/UX",
    "ms sql": "SQL Server",
    "ms sql server": "SQL Server",
    "postgres": "PostgreSQL",
    "k8s": "Kubernetes",
}

# ── Lớp 1b: Synonym song ngữ VI↔EN cho cùng một kỹ năng ────────────────────────
# Lý do (xử lý "Lỗ hổng 5" theo hướng ĐÁNG TIN CẬY): từ điển skill (regex) chứa
# cả biến thể tiếng Việt lẫn tiếng Anh của cùng khái niệm. CV tiếng Anh trích ra
# "Machine Learning", còn profile (JD tiếng Việt) lưu "Học máy" → exact-match
# trượt. Embedding-cosine KHÔNG tách bạch được cụm skill ngắn (synonym 0.59 còn
# cặp khác nghĩa lại 0.75 — không có ngưỡng nào phân tách), nên ta gộp bằng map
# tường minh: mọi biến thể → MỘT canonical (deterministic, không false positive).
# Key đã lowercase; value là canonical chuẩn.
SYNONYM_MAP: dict[str, str] = {
    "học máy": "Machine Learning",
    "machine learning": "Machine Learning",
    "học sâu": "Deep Learning",
    "deep learning": "Deep Learning",
    "trí tuệ nhân tạo": "Trí tuệ nhân tạo",
    "artificial intelligence": "Trí tuệ nhân tạo",
    "xử lý ngôn ngữ tự nhiên": "NLP",
    "natural language processing": "NLP",
    "điện toán đám mây": "Cloud Computing",
    "cloud computing": "Cloud Computing",
    "bảo mật thông tin": "Bảo mật thông tin",
    "information security": "Bảo mật thông tin",
    "an ninh mạng": "An ninh mạng",
    "network security": "An ninh mạng",
    "cyber security": "An ninh mạng",
    "cybersecurity": "An ninh mạng",
    "mạng máy tính": "Mạng máy tính",
    "computer network": "Mạng máy tính",
    "computer networking": "Mạng máy tính",
    "kiểm thử phần mềm": "Kiểm thử phần mềm",
    "software testing": "Kiểm thử phần mềm",
    "kiểm thử tự động": "Kiểm thử tự động",
    "automation testing": "Kiểm thử tự động",
    "automated testing": "Kiểm thử tự động",
    "phân tích dữ liệu": "Phân tích dữ liệu",
    "data analysis": "Phân tích dữ liệu",
    "data analytics": "Phân tích dữ liệu",
    "khai phá dữ liệu": "Khai phá dữ liệu",
    "data mining": "Khai phá dữ liệu",
    "lập trình": "Lập trình",
    "programming": "Lập trình",
    "coding": "Lập trình",
    "kế toán": "Kế toán",
    "accounting": "Kế toán",
    "kiểm toán": "Kiểm toán",
    "auditing": "Kiểm toán",
    "quản lý dự án": "Quản lý dự án",
    "project management": "Quản lý dự án",
    "quản lý chuỗi cung ứng": "Quản lý chuỗi cung ứng",
    "supply chain management": "Quản lý chuỗi cung ứng",
    "thiết kế đồ họa": "Thiết kế đồ họa",
    "graphic design": "Thiết kế đồ họa",
    "marketing kỹ thuật số": "Digital Marketing",
    "digital marketing": "Digital Marketing",
    "tuyển dụng": "Tuyển dụng",
    "recruitment": "Tuyển dụng",
    "quản lý chất lượng": "Quản lý chất lượng",
    "quality management": "Quản lý chất lượng",
    "quản lý sản xuất": "Quản lý sản xuất",
    "production management": "Quản lý sản xuất",
}

# ── Lớp 3: Display chuẩn cho các acronym / tên riêng (key đã lowercase) ─────────
# Dùng khi cùng `.lower()` có nhiều biến thể; PREFERRED_DISPLAY thắng tần suất.
PREFERRED_DISPLAY: dict[str, str] = {
    "erp": "ERP",
    "sql": "SQL",
    "nosql": "NoSQL",
    "html": "HTML",
    "css": "CSS",
    "php": "PHP",
    "aws": "AWS",
    "gcp": "GCP",
    "sap": "SAP",
    "crm": "CRM",
    "seo": "SEO",
    "sem": "SEM",
    "iso": "ISO",
    "plc": "PLC",
    "scada": "SCADA",
    "bim": "BIM",
    "nlp": "NLP",
    "api": "API",
    "rest api": "REST API",
    "ui/ux": "UI/UX",
    "ci/cd": "CI/CD",
    "sql server": "SQL Server",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    "node.js": "Node.js",
    "react.js": "React.js",
    "vue.js": "Vue.js",
    "c#": "C#",
    "c++": "C++",
    ".net": ".NET",
    "power bi": "Power BI",
    "github": "GitHub",
    "gitlab": "GitLab",
}

# Token đuôi coi là tương đương khi gộp lặp (số nhiều / biến thể).
_SUFFIX_EQUIV = {"api": "api", "apis": "api"}

_WS = re.compile(r"\s+")


def _basic_clean(skill: str) -> str:
    """Strip + gộp khoảng trắng thừa."""
    return _WS.sub(" ", skill.strip())


def _collapse_repeated_suffix(skill: str) -> str:
    """
    Gộp token đuôi bị lặp: "REST API API" / "REST API APIs" → "REST API".

    Chỉ gộp khi token cuối lặp lại token liền trước (so khớp qua _SUFFIX_EQUIV
    để 'api' == 'apis'), tránh đụng tới phần đầu chuỗi.
    """
    tokens = skill.split(" ")
    while len(tokens) >= 2:
        last = _SUFFIX_EQUIV.get(tokens[-1].lower(), tokens[-1].lower())
        prev = _SUFFIX_EQUIV.get(tokens[-2].lower(), tokens[-2].lower())
        if last == prev:
            tokens.pop()  # bỏ token đuôi lặp
        else:
            break
    return " ".join(tokens)


def canonicalize_skill(skill: str) -> str:
    """
    Chuẩn hóa 1 skill: alias → collapse suffix → preferred display.

    KHÔNG tự quyết hoa/thường cho biến thể không xác định (vd 'Kế toán' vs
    'kế toán'); việc đó để dedupe_weighted_skills() xử lý data-driven.

    Args:
        skill: Tên skill thô.

    Returns:
        Tên skill đã chuẩn hóa (giữ nguyên nếu không khớp luật nào).
    """
    s = _basic_clean(skill)
    if not s:
        return s

    low = s.lower()
    if low in ALIAS_MAP:
        return ALIAS_MAP[low]
    if low in SYNONYM_MAP:
        return SYNONYM_MAP[low]

    s = _collapse_repeated_suffix(s)
    low = s.lower()
    if low in ALIAS_MAP:
        return ALIAS_MAP[low]
    if low in SYNONYM_MAP:
        return SYNONYM_MAP[low]
    if low in PREFERRED_DISPLAY:
        return PREFERRED_DISPLAY[low]
    return s


def build_display_preference(skill_iterables: Iterable[Iterable[str]]) -> dict[str, str]:
    """
    Xây map `lower → display chuẩn` từ tần suất xuất hiện trong corpus.

    Với mỗi nhóm cùng `.lower()` (sau canonicalize), display được chọn theo:
        1. PREFERRED_DISPLAY nếu có (acronym/tên riêng chuẩn).
        2. Biến thể xuất hiện ở NHIỀU profile nhất (data-driven).
        3. Tie-break: ưu tiên có chữ in hoa đầu, rồi alphabet.

    Args:
        skill_iterables: Lặp các tập skill (vd: mỗi profile một tập key skill).
                         Mỗi tập chỉ tính 1 lần/biến thể (document frequency).

    Returns:
        Dict[lower → display].
    """
    variant_doc_count: dict[str, Counter] = {}
    for skills in skill_iterables:
        seen_in_doc: set[str] = set()
        for raw in skills:
            canon = canonicalize_skill(raw)
            low = canon.lower()
            if low in seen_in_doc:
                continue
            seen_in_doc.add(low)
            variant_doc_count.setdefault(low, Counter())[canon] += 1

    preference: dict[str, str] = {}
    for low, counter in variant_doc_count.items():
        if low in PREFERRED_DISPLAY:
            preference[low] = PREFERRED_DISPLAY[low]
            continue
        # Sắp theo (số profile giảm dần, có hoa đầu, alphabet) → lấy đầu.
        best = sorted(
            counter.items(),
            key=lambda kv: (-kv[1], 0 if kv[0][:1].isupper() else 1, kv[0]),
        )[0][0]
        preference[low] = best
    return preference


def dedupe_weighted_skills(
    weights: Mapping[str, float],
    display_preference: Optional[Mapping[str, str]] = None,
    merge: str = "max",
) -> dict[str, float]:
    """
    Chuẩn hóa + gộp các biến thể trong một dict skill→weight.

    Args:
        weights:            Dict skill (thô) → weight.
        display_preference: Map lower→display (từ build_display_preference).
                            Nếu None, tự suy từ chính dict này.
        merge:              Cách gộp weight khi trùng: "max" (mặc định) hoặc "sum".

    Returns:
        Dict skill (đã chuẩn hóa, không trùng) → weight, sắp giảm dần theo weight.
    """
    if display_preference is None:
        display_preference = build_display_preference([weights.keys()])

    merged: dict[str, float] = {}
    for raw, w in weights.items():
        canon = canonicalize_skill(raw)
        low = canon.lower()
        display = display_preference.get(low, canon)
        if display in merged:
            merged[display] = (
                max(merged[display], w) if merge == "max" else merged[display] + w
            )
        else:
            merged[display] = w

    if merge == "sum":  # sum có thể vượt 1 → clamp về [0,1]
        merged = {k: max(0.0, min(1.0, v)) for k, v in merged.items()}

    return dict(sorted(merged.items(), key=lambda kv: kv[1], reverse=True))


def dedupe_skill_list(
    skills: Iterable[str],
    display_preference: Optional[Mapping[str, str]] = None,
) -> list[str]:
    """Chuẩn hóa + loại trùng cho 1 list skill (giữ thứ tự xuất hiện đầu tiên)."""
    if display_preference is None:
        display_preference = build_display_preference([list(skills)])
    out: list[str] = []
    seen: set[str] = set()
    for raw in skills:
        canon = canonicalize_skill(raw)
        low = canon.lower()
        display = display_preference.get(low, canon)
        if low not in seen:
            seen.add(low)
            out.append(display)
    return out


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    samples = [
        "REST API", "REST API API", "REST API APIs",
        "Node.js", "Node.JavaScript",
        "erp", "erP", "ERP",
        "Kế toán", "kế toán", "Kế Toán",
        "reactjs", "React.js",
    ]
    print("canonicalize_skill:")
    for s in samples:
        print(f"  {s!r:25} → {canonicalize_skill(s)!r}")

    demo = {
        "REST API": 0.9, "REST API API": 0.4, "REST API APIs": 0.3,
        "Node.js": 0.7, "Node.JavaScript": 0.2,
        "erp": 0.5, "erP": 0.3, "ERP": 0.6,
    }
    print("\ndedupe_weighted_skills(merge='max'):")
    for k, v in dedupe_weighted_skills(demo).items():
        print(f"  {k:15} {v}")
