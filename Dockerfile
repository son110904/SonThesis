# ShibaCV: FastAPI + Streamlit
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_RUN_ON_SAVE=false

WORKDIR /app

# Copy và install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501')" || exit 1

# Start both FastAPI (8000) and Streamlit (8501) together
CMD ["sh", "-c", \
    "uvicorn src.api.main:app --host 0.0.0.0 --port 8000 & " \
    "streamlit run src/frontend/app.py --server.port 8501 --server.address 0.0.0.0 & " \
    "wait"]
