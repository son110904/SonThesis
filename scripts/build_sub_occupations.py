"""
build_sub_occupations.py – Tách MỌI lĩnh vực thành các VỊ TRÍ con (sub-occupation).

Xử lý "Lỗ hổng granularity quá thô" (#7) + GỐC RỄ "skill sai lệch do gộp vai trò" (#3):
    16 nhóm nghề gộp quá nhiều vai trò khác nhau (vd nhóm CNTT trộn Backend / Designer
    → Photoshop lọt top "core CNTT"). Tách theo vị trí giúp skill đặc trưng nổi đúng chỗ.

Cách làm (tái dùng TRỌN VẸN pipeline offline cho TỪNG lĩnh vực):
    Với mỗi lĩnh vực cha:
      1. Lọc JD theo category.
      2. Gán mỗi JD vào 1 vị trí con theo job_title (regex ưu tiên theo độ đặc thù).
      3. Ghi đè category = sub_key → build_occupation_profiles gom theo vị trí con.
      4. frequency → TF-IDF (CORPUS = các vị trí con CỦA LĨNH VỰC ĐÓ) → skill weight.
         TF-IDF trong phạm vi lĩnh vực làm nổi skill đặc trưng từng vị trí.
      5. Canonicalize/dedupe (skill_normalize) → embed (fine-tuned) → ghi JSON.

Mỗi vị trí con → file data/occupation_profiles/<parent_key>__<sub_key>.json (parent_key
là tên file ASCII của profile gốc) + field `_parent`, `_sub_display` để frontend gom
"lĩnh vực → vị trí".

Chạy:
    python scripts/build_sub_occupations.py                       # build TẤT CẢ lĩnh vực
    python scripts/build_sub_occupations.py --field "công_nghệ_thông_tin_kỹ_thuật_số"
    python scripts/build_sub_occupations.py --no-embed            # bỏ embed (nhanh, xem skill)
    python scripts/build_sub_occupations.py --dry-run             # chỉ in thống kê
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import OCCUPATION_PROFILES_DIR, JD_CATEGORY_COL, JD_TITLE_COL
from src.offline.preprocessing_step1.data_loader import load_jd_dataset
from src.offline.preprocessing_step1.text_cleaner import clean_jd_dataframe
from src.offline.skill_extraction_step2.extractor import extract_all
from src.offline.profile_builder_step3.occupation_profile_builder import build_occupation_profiles
from src.offline.frequency_analysis_step4.frequency_analyzer import compute_frequency
from src.offline.tfidf_analysis_step5.tfidf_analyzer import compute_tfidf
from src.offline.skill_weight_step6.skill_weight_calculator import (
    compute_skill_weights, weight_result_to_profile_format,
)
from src.offline.skill_normalize import build_display_preference, dedupe_weighted_skills

# ── Taxonomy: category (có dấu, khớp cột category trong CSV) → vị trí con ────────
# Mỗi sub: (key ASCII, display tiếng Việt, danh sách regex job_title).
# Vị trí ĐẶC THÙ hơn đặt TRƯỚC; vị trí "chung" đặt CUỐI (chỉ bắt phần còn lại).
TAXONOMY: dict[str, dict] = {
    "công_nghệ_thông_tin_kỹ_thuật_số": {
        "parent_display": "Công nghệ thông tin",
        "subs": [
            ("fullstack_developer", "Lập trình viên Full-stack", [r"full[\s-]?stack"]),
            ("data_ai_engineer", "Kỹ sư Dữ liệu / AI",
             [r"\bdata\b", r"data engineer", r"data scientist", r"machine learning",
              r"\bai\b", r"big data", r"\bbi\b", r"phân tích dữ liệu", r"khoa học dữ liệu"]),
            ("devops_cloud_engineer", "Kỹ sư DevOps / Cloud",
             [r"devops", r"\bsre\b", r"cloud", r"\baws\b", r"azure", r"kubernetes",
              r"system admin", r"sysadmin", r"hạ tầng"]),
            ("qa_tester", "Kiểm thử (QA/Tester)",
             [r"tester", r"\bqa\b", r"\bqc\b", r"kiểm thử", r"quality assurance", r"automation test"]),
            ("mobile_developer", "Lập trình viên Mobile",
             [r"mobile", r"android", r"\bios\b", r"flutter", r"react native"]),
            ("frontend_developer", "Lập trình viên Frontend",
             [r"front[\s-]?end", r"reactjs", r"\breact\b", r"angular", r"\bvue\b", r"ui developer"]),
            ("backend_developer", "Lập trình viên Backend",
             [r"back[\s-]?end", r"\.net", r"\bjava\b", r"\bphp\b", r"nodejs", r"node\.js",
              r"golang", r"\bgo\b", r"spring", r"laravel", r"\bc#\b"]),
            ("ba_pm", "Business Analyst / PM",
             [r"business analyst", r"\bba\b", r"phân tích nghiệp vụ", r"product owner",
              r"product manager", r"project manager", r"\bpm\b", r"scrum", r"chủ sở hữu sản phẩm"]),
            ("security_engineer", "Kỹ sư An ninh mạng",
             [r"security", r"bảo mật", r"an ninh mạng", r"pentest"]),
            ("designer_ux", "Thiết kế UI/UX & Đồ họa",
             [r"ui/ux", r"ux/ui", r"\bux\b", r"graphic", r"thiết kế đồ họa", r"\bdesigner\b",
              r"thiết kế", r"game designer"]),
            ("software_engineer", "Kỹ sư phần mềm (chung)",
             [r"developer", r"lập trình", r"kỹ sư phần mềm", r"software engineer", r"\bit\b", r"phần mềm"]),
        ],
    },
    "kinh_doanh_bán_hàng_chăm_sóc_khách_hàng": {
        "parent_display": "Kinh doanh / Bán hàng",
        "subs": [
            ("sales_manager", "Quản lý kinh doanh",
             [r"trưởng phòng kinh doanh", r"trưởng nhóm kinh doanh", r"giám đốc kinh doanh", r"quản lý kinh doanh"]),
            ("store_manager", "Quản lý cửa hàng",
             [r"quản lý cửa hàng", r"cửa hàng trưởng"]),
            ("customer_service", "Chăm sóc khách hàng",
             [r"chăm sóc khách hàng", r"cskh", r"tổng đài", r"dịch vụ khách hàng"]),
            ("telesales", "Telesales",
             [r"telesale", r"telesales"]),
            ("sales_admin", "Sales Admin / Trợ lý KD",
             [r"sale[s]? ?admin", r"trợ lý kinh doanh", r"sales support", r"hỗ trợ kinh doanh"]),
            ("sales_rep", "Nhân viên kinh doanh / Bán hàng",
             [r"nhân viên kinh doanh", r"bán hàng", r"tư vấn bán hàng", r"sales", r"phát triển thị trường",
              r"chuyên viên kinh doanh", r"tư vấn"]),
        ],
    },
    "sản_xuất_lao_động_phổ_thông_cơ_khí": {
        "parent_display": "Sản xuất / Cơ khí",
        "subs": [
            ("mechanical_engineer", "Kỹ sư cơ khí",
             [r"kỹ sư cơ khí", r"thiết kế cơ khí", r"kỹ thuật cơ khí", r"nhân viên cơ khí"]),
            ("quality_qc", "Quản lý / Kiểm soát chất lượng",
             [r"\bqc\b", r"\bqa\b", r"quản lý chất lượng", r"kiểm soát chất lượng", r"kiểm tra chất lượng"]),
            ("production_mgmt", "Quản lý sản xuất",
             [r"quản lý sản xuất", r"kế hoạch sản xuất", r"điều hành sản xuất", r"trưởng ca"]),
            ("maintenance", "Bảo trì / Vận hành máy",
             [r"bảo trì", r"bảo dưỡng", r"vận hành máy"]),
            ("warehouse", "Kho / Thủ kho",
             [r"thủ kho", r"nhân viên kho", r"quản lý kho"]),
            ("technician", "Kỹ thuật / Công nhân sản xuất",
             [r"nhân viên kỹ thuật", r"công nhân", r"lao động phổ thông", r"vận hành"]),
        ],
    },
    "marketing_truyền_thông_quảng_cáo_nội_dung": {
        "parent_display": "Marketing / Truyền thông",
        "subs": [
            ("content", "Content / Nội dung",
             [r"content", r"nội dung", r"copywriter", r"content creator", r"biên tập", r"tạo nội dung"]),
            ("digital_performance", "Digital / Performance",
             [r"digital marketing", r"performance", r"\bads\b", r"\bseo\b", r"\bsem\b", r"google ads", r"facebook ads"]),
            ("video_media", "Video / Media",
             [r"video editor", r"quay dựng", r"\beditor\b", r"\bmedia\b", r"dựng phim"]),
            ("design", "Thiết kế",
             [r"thiết kế", r"graphic", r"đồ họa"]),
            ("marketing_manager", "Quản lý Marketing",
             [r"trưởng phòng marketing", r"trưởng nhóm marketing", r"giám đốc.*tiếp thị", r"marketing manager"]),
            ("marketing_generic", "Nhân viên Marketing (chung)",
             [r"marketing"]),
        ],
    },
    "tài_chính_kế_toán_ngân_hàng_bảo_hiểm": {
        "parent_display": "Tài chính / Kế toán",
        "subs": [
            ("chief_accountant", "Kế toán trưởng / Quản lý",
             [r"kế toán trưởng", r"trưởng phòng kế toán", r"phó phòng kế toán"]),
            ("tax_accountant", "Kế toán thuế", [r"kế toán thuế"]),
            ("general_accountant", "Kế toán tổng hợp", [r"kế toán tổng hợp"]),
            ("internal_accountant", "Kế toán nội bộ", [r"kế toán nội bộ"]),
            ("specialized_accountant", "Kế toán công nợ / kho / thanh toán",
             [r"kế toán công nợ", r"kế toán thanh toán", r"kế toán kho", r"kế toán bán hàng"]),
            ("finance_specialist", "Chuyên viên tài chính",
             [r"tài chính", r"phân tích tài chính", r"đầu tư", r"chuyên viên tài chính"]),
            ("banking_insurance", "Ngân hàng / Bảo hiểm",
             [r"ngân hàng", r"tín dụng", r"bảo hiểm", r"thẩm định"]),
            ("accountant_generic", "Nhân viên kế toán (chung)", [r"kế toán"]),
        ],
    },
    "du_lịch_nhà_hàng_khách_sạn_dịch_vụ": {
        "parent_display": "Du lịch / Nhà hàng - Khách sạn",
        "subs": [
            ("restaurant_mgmt", "Quản lý nhà hàng / cửa hàng",
             [r"quản lý nhà hàng", r"giám sát nhà hàng", r"quản lý cửa hàng", r"cửa hàng trưởng"]),
            ("fnb_service", "Phục vụ / Pha chế / Bếp / Lễ tân",
             [r"phục vụ", r"pha chế", r"bartender", r"\bbếp\b", r"đầu bếp", r"lễ tân"]),
            ("tour_operator", "Điều hành tour / Du lịch",
             [r"điều hành tour", r"hướng dẫn viên", r"kinh doanh du lịch"]),
            ("cashier", "Thu ngân", [r"thu ngân"]),
            ("sales_service", "Kinh doanh / Bán hàng",
             [r"nhân viên kinh doanh", r"bán hàng", r"tư vấn bán hàng"]),
        ],
    },
    "thiết_kế_nghệ_thuật_giải_trí_truyền_hình_báo_chí": {
        "parent_display": "Thiết kế / Nghệ thuật",
        "subs": [
            ("video_editor", "Video Editor / Quay dựng",
             [r"video editor", r"quay dựng", r"\beditor\b", r"dựng phim"]),
            ("graphic_designer", "Thiết kế đồ họa",
             [r"thiết kế đồ họa", r"graphic", r"đồ họa"]),
            ("interior_designer", "Thiết kế nội thất",
             [r"thiết kế nội thất", r"nội thất"]),
            ("architect", "Kiến trúc sư", [r"kiến trúc sư", r"kiến trúc"]),
            ("media", "Media / Báo chí",
             [r"\bmedia\b", r"truyền thông", r"báo chí", r"biên tập"]),
            ("designer_generic", "Thiết kế (chung)", [r"thiết kế"]),
        ],
    },
    "nhân_sự_hành_chính_pháp_chế_tư_vấn": {
        "parent_display": "Nhân sự / Hành chính / Pháp chế",
        "subs": [
            ("recruitment", "Tuyển dụng", [r"tuyển dụng"]),
            ("legal", "Pháp chế / Pháp lý", [r"pháp chế", r"pháp lý", r"\bluật\b"]),
            ("training", "Đào tạo", [r"đào tạo"]),
            ("assistant", "Trợ lý / Thư ký", [r"trợ lý", r"thư ký"]),
            ("sales_admin", "Sales Admin", [r"sale[s]? ?admin"]),
            ("hr_admin", "Hành chính nhân sự (chung)",
             [r"hành chính nhân sự", r"hành chính", r"\badmin\b", r"nhân sự"]),
        ],
    },
    "xây_dựng_kiến_trúc_bất_động_sản": {
        "parent_display": "Xây dựng / Kiến trúc / BĐS",
        "subs": [
            ("construction_engineer", "Kỹ sư xây dựng",
             [r"kỹ sư xây dựng", r"kỹ sư hiện trường", r"kỹ sư kết cấu", r"kỹ sư qs", r"dự toán"]),
            ("site_supervisor", "Giám sát công trình",
             [r"giám sát thi công", r"giám sát công trình", r"chỉ huy trưởng", r"an toàn lao động"]),
            ("architect", "Kiến trúc sư", [r"kiến trúc sư", r"kiến trúc"]),
            ("interior_design", "Thiết kế nội thất", [r"thiết kế nội thất", r"nội thất"]),
            ("mep_engineer", "Kỹ sư cơ điện (MEP)", [r"cơ điện", r"\bmep\b", r"kỹ sư điện"]),
            ("real_estate_sales", "Kinh doanh BĐS",
             [r"kinh doanh bất động sản", r"bất động sản", r"phát triển dự án", r"kinh doanh nội thất"]),
        ],
    },
    "logistics_vận_tải_chuỗi_cung_ứng": {
        "parent_display": "Logistics / Chuỗi cung ứng",
        "subs": [
            ("procurement", "Mua hàng / Thu mua", [r"mua hàng", r"thu mua"]),
            ("import_export", "Xuất nhập khẩu / Hải quan",
             [r"xuất nhập khẩu", r"khai báo hải quan", r"chứng từ", r"hải quan"]),
            ("warehouse", "Kho / Kho vận", [r"thủ kho", r"nhân viên kho", r"kho vận"]),
            ("transport_coord", "Điều phối / Vận tải / Giao nhận",
             [r"điều phối", r"vận tải", r"giao hàng", r"giao nhận"]),
        ],
    },
    "kỹ_thuật_điện_điện_tử_viễn_thông": {
        "parent_display": "Kỹ thuật điện / Viễn thông",
        "subs": [
            ("electrical_engineer", "Kỹ sư điện",
             [r"kỹ sư điện", r"kỹ thuật điện", r"thiết kế điện"]),
            ("mep_engineer", "Kỹ sư cơ điện (MEP)", [r"cơ điện", r"\bmep\b"]),
            ("automation", "Tự động hóa", [r"tự động hóa", r"\bplc\b", r"scada"]),
            ("maintenance", "Bảo trì / Điện lạnh",
             [r"bảo trì", r"bảo dưỡng", r"điện lạnh"]),
            ("telecom", "Viễn thông", [r"viễn thông"]),
            ("technician", "Kỹ thuật viên (chung)",
             [r"nhân viên kỹ thuật", r"kỹ thuật viên", r"kỹ thuật"]),
        ],
    },
    "giáo_dục_đào_tạo_nghiên_cứu": {
        "parent_display": "Giáo dục / Đào tạo",
        "subs": [
            ("teacher", "Giáo viên / Giảng viên",
             [r"giáo viên", r"giảng viên", r"trợ giảng"]),
            ("admissions", "Tư vấn tuyển sinh",
             [r"tư vấn tuyển sinh", r"tuyển sinh", r"tư vấn giáo dục", r"tư vấn du học", r"tư vấn khóa học"]),
            ("training_specialist", "Chuyên viên đào tạo", [r"đào tạo"]),
        ],
    },
    "y_tế_dược_chăm_sóc_sức_khỏe_công_nghệ_sinh_học": {
        "parent_display": "Y tế / Dược",
        "subs": [
            ("doctor", "Bác sĩ", [r"bác sĩ"]),
            ("nurse", "Điều dưỡng / Y tá", [r"điều dưỡng", r"y tá"]),
            ("pharma_rep", "Trình dược / Dược", [r"trình dược", r"\bdược\b"]),
            ("lab_technician", "KTV xét nghiệm / Phụ tá",
             [r"xét nghiệm", r"kỹ thuật viên", r"phụ tá", r"nhân viên y tế"]),
            ("medical_sales", "Kinh doanh thiết bị y tế",
             [r"thiết bị y tế", r"kinh doanh", r"telesale"]),
        ],
    },
    "ngôn_ngữ_dịch_thuật": {
        "parent_display": "Ngôn ngữ / Dịch thuật",
        "subs": [
            ("chinese", "Tiếng Trung", [r"tiếng trung"]),
            ("korean", "Tiếng Hàn", [r"tiếng hàn"]),
            ("japanese", "Tiếng Nhật", [r"tiếng nhật"]),
            ("english", "Tiếng Anh", [r"tiếng anh"]),
        ],
    },
    "nông_nghiệp_năng_lượng_môi_trường": {
        "parent_display": "Nông nghiệp / Năng lượng / Môi trường",
        "subs": [
            ("safety_hse", "An toàn lao động / HSE",
             [r"an toàn lao động", r"\bhse\b", r"an toàn"]),
            ("environment", "Môi trường",
             [r"môi trường", r"quan trắc", r"xử lý nước thải"]),
            ("agriculture", "Nông nghiệp", [r"nông nghiệp"]),
            ("energy", "Năng lượng", [r"năng lượng", r"điện mặt trời", r"điện năng"]),
        ],
    },
}


def _compile_subs(subs: list[tuple]) -> list[dict]:
    return [
        {"key": k, "display": d, "regex": [re.compile(p, re.IGNORECASE) for p in pats]}
        for k, d, pats in subs
    ]


def assign_sub_occupation(job_title: str, compiled_subs: list[dict]) -> str | None:
    """Gán job_title vào 1 vị trí con (ưu tiên theo thứ tự). None nếu không khớp."""
    if not isinstance(job_title, str):
        return None
    for sub in compiled_subs:
        if any(rx.search(job_title) for rx in sub["regex"]):
            return sub["key"]
    return None


def _resolve_parent_key(parent_category: str) -> str | None:
    """Tìm loader-key (tên file ASCII) của profile gốc khớp category. None nếu chưa có."""
    for f in Path(OCCUPATION_PROFILES_DIR).glob("*.json"):
        d = json.load(open(f, encoding="utf-8"))
        if d.get("occupation") == parent_category and not d.get("_parent"):
            return f.stem
    return None


def build_field(parent_category: str, taxonomy: dict, df_raw, model, dry_run: bool) -> int:
    """Build toàn bộ vị trí con của 1 lĩnh vực. Trả số profile đã ghi."""
    parent_display = taxonomy["parent_display"]
    compiled = _compile_subs(taxonomy["subs"])
    sub_display = {s["key"]: s["display"] for s in compiled}

    print(f"\n########## {parent_category}  ({parent_display}) ##########")
    df = df_raw[df_raw[JD_CATEGORY_COL] == parent_category].copy()
    if df.empty:
        print("  (không có JD — bỏ qua)")
        return 0
    df = clean_jd_dataframe(df)
    df["_sub"] = df[JD_TITLE_COL].apply(lambda t: assign_sub_occupation(t, compiled))
    assigned = df[df["_sub"].notna()].copy()
    dist = assigned["_sub"].value_counts()
    print(f"  Gán {len(assigned)}/{len(df)} JD:")
    for s in compiled:
        print(f"    {s['key']:22} {int(dist.get(s['key'],0)):>4}  {s['display']}")
    if assigned.empty:
        print("  (không gán được JD nào — bỏ qua)")
        return 0

    assigned[JD_CATEGORY_COL] = assigned["_sub"]
    records = extract_all(assigned)
    profiles = build_occupation_profiles(records)
    freq = compute_frequency(profiles)
    tfidf = compute_tfidf(profiles, freq)            # corpus = vị trí con trong lĩnh vực
    weights = compute_skill_weights(freq, tfidf)
    enriched = weight_result_to_profile_format(weights, profiles)

    display_pref = build_display_preference(
        [list(p["core_skills"]) + list(p["optional_skills"]) for p in enriched.values()]
    )
    for p in enriched.values():
        core = dedupe_weighted_skills(p["core_skills"], display_pref, merge="max")
        opt = dedupe_weighted_skills(p["optional_skills"], display_pref, merge="max")
        core_lower = {k.lower() for k in core}
        opt = {k: v for k, v in opt.items() if k.lower() not in core_lower}
        p["core_skills"], p["optional_skills"] = core, opt

    print("  Top core skills:")
    for key, p in enriched.items():
        top = ", ".join(f"{k}({v:.2f})" for k, v in list(p["core_skills"].items())[:6]) or "(trống)"
        print(f"    [{sub_display.get(key, key)}] {top}")

    if dry_run:
        return 0

    parent_key = _resolve_parent_key(parent_category) or parent_category
    out_dir = Path(OCCUPATION_PROFILES_DIR)
    written = 0
    for key, p in enriched.items():
        record = {
            "occupation": f"{parent_category} / {key}",
            "core_skills": p["core_skills"],
            "optional_skills": p["optional_skills"],
            "responsibilities": p["responsibilities"],
            "jd_count": p["jd_count"],
            "_parent": parent_key,
            "_parent_display": parent_display,
            "_sub_occupation": key,
            "_sub_display": sub_display.get(key, key),
            "_meta": {
                "jd_count": p["jd_count"],
                "core_skill_count": len(p["core_skills"]),
                "optional_skill_count": len(p["optional_skills"]),
                "built_at": datetime.now().isoformat(timespec="seconds"),
                "granularity": "sub_occupation",
            },
        }
        if model is not None:
            from src.offline.embedding_step7.embedder import embed_occupation_profiles
            emb = embed_occupation_profiles({key: record}, model=model)
            record["embedding"] = emb[key]
            record["_meta"]["embedding_dim"] = len(emb[key])
            record["_meta"]["embedding_model"] = "gte_multilingual_resume_match"

        json.dump(record, open(out_dir / f"{parent_key}__{key}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        written += 1
    print(f"  → ghi {written} profile vị trí con.")
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", help="Chỉ build 1 lĩnh vực (category có dấu). Mặc định: tất cả.")
    ap.add_argument("--no-embed", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    targets = [args.field] if args.field else list(TAXONOMY.keys())
    unknown = [t for t in targets if t not in TAXONOMY]
    if unknown:
        print(f"Lĩnh vực không có trong taxonomy: {unknown}\nCó: {list(TAXONOMY.keys())}")
        return

    print("Load JD dataset (1 lần)...")
    df_raw = load_jd_dataset()

    model = None
    if not args.no_embed and not args.dry_run:
        print("Load fine-tuned model (1 lần cho mọi lĩnh vực)...")
        from src.offline.embedding_step7.embedder import load_model
        model = load_model(use_finetuned=True)

    total = 0
    for cat in targets:
        total += build_field(cat, TAXONOMY[cat], df_raw, model, args.dry_run)

    print(f"\n==================== HOÀN TẤT: ghi {total} profile vị trí con ====================")
    if args.dry_run:
        print("(dry-run — không ghi file)")
    elif args.no_embed:
        print("LƯU Ý: chưa embed (--no-embed). Chạy lại không có --no-embed để dùng online.")


if __name__ == "__main__":
    main()
