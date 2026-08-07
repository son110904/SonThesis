"""
resources.py – Cache tài nguyên nặng + prewarm nền theo chuẩn Streamlit.

Nguyên tắc:
  • @st.cache_resource: 1 instance / tiến trình, KHÔNG serialize → model AI, KB.
  • start_background_warmup(): nạp Embedding Model + Knowledge Base ở LUỒNG NỀN ngay
    khi app khởi động → trang upload hiện NGAY (không chặn), model nạp trong lúc người
    dùng đọc/chọn file. Tới lúc bấm "Phân tích" thì model thường đã sẵn sàng.

Lock ở tầng service (candidate_embedder._model_lock) đảm bảo dù luồng nền và luồng
phân tích cùng gọi thì model vẫn chỉ load đúng 1 lần.
"""

from __future__ import annotations

import logging
import threading

import streamlit as st

logger = logging.getLogger(__name__)

_bg_lock = threading.Lock()
_bg_started = False


@st.cache_resource(show_spinner=False)
def get_embedding_model():
    """Embedding Model (gte fine-tuned) — tải 1 lần, dùng lại cho toàn bộ phiên."""
    from src.online.embedding_step5 import get_shared_model
    return get_shared_model(use_finetuned=True)


@st.cache_resource(show_spinner=False)
def get_knowledge_base() -> dict:
    """Occupation Knowledge Base (toàn bộ profile JSON) — nạp 1 lần vào RAM."""
    from src.online.services.occupation_loader import _load_all
    return _load_all()


@st.cache_data(ttl=60, show_spinner=False)
def get_health() -> dict:
    """Trạng thái backend/LLM — cache 60s để không gọi lại mỗi rerun."""
    from src.frontend.utils.api_client import health
    return health()


def is_model_ready() -> bool:
    """True nếu embedding model đã nạp xong (để hiện trạng thái không chặn)."""
    from src.online.embedding_step5 import candidate_embedder
    return candidate_embedder._shared_model is not None


def start_background_warmup() -> None:
    """
    Nạp Knowledge Base + Embedding Model ở LUỒNG NỀN, 1 lần/tiến trình. KHÔNG chặn
    render trang. An toàn khi gọi mỗi rerun (tự guard bằng cờ module-global).
    """
    global _bg_started
    if _bg_started:
        return
    with _bg_lock:
        if _bg_started:
            return
        _bg_started = True

    def _work() -> None:
        try:
            from src.online.services.occupation_loader import _load_all
            from src.online.embedding_step5 import get_shared_model
            _load_all()                       # KB vào RAM (lru_cache)
            get_shared_model(use_finetuned=True)  # model nặng — phần lâu nhất
            logger.info("Background warmup: model + KB đã sẵn sàng.")
        except Exception:  # noqa: BLE001
            logger.exception("Background warmup lỗi (sẽ load lazy khi cần)")
        # KHÔNG để thread này kết thúc: trên Windows + torch 2.6 (Python 3.12),
        # runtime native bị segfault lúc dọn dẹp thread-local khi luồng ĐÃ nạp
        # model thoát ra (kiểm chứng: load ở main thread thì bình thường, load ở
        # thread rồi để thread kết thúc thì crash exit 139 — cả CPU lẫn CUDA).
        # Park luồng lại (daemon nên vẫn không chặn tiến trình thoát).
        threading.Event().wait()

    threading.Thread(target=_work, name="model-warmup", daemon=True).start()
    logger.info("Background warmup: bắt đầu nạp model ở luồng nền…")
