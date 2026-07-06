# Dockerfile – ShibaCV trên Hugging Face Spaces (SDK: Docker, template Streamlit).
#
# HF Spaces (Docker SDK) mong đợi app lắng nghe cổng 7860 (khai báo app_port
# trong README.md frontmatter). Container chạy chế độ EMBEDDED (KHÔNG cần
# FastAPI riêng) — xem app.py.

FROM python:3.12-slim

WORKDIR /app

# libgomp1: OpenMP runtime cần cho torch/numpy khi chạy multi-thread trên CPU.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Torch bản CPU trước — nếu để requirements.txt tự resolve, một số môi trường
# Linux vẫn kéo theo gói nvidia-* (CUDA) nặng hàng GB dù không có GPU, dễ vỡ
# RAM/dung lượng lúc build. Ép rõ index CPU để tránh rủi ro này.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chỉ copy phần cần để CHẠY (không copy notebook train, CSV lớn, .venv...).
COPY src/ ./src/
COPY data/occupation_profiles/ ./data/occupation_profiles/
COPY app.py .

# Model fine-tuned KHÔNG copy vào image (bị .gitignore, quá lớn) — tải lúc
# runtime từ HF Hub qua biến môi trường FINETUNED_MODEL_REPO (đặt ở Space
# Settings → Variables and secrets, cùng chỗ với OPENAI_API_KEY, HF_TOKEN).

ENV OMP_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    PYTHONUNBUFFERED=1

EXPOSE 7860

# enableCORS/XsrfProtection=false: HF Spaces nhúng app trong iframe của họ,
# Streamlit mặc định chặn iframe cross-origin nếu không tắt 2 cờ này.
CMD ["streamlit", "run", "app.py", \
     "--server.port=7860", "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
