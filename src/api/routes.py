"""
routes.py – Định nghĩa các endpoint API.

Chế độ 1 — Occupation Matching (dùng Occupation Knowledge Base):
    GET  /health              kiểm tra trạng thái (model, LLM)
    GET  /occupations         danh sách nghề cho dropdown
    POST /analyze             phân tích CV với 1 nghề (multipart: file + occupation)
    POST /cv-improvement      sinh AI CV Improvement (tiếp nối AI CV Review)
    POST /application-email    sinh Application Email (chỉ khi người dùng bấm nút)

Chế độ 2 — JD Comparison (so sánh trực tiếp CV ↔ JD cụ thể, KHÔNG dùng KB):
    POST /compare-jd          upload CV + JD → matched/missing skills + AI Recommendation
    POST /jd/cv-improvement   sinh AI CV Improvement cho JD cụ thể
    POST /jd/application-email sinh Application Email cho JD cụ thể (chỉ khi bấm nút)

Authentication (hỗ trợ trải nghiệm — lưu 1 CV/tài khoản để tái sử dụng):
    POST /auth/register       đăng ký tài khoản
    POST /auth/login          đăng nhập
    POST /auth/cv             upload/ghi đè CV đã lưu của tài khoản
    GET  /auth/cv/{user_id}   thông tin CV đã lưu (404 nếu chưa có)
    POST /analyze-saved       phân tích CV ĐÃ LƯU với 1 nghề (không cần upload lại)
    POST /compare-jd-saved    so sánh CV ĐÃ LƯU với 1 JD (không cần upload lại CV)
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.online.extraction_step2.text_extractor import UnsupportedFileType
from src.online.services import (
    analyze_cv,
    analyze_cv_for_saved_user,
    compare_cv_with_jd,
    compare_saved_cv_with_jd,
    generate_application_email_for_jd,
    generate_application_email_for_occupation,
    generate_cv_improvement_for_jd,
    generate_cv_improvement_for_occupation,
    get_cv_info_for_user,
    list_occupations,
    login_user,
    register_user,
    save_cv_for_user,
    InvalidCredentialsError,
    NoSavedCVError,
)
from src.database.repository import EmailAlreadyExistsError
from src.online.services.analysis_service import EmptyCVError
from src.online.services.occupation_loader import OccupationNotFound
from src.online.recommendation_step11.llm_client import get_llm_client
from src.online.validation import NotACVError
from src.api.schemas import (
    AnalyzeResponse,
    AnalyzeSavedRequest,
    ApplicationEmailRequest,
    CandidateProfileOut,
    CVImprovementRequest,
    CVInfoOut,
    JDApplicationEmailRequest,
    JDComparisonResponse,
    JDCVImprovementRequest,
    LoginRequest,
    OccupationItem,
    OccupationListResponse,
    RegisterRequest,
    UserOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Giới hạn kích thước file CV (10 MB)
_MAX_FILE_BYTES = 10 * 1024 * 1024
# Giới hạn độ dài JD dán trực tiếp. Một tin tuyển dụng dài nhất cũng hiếm khi
# quá vài nghìn ký tự; chặn ở đây để tránh dán nhầm cả trang web vào ô nhập.
_MAX_JD_TEXT_CHARS = 50_000


@router.get("/health")
def health() -> dict:
    """Trạng thái dịch vụ."""
    return {
        "status": "ok",
        "llm_available": get_llm_client().is_available(),
    }


@router.get("/occupations", response_model=OccupationListResponse)
def get_occupations() -> OccupationListResponse:
    """Danh sách nghề cho dropdown."""
    items = [OccupationItem(**occ) for occ in list_occupations()]
    return OccupationListResponse(occupations=items)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(..., description="CV dạng PDF hoặc DOCX"),
    occupation: str = Form(..., description="Key nghề mong muốn"),
    include_recommendation: bool = Form(True),
) -> AnalyzeResponse:
    """Phân tích CV với nghề mục tiêu (Bước 2-11)."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="File rỗng.")
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File quá lớn (tối đa 10MB).")

    try:
        result = analyze_cv(
            file_bytes=data,
            filename=file.filename or "cv",
            occupation_key=occupation,
            include_recommendation=include_recommendation,
        )
    except OccupationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnsupportedFileType as e:
        raise HTTPException(status_code=415, detail=str(e))
    except (EmptyCVError, NotACVError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi phân tích CV")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    d = result.to_dict()
    return AnalyzeResponse(
        occupation_key=d["occupation_key"],
        occupation_display=d["occupation_display"],
        semantic_similarity_score=d["semantic_similarity_score"],
        weighted_skill_score=d["weighted_skill_score"],
        matched_skills=d["matched_skills"],
        missing_skills=d["missing_skills"],
        extra_skills=d["extra_skills"],
        candidate_profile=CandidateProfileOut(**d["candidate_profile"]),
        ai_recommendation=d["ai_recommendation"],
        cv_review=d.get("cv_review"),
    )


@router.post("/cv-improvement")
def cv_improvement(req: CVImprovementRequest) -> dict:
    """Sinh AI CV Improvement — tiếp nối AI CV Review (tái dùng profile + điểm số)."""
    try:
        result = generate_cv_improvement_for_occupation(
            candidate_profile=req.candidate_profile,
            occupation_key=req.occupation,
            semantic_similarity_score=req.semantic_similarity_score,
            weighted_skill_score=req.weighted_skill_score,
            matched_skills=req.matched_skills,
            missing_skills=req.missing_skills,
        )
    except OccupationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi sinh AI CV Improvement")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    return {"cv_improvement": result}


@router.post("/application-email")
def application_email(req: ApplicationEmailRequest) -> dict:
    """Sinh Application Email — CHỈ gọi khi người dùng chủ động bấm nút."""
    try:
        result = generate_application_email_for_occupation(
            candidate_profile=req.candidate_profile,
            occupation_key=req.occupation,
            semantic_similarity_score=req.semantic_similarity_score,
            weighted_skill_score=req.weighted_skill_score,
            matched_skills=req.matched_skills,
            missing_skills=req.missing_skills,
            cv_review=req.cv_review,
        )
    except OccupationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi sinh Application Email")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    return {"application_email": result}


# ══════════════════════════════════════════════════════════════════════════
# Chế độ 2 — JD Comparison
# ══════════════════════════════════════════════════════════════════════════
@router.post("/compare-jd", response_model=JDComparisonResponse)
async def compare_jd(
    cv_file: UploadFile = File(..., description="CV dạng PDF/DOCX/MD"),
    jd_file: Optional[UploadFile] = File(None, description="Job Description dạng PDF/DOCX/MD"),
    jd_text: str = Form("", description="Nội dung JD dán trực tiếp (thay cho jd_file)"),
) -> JDComparisonResponse:
    """
    So sánh trực tiếp CV ↔ JD cụ thể (CHẾ ĐỘ 2 — KHÔNG dùng Occupation KB).

    JD nhận qua `jd_file` HOẶC `jd_text` (dán trực tiếp) — cần ít nhất một trong hai.

    Pipeline:
      1. Extract text CV → validate là CV (LLM/heuristic).
      2. Lấy text JD (từ file hoặc từ nội dung dán).
      3. Build candidate profile (hybrid regex + LLM).
      4. Extract skills từ JD, match với candidate skills.
      5. Tính 2 chỉ số độc lập (semantic_similarity_score + coverage_pct).
      6. AI Recommendation (LLM) với context JD cụ thể.
    """
    cv_bytes = await cv_file.read()
    jd_bytes = await jd_file.read() if jd_file is not None else None
    if not cv_bytes:
        raise HTTPException(status_code=400, detail="File CV rỗng.")
    if not jd_bytes and not jd_text.strip():
        raise HTTPException(
            status_code=400, detail="Vui lòng tải lên file JD hoặc dán nội dung JD."
        )
    if len(cv_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File CV quá lớn (tối đa 10MB).")
    if jd_bytes and len(jd_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File JD quá lớn (tối đa 10MB).")
    if len(jd_text) > _MAX_JD_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Nội dung JD quá dài (tối đa {_MAX_JD_TEXT_CHARS:,} ký tự).",
        )

    try:
        result = compare_cv_with_jd(
            cv_file_bytes=cv_bytes,
            cv_filename=cv_file.filename or "cv",
            jd_file_bytes=jd_bytes,
            jd_filename=(jd_file.filename if jd_file is not None else "") or "",
            jd_text=jd_text,
        )
    except UnsupportedFileType as e:
        raise HTTPException(status_code=415, detail=str(e))
    except (EmptyCVError, NotACVError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi so sánh CV ↔ JD")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    return JDComparisonResponse(
        jd_filename=result["jd_filename"],
        jd_position=result["jd_position"],
        jd_skills=result["jd_skills"],
        jd_text_preview=result["jd_text_preview"],
        semantic_similarity_score=result["semantic_similarity_score"],
        coverage_pct=result["coverage_pct"],
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        candidate_profile=CandidateProfileOut(**result["candidate_profile"]),
        ai_recommendation=result["ai_recommendation"],
        cv_review=result["cv_review"],
    )


@router.post("/jd/cv-improvement")
def jd_cv_improvement(req: JDCVImprovementRequest) -> dict:
    """Sinh AI CV Improvement cho JD Comparison — tiếp nối AI CV Review (tái dùng profile + điểm số)."""
    try:
        result = generate_cv_improvement_for_jd(
            candidate_profile=req.candidate_profile,
            jd_position=req.jd_position,
            jd_skills=req.jd_skills,
            semantic_similarity_score=req.semantic_similarity_score,
            coverage_pct=req.coverage_pct,
            matched_skills=req.matched_skills,
            missing_skills=req.missing_skills,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi sinh AI CV Improvement (JD mode)")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    return {"cv_improvement": result}


@router.post("/jd/application-email")
def jd_application_email(req: JDApplicationEmailRequest) -> dict:
    """Sinh Application Email cho JD Comparison — CHỈ gọi khi người dùng chủ động bấm nút."""
    try:
        result = generate_application_email_for_jd(
            candidate_profile=req.candidate_profile,
            jd_skills=req.jd_skills,
            jd_text_preview=req.jd_text_preview,
            semantic_similarity_score=req.semantic_similarity_score,
            coverage_pct=req.coverage_pct,
            matched_skills=req.matched_skills,
            missing_skills=req.missing_skills,
            cv_review=req.cv_review,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi sinh Application Email (JD mode)")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    return {"application_email": result}


# ══════════════════════════════════════════════════════════════════════════
# Authentication (hỗ trợ trải nghiệm — lưu 1 CV/tài khoản để tái sử dụng)
# ══════════════════════════════════════════════════════════════════════════
@router.post("/auth/register", response_model=UserOut)
def auth_register(req: RegisterRequest) -> UserOut:
    """Đăng ký tài khoản mới."""
    try:
        user = register_user(req.full_name, req.email, req.password)
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return UserOut(**user)


@router.post("/auth/login", response_model=UserOut)
def auth_login(req: LoginRequest) -> UserOut:
    """Đăng nhập bằng email + mật khẩu."""
    try:
        user = login_user(req.email, req.password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return UserOut(**user)


@router.post("/auth/cv", response_model=CVInfoOut)
async def auth_upload_cv(
    user_id: int = Form(...),
    file: UploadFile = File(..., description="CV dạng PDF/DOCX/MD"),
) -> CVInfoOut:
    """Upload/ghi đè CV đã lưu của tài khoản."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="File rỗng.")
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File quá lớn (tối đa 10MB).")
    info = save_cv_for_user(user_id, data, file.filename or "cv")
    return CVInfoOut(**info)


@router.get("/auth/cv/{user_id}", response_model=CVInfoOut)
def auth_get_cv(user_id: int) -> CVInfoOut:
    """Thông tin CV đã lưu của tài khoản (404 nếu chưa upload)."""
    info = get_cv_info_for_user(user_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Tài khoản chưa lưu CV nào.")
    return CVInfoOut(**info)


@router.post("/analyze-saved", response_model=AnalyzeResponse)
def analyze_saved(req: AnalyzeSavedRequest) -> AnalyzeResponse:
    """Phân tích CV ĐÃ LƯU của tài khoản với 1 nghề (không cần upload lại)."""
    try:
        result = analyze_cv_for_saved_user(
            user_id=req.user_id,
            occupation_key=req.occupation,
            include_recommendation=req.include_recommendation,
        )
    except OccupationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NoSavedCVError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (EmptyCVError, NotACVError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi phân tích CV đã lưu")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    d = result.to_dict()
    return AnalyzeResponse(
        occupation_key=d["occupation_key"],
        occupation_display=d["occupation_display"],
        semantic_similarity_score=d["semantic_similarity_score"],
        weighted_skill_score=d["weighted_skill_score"],
        matched_skills=d["matched_skills"],
        missing_skills=d["missing_skills"],
        extra_skills=d["extra_skills"],
        candidate_profile=CandidateProfileOut(**d["candidate_profile"]),
        ai_recommendation=d["ai_recommendation"],
        cv_review=d.get("cv_review"),
    )


@router.post("/compare-jd-saved", response_model=JDComparisonResponse)
async def compare_jd_saved(
    user_id: int = Form(...),
    jd_file: Optional[UploadFile] = File(None, description="Job Description dạng PDF/DOCX/MD"),
    jd_text: str = Form("", description="Nội dung JD dán trực tiếp (thay cho jd_file)"),
) -> JDComparisonResponse:
    """So sánh CV ĐÃ LƯU của tài khoản với 1 JD cụ thể (không cần upload lại CV).

    JD nhận qua `jd_file` HOẶC `jd_text` (dán trực tiếp).
    """
    jd_bytes = await jd_file.read() if jd_file is not None else None
    if not jd_bytes and not jd_text.strip():
        raise HTTPException(
            status_code=400, detail="Vui lòng tải lên file JD hoặc dán nội dung JD."
        )
    if jd_bytes and len(jd_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File JD quá lớn (tối đa 10MB).")
    if len(jd_text) > _MAX_JD_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"Nội dung JD quá dài (tối đa {_MAX_JD_TEXT_CHARS:,} ký tự).",
        )

    try:
        result = compare_saved_cv_with_jd(
            user_id=user_id,
            jd_file_bytes=jd_bytes,
            jd_filename=(jd_file.filename if jd_file is not None else "") or "",
            jd_text=jd_text,
        )
    except NoSavedCVError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnsupportedFileType as e:
        raise HTTPException(status_code=415, detail=str(e))
    except (EmptyCVError, NotACVError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi so sánh CV đã lưu với JD")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    return JDComparisonResponse(
        jd_filename=result["jd_filename"],
        jd_position=result["jd_position"],
        jd_skills=result["jd_skills"],
        jd_text_preview=result["jd_text_preview"],
        semantic_similarity_score=result["semantic_similarity_score"],
        coverage_pct=result["coverage_pct"],
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        candidate_profile=CandidateProfileOut(**result["candidate_profile"]),
        ai_recommendation=result["ai_recommendation"],
        cv_review=result["cv_review"],
    )
