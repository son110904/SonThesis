import pytest

from src.offline.skill_extraction_step2.extractor import extract_skills_from_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Lập báo cáo tài chính, quyết toán thuế trên MISA.", {"Lập báo cáo tài chính", "Quyết toán thuế", "MISA"}),
        ("Điều phối giao nhận, khai báo hải quan và quản lý kho.", {"Điều phối giao nhận", "Khai báo hải quan", "Quản lý kho"}),
        ("Giám sát thi công, bóc tách khối lượng bằng Revit.", {"Giám sát thi công", "Bóc tách khối lượng", "Revit"}),
        ("Điều dưỡng cần kiểm soát nhiễm khuẩn và chăm sóc bệnh nhân.", {"Điều dưỡng", "Kiểm soát nhiễm khuẩn", "Chăm sóc bệnh nhân"}),
        ("Kỹ thuật viên vận hành CNC, đọc bản vẽ kỹ thuật và áp dụng 5S.", {"CNC", "Đọc bản vẽ kỹ thuật", "5S"}),
    ],
)
def test_extracts_specialized_non_it_skills(text, expected):
    extracted = {skill.casefold() for skill in extract_skills_from_text(text)}
    assert {skill.casefold() for skill in expected}.issubset(extracted)
