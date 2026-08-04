# ShibaCV: Streamlit only
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

# Debug: print working dir + files first, then start
CMD ["sh", "-c", "pwd && ls && echo '---START---' && streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0"]
