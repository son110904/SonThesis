"""
app.py – Điểm vào cho Hugging Face Spaces (Streamlit SDK).

Spaces chạy: `streamlit run app.py`. File này chỉ ủy quyền sang frontend chính
(src/frontend/app.py). Vì KHÔNG đặt API_BASE_URL, api_client tự bật chế độ
EMBEDDED → gọi service trong cùng tiến trình, không cần chạy FastAPI riêng.

Chạy local tương đương:
    streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Đảm bảo repo root nằm trên sys.path để import được package `src`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.frontend.app import main

if __name__ == "__main__":
    main()
