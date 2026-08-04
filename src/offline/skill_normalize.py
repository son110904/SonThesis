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



# ── Skill BLACKLIST theo domain ─────────────────────────────────────────────────
# Blacklist ÁP DỤNG CHO TẤT CẢ ngành (skill không thuộc bất kỳ domain nào).
# Đây là skill "chung" xuất hiện ở mọi nơi do noise extraction, không đặc trưng domain.
# Áp dụng TRƯỚC khi dedupe, cho TẤT CẢ profile.
SKILL_BLACKLIST_ALL: set[str] = {
    "đam mê kiếm tiền",
    "nhiệt huyết",
    "nhiệt tình trong công việc",
    "khả năng tự học",
    "khả năng học hỏi",
    "tinh thần làm việc nhóm",
    "kỹ năng làm việc theo nhóm",
    "kỹ năng làm việc nhóm tốt",
    "phối hợp nhóm",
    "bền bỉ",
    "tư duy logic",
    "proactive attitude",
    "lãnh đạo",
    "tổ chức",
    "phản xạ tình huống",
    "phần mềm văn phòng",
    "sử dụng thành thạo các phần mềm office (word, excel, powerpoint)",
    "thành thạo excel",
    "vlookup",
    "countif",
    "sumif",
    "google sheet",
    "g-suite",
    "microsoft 365",
    "tìm kiếm khách hàng",
    "xây dựng và duy trì mối quan hệ khách hàng",
    "khả năng tư vấn khách hàng",
    "sử dụng crm",
    "đọc hiểu tài liệu bằng tiếng anh",
    "documentation skills",
    "tư duy chiến lược",
    "kỹ năng phân tích",
    "khả năng phân tích",
    "phân tích",
    "kỹ năng lắng nghe",
    "kỹ năng viết tài liệu",
}


# ── Skill BLACKLIST chỉ cho ngành IT / phần mềm ──────────────────────────────
# Những skill này thuộc domain KHÁC (cơ khí, sales, tài chính...) nên không liên
# quan khi đánh giá ứng viên IT/software. Chỉ áp dụng khi profile thuộc nhóm IT.
# Key: skill lowercase; Value: lý do.
SKILL_BLACKLIST_IT_ONLY: dict[str, str] = {
    # Cơ khí / gia công
    "cnc": "gia công cơ khí",
    "lập trình cnc": "gia công cơ khí",
    "máy cnc": "gia công cơ khí",
    "g-code": "gia công CNC",
    "mastercam": "gia công CNC",
    "cam": "máy tính hỗ trợ sản xuất (chuyên ngành cơ khí)",
    "phay": "gia công cơ khí",
    "tiện": "gia công cơ khí",
    "cơ khí": "ngành cơ khí",
    "gia công cơ khí": "ngành cơ khí",
    "hàn": "ngành hàn",
    "solidworks": "CAD cơ khí (SolidWorks ≠ software dev)",
    "autocad": "CAD cơ khí (AutoCAD ≠ software dev)",
    "nx": "CAD/CAM cơ khí",
    # Viễn thông hạ tầng
    "viễn thông": "hạ tầng viễn thông (≠ software)",
    "voice": "voip/viễn thông",
    "rf": "radio frequency engineering",
    # Tài chính / kế toán
    "kế toán": "ngành tài chính",
    "kiểm toán": "ngành tài chính",
    "tính lương": "ngành nhân sự/tài chính",
    # Sales / kinh doanh
    "chăm sóc khách hàng": "ngành dịch vụ (≠ dev)",
    "kỹ năng bán hàng": "ngành sales",
    "bán hàng b2b": "ngành sales",
    "kinh nghiệm sales b2b": "ngành sales",
    "kinh doanh phần mềm": "sales/pre-sales, không phải dev",
    "phát triển kinh doanh": "ngành kinh doanh",
    "telesales": "ngành telemarketing",
    "báo giá": "bán hàng/kế toán",
    "sourcing": "mua hàng/procurement",
    # Marketing
    "email marketing": "ngành marketing",
    "nghiên cứu thị trường": "ngành marketing",
    "phân tích thị trường": "ngành marketing",
    # HR / nhân sự
    "tuyển dụng": "ngành nhân sự",
    "kỹ năng đào tạo": "ngành nhân sự",
    # Y / giáo dục
    "y tế": "ngành y",
    "tương tác với trẻ em": "ngành giáo dục mầm non",
    "giảng dạy": "ngành giáo dục",
    # F&B / logistics
    "quản lý nhà hàng": "ngành f&b",
    "quản lý kho": "ngành logistics",
    "quản lý sản xuất": "ngành sản xuất",
    "kiểm kê": "ngành logistics/kho",
    # Xây dựng
    "bóc tách khối lượng": "ngành xây dựng",
    "đọc hiểu bản vẽ kỹ thuật": "ngành cơ khí/xây dựng",
    # Pháp lý
    "luật": "ngành pháp lý",
    # An toàn / HSE
    "an toàn lao động": "ngành an toàn",
    # Misc
    "vas": "noise/ví dụ không phải skill",
    "tiện ích": "chung chung",
    "cctv": "an ninh/vật lý",
    "quản lý tài sản": "ngành quản lý tài sản",
    "tư vấn": "ngành tư vấn (chung)",
    "quản lý chất lượng": "sản xuất/iso",
    # IT support/hardware (không phải software dev)
    "cài đặt máy tính": "it support/hardware",
    "sửa chữa thiết bị": "it support/hardware",
    "phần cứng máy tính": "it support/hardware",
    "phần cứng": "it support/hardware",
    "thiết bị ngoại vi": "it support",
    "nas": "storage (it ops)",
    "vmware": "virtualization (it ops)",
    "microsoft hyper-v": "virtualization (it ops)",
    "hyper-v": "virtualization it ops",
    "active directory": "it ops/ad (sysadmin, không phải dev)",
    "exchange": "mail server (it ops)",
    "quản lý hạ tầng mạng": "it ops networking",
    "quản lý mạng nội bộ kết nối data center": "it ops networking",
    "giám sát hệ thống": "it ops monitoring",
    "cài đặt cấu hình mail server": "it ops mail",
    "quản trị hệ điều hành server": "it ops server admin",
    "backup restore": "it ops",
    "bảo mật hệ thống": "it ops security (khác security engineer)",
    "san or storage systems": "it ops storage",
}


