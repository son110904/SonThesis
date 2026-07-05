"""
routes.py – Định nghĩa các endpoint API.

    GET  /health              kiểm tra trạng thái (model, LLM)
    GET  /occupations         danh sách nghề cho dropdown
    POST /analyze             phân tích CV với 1 nghề (multipart: file + occupation)
    POST /recommend           gợi ý Top-K nghề phù hợp nhất
    POST /review              sinh AI Review cho 1 nghề (tái dùng profile + embedding)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.online.extraction_step2.text_extractor import UnsupportedFileType
from src.online.services import (
    analyze_cv,
    list_occupations,
    recommend_occupations,
    review_occupation,
)
from src.online.services.analysis_service import EmptyCVError
from src.online.services.occupation_loader import OccupationNotFound
from src.online.recommendation_step11.llm_client import get_llm_client
from src.online.validation import NotACVError
from src.api.schemas import (
    AnalyzeResponse,
    CandidateProfileOut,
    OccupationItem,
    OccupationListResponse,
    RecommendationItem,
    RecommendationResponse,
    ReviewRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Giới hạn kích thước file CV (10 MB)
_MAX_FILE_BYTES = 10 * 1024 * 1024


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
        match_score=d["match_score"],
        semantic_similarity_score=d["semantic_similarity_score"],
        weighted_skill_score=d["weighted_skill_score"],
        matched_skills=d["matched_skills"],
        missing_skills=d["missing_skills"],
        extra_skills=d["extra_skills"],
        candidate_profile=CandidateProfileOut(**d["candidate_profile"]),
        ai_recommendation=d["ai_recommendation"],
        cv_review=d.get("cv_review"),
    )


@router.post("/recommend", response_model=RecommendationResponse)
async def recommend(
    file: UploadFile = File(..., description="CV dạng PDF/DOCX/MD"),
    top_k: int = Form(3),
) -> RecommendationResponse:
    """Career Recommendation: Top-K nghề phù hợp nhất với CV."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="File rỗng.")
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File quá lớn (tối đa 10MB).")

    try:
        out = recommend_occupations(
            file_bytes=data, filename=file.filename or "cv", top_k=top_k
        )
    except UnsupportedFileType as e:
        raise HTTPException(status_code=415, detail=str(e))
    except (EmptyCVError, NotACVError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi gợi ý nghề")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    return RecommendationResponse(
        recommendations=[RecommendationItem(**r) for r in out["recommendations"]],
        candidate_profile=out["candidate_profile"],
        candidate_embedding=out["candidate_embedding"],
    )


@router.post("/review", response_model=AnalyzeResponse)
def review(req: ReviewRequest) -> AnalyzeResponse:
    """Sinh AI CV Review cho 1 nghề đã chọn (tái dùng profile + embedding)."""
    try:
        result = review_occupation(
            candidate_profile=req.candidate_profile,
            candidate_embedding=req.candidate_embedding,
            occupation_key=req.occupation,
            include_recommendation=req.include_recommendation,
        )
    except OccupationNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("Lỗi khi review nghề đã chọn")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {e}")

    d = result.to_dict()
    return AnalyzeResponse(
        occupation_key=d["occupation_key"],
        occupation_display=d["occupation_display"],
        match_score=d["match_score"],
        semantic_similarity_score=d["semantic_similarity_score"],
        weighted_skill_score=d["weighted_skill_score"],
        matched_skills=d["matched_skills"],
        missing_skills=d["missing_skills"],
        extra_skills=d["extra_skills"],
        candidate_profile=CandidateProfileOut(**d["candidate_profile"]),
        ai_recommendation=d["ai_recommendation"],
        cv_review=d.get("cv_review"),
    )
