"""
main.py – Điểm khởi động FastAPI app.

Chạy:
    uvicorn src.api.main:app --reload
hoặc:
    python -m src.api.main
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.config import API_HOST, API_PORT
from src.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo DB + seed occupations khi app start."""
    from src.database import init_db, seed_occupations
    from src.online.services import list_occupations

    logger.info("Khởi động backend Online Pipeline...")
    init_db()
    try:
        seed_occupations(list_occupations())
    except Exception as e:  # noqa: BLE001
        logger.error(f"Không seed được occupations: {e}")

    # Prewarm embedding model ở thread nền: load model tốn ~6s (lần đầu/disk lạnh có
    # thể tới ~1 phút). Nếu để lazy thì USER ĐẦU TIÊN phải gánh toàn bộ độ trễ này.
    # Nạp sẵn lúc boot (không chặn server) → tới lúc có request /analyze model đã sẵn,
    # còn việc encode mỗi CV vốn chỉ ~0.1s.
    import threading

    def _prewarm_model() -> None:
        try:
            from src.online.embedding_step5 import get_shared_model

            logger.info("Prewarm: đang nạp embedding model ở nền...")
            get_shared_model()
            logger.info("Prewarm: embedding model đã sẵn sàng.")
        except Exception as e:  # noqa: BLE001
            logger.error(f"Prewarm model thất bại (sẽ load lazy khi cần): {e}")

    threading.Thread(target=_prewarm_model, name="model-prewarm", daemon=True).start()

    logger.info("Backend sẵn sàng. (Embedding model đang prewarm ở nền)")
    yield
    logger.info("Tắt backend.")


app = FastAPI(
    title="CV ↔ Occupation Matching API",
    description="Phân tích CV, đánh giá độ phù hợp nghề nghiệp, khuyến nghị AI.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # demo: cho phép Streamlit gọi
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"service": "cv-occupation-matching", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT, reload=False)
