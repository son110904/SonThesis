# ShibaCV: FastAPI + Streamlit
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_RUN_ON_SAVE=false

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway exposes PORT (default 8080) publicly.
# FastAPI internal on 8000, Streamlit on PORT.
RUN printf '#!/bin/sh\n' \
    'uvicorn src.api.main:app --host 127.0.0.1 --port 8000 &\n' \
    'streamlit run src/frontend/app.py --server.port $PORT --server.address 0.0.0.0\n' \
    > /start.sh && chmod +x /start.sh

EXPOSE 8080

CMD ["/start.sh"]