def is_blacklisted(skill: str, domain_key: str = "") -> bool:
    """
    Kiểm tra skill có bị blacklist không.

    Args:
        skill: Tên skill thô.
        domain_key: ASCII key của profile (vd "cong_nghe_thong_tin_ky_thuat_so").
                   Dùng để quyết định blacklist IT-only có áp dụng không.

    Returns:
        True nếu skill bị blacklist (loại bỏ khỏi profile).
    """
    low = skill.lower()
    # Luôn loại blacklist toàn ngành.
    if low in SKILL_BLACKLIST_ALL:
        return True
    # Blacklist IT-only chỉ áp dụng cho profile thuộc nhóm CNTT.
    if domain_key.startswith("cong_nghe_thong_tin_ky_thuat_so"):
        if low in SKILL_BLACKLIST_IT_ONLY:
            return True
    return False


# ── Lớp 0b: Skill con → Skill cha ─────────────────────────────────────────────
# Khi candidate có skill CỤ THỂ (Python, Java…) và nghề yêu cầu NHÓM (Lập trình),
# coi như match. Key: skill con (lowercase); Value: skill cha (canonical chuẩn).
PARENT_SKILL_MAP: dict[str, str] = {
    # Ngôn ngữ lập trình → Lập trình
    "python": "Lập trình",
    "java": "Lập trình",
    "javascript": "Lập trình",
    "typescript": "Lập trình",
    "c": "Lập trình",
    "c++": "Lập trình",
    "c#": "Lập trình",
    "go": "Lập trình",
    "rust": "Lập trình",
    "kotlin": "Lập trình",
    "swift": "Lập trình",
    "php": "Lập trình",
    "ruby": "Lập trình",
    "r": "Lập trình",
    "scala": "Lập trình",
    "perl": "Lập trình",
    "matlab": "Lập trình",
    "lua": "Lập trình",
    "objective-c": "Lập trình",
    "dart": "Lập trình",
    "elixir": "Lập trình",
    "clojure": "Lập trình",
    "haskell": "Lập trình",
    "f#": "Lập trình",
    # Scripting → Lập trình
    "bash": "Lập trình",
    "shell": "Lập trình",
    "powershell": "Lập trình",
    "perl": "Lập trình",
    "groovy": "Lập trình",
    "vba": "Lập trình",
    "batch": "Lập trình",
    "lua": "Lập trình",
    # Web development skills → Các kỹ năng web
    "html": "HTML/CSS",
    "css": "HTML/CSS",
    "sass": "HTML/CSS",
    "scss": "HTML/CSS",
    "less": "HTML/CSS",
    "tailwind": "HTML/CSS",
    "bootstrap": "HTML/CSS",
    "react.js": "Lập trình Web",
    "reactjs": "Lập trình Web",
    "vue.js": "Lập trình Web",
    "vuejs": "Lập trình Web",
    "angular": "Lập trình Web",
    "next.js": "Lập trình Web",
    "nuxt.js": "Lập trình Web",
    "svelte": "Lập trình Web",
    "jquery": "Lập trình Web",
    "ajax": "Lập trình Web",
    "rest api": "Lập trình Web",
    "graphql": "Lập trình Web",
    # Backend frameworks
    "node.js": "Lập trình Web",
    "express.js": "Lập trình Web",
    "fastapi": "Lập trình Web",
    "django": "Lập trình Web",
    "flask": "Lập trình Web",
    "spring": "Lập trình Web",
    "spring boot": "Lập trình Web",
    "laravel": "Lập trình Web",
    "rails": "Lập trình Web",
    "ruby on rails": "Lập trình Web",
    # Database
    "sql": "Cơ sở dữ liệu",
    "mysql": "Cơ sở dữ liệu",
    "postgresql": "Cơ sở dữ liệu",
    "postgres": "Cơ sở dữ liệu",
    "mongodb": "Cơ sở dữ liệu",
    "redis": "Cơ sở dữ liệu",
    "elasticsearch": "Cơ sở dữ liệu",
    "cassandra": "Cơ sở dữ liệu",
    "dynamodb": "Cơ sở dữ liệu",
    "mariadb": "Cơ sở dữ liệu",
    "oracle": "Cơ sở dữ liệu",
    "sqlite": "Cơ sở dữ liệu",
    # DevOps & Cloud
    "docker": "DevOps",
    "kubernetes": "DevOps",
    "k8s": "DevOps",
    "jenkins": "DevOps",
    "gitlab ci": "DevOps",
    "github actions": "DevOps",
    "ci/cd": "DevOps",
    "terraform": "DevOps",
    "ansible": "DevOps",
    "puppet": "DevOps",
    "chef": "DevOps",
    "aws": "Cloud Computing",
    "azure": "Cloud Computing",
    "gcp": "Cloud Computing",
    "google cloud": "Cloud Computing",
    "heroku": "Cloud Computing",
    "docker compose": "DevOps",
    # Data & AI
    "pandas": "Phân tích dữ liệu",
    "numpy": "Phân tích dữ liệu",
    "scipy": "Phân tích dữ liệu",
    "jupyter": "Phân tích dữ liệu",
    "tableau": "Phân tích dữ liệu",
    "power bi": "Phân tích dữ liệu",
    "powerbi": "Phân tích dữ liệu",
    "excel": "Phân tích dữ liệu",
    "tensorflow": "Machine Learning",
    "pytorch": "Machine Learning",
    "keras": "Machine Learning",
    "scikit-learn": "Machine Learning",
    "sklearn": "Machine Learning",
    "opencv": "Machine Learning",
    "spacy": "NLP",
    "nltk": "NLP",
    "hugging face": "NLP",
    "langchain": "NLP",
    # Tools & Platforms
    "git": "Quản lý mã nguồn",
    "github": "Quản lý mã nguồn",
    "gitlab": "Quản lý mã nguồn",
    "bitbucket": "Quản lý mã nguồn",
    "jira": "Quản lý dự án",
    "confluence": "Quản lý dự án",
    "trello": "Quản lý dự án",
    "slack": "Quản lý dự án",
    "figma": "Thiết kế",
    "sketch": "Thiết kế",
    "adobe xd": "Thiết kế",
    "photoshop": "Thiết kế",
    "illustrator": "Thiết kế",
    "canva": "Thiết kế",
    # Security
    "penetration testing": "An ninh mạng",
    "ethical hacking": "An ninh mạng",
    "metasploit": "An ninh mạng",
    "burp suite": "An ninh mạng",
    "owasp": "An ninh mạng",
}


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
