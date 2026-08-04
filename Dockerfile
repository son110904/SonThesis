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

# Start both services using a shell script
RUN echo '#!/bin/sh' > /start.sh && \
    echo 'uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &' >> /start.sh && \
    echo 'streamlit run src/frontend/app.py --server.port 8501 --server.address 0.0.0.0 &' >> /start.sh && \
    echo 'wait' >> /start.sh && \
    chmod +x /start.sh

CMD ["/start.sh"]
