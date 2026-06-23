"""
routes.py – Định nghĩa các endpoint API.

    GET  /health              kiểm tra trạng thái (model, LLM)
    GET  /occupations         danh sách 16 nghề cho dropdown
    POST /analyze             phân tích CV (multipart: file + occupation)
    GET  /history             lịch sử đánh giá
    GET  /history/{eval_id}   chi tiết 1 lần đánh giá
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.online.extraction_step2.text_extractor import UnsupportedFileType
from src.online.services import analyze_cv, list_occupations
from src.online.services.analysis_service import EmptyCVError
from src.online.services.occupation_loader import OccupationNotFound
from src.online.recommendation_step11.llm_client import get_llm_client
from src.database import list_evaluations, get_evaluation
from src.api.schemas import (
    AnalyzeResponse,
    CandidateProfileOut,
    HistoryItem,
    HistoryListResponse,
    OccupationItem,
    OccupationListResponse,
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
    except EmptyCVError as e:
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


@router.get("/history", response_model=HistoryListResponse)
def history(limit: int = 50, occupation: str | None = None) -> HistoryListResponse:
    """Lịch sử đánh giá (mới nhất trước)."""
    rows = list_evaluations(limit=limit, occupation_key=occupation)
    items = [HistoryItem(**_to_history_item(r)) for r in rows]
    return HistoryListResponse(items=items)


@router.get("/history/{eval_id}", response_model=HistoryItem)
def history_detail(eval_id: int) -> HistoryItem:
    """Chi tiết 1 lần đánh giá."""
    row = get_evaluation(eval_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Không có bản ghi #{eval_id}.")
    return HistoryItem(**_to_history_item(row))


def _to_history_item(row: dict) -> dict:
    """Chuẩn hóa row DB → dict khớp HistoryItem (xử lý cột JSON/None)."""
    profile = row.get("candidate_profile")
    return {
        "id": row["id"],
        "created_at": row.get("created_at", ""),
        "cv_filename": row.get("cv_filename"),
        "occupation_key": row["occupation_key"],
        "occupation_display": row.get("occupation_display"),
        "match_score": row.get("match_score"),
        "semantic_similarity_score": row.get("semantic_similarity_score"),
        "weighted_skill_score": row.get("weighted_skill_score"),
        "matched_skills": row.get("matched_skills") or [],
        "missing_skills": row.get("missing_skills") or [],
        "candidate_profile": profile if isinstance(profile, dict) else None,
        "ai_recommendation": row.get("ai_recommendation"),
    }
