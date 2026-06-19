# ShibaCV — AI Career Intelligence

Hệ thống đánh giá độ phù hợp CV ↔ Nghề nghiệp sử dụng mô hình embedding fine-tuned và GPT-4o Mini.

---

## Yêu cầu

- Python **3.10 – 3.12** (khuyến nghị 3.12)
- pip / virtualenv
- *(Tuỳ chọn)* GPU CUDA 12.1 để train mô hình

---

## Cài đặt

```bash
# 1. Clone repo
git clone https://github.com/son110904/SonThesis.git
cd SonThesis

# 2. Tạo môi trường ảo
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Cài dependencies
pip install -r requirements.txt
```

---

## Cấu hình

Tạo file `.env` ở thư mục gốc:

```env
# Bắt buộc nếu muốn sinh khuyến nghị AI
OPENAI_API_KEY=sk-...
```

> Thiếu key vẫn chạy được — điểm phù hợp vẫn tính đầy đủ, phần khuyến nghị AI sẽ để trống.

---

## Chạy ứng dụng

### Bước 1 — Khởi động Backend (FastAPI)

```bash
uvicorn src.api.main:app --reload
```

Backend chạy tại `http://localhost:8000`  
Swagger docs: `http://localhost:8000/docs`

### Bước 2 — Khởi động Frontend (Streamlit)

Mở terminal mới:

```bash
streamlit run src/frontend/app.py
```

Giao diện mở tại `http://localhost:8501`

---

## Mô hình embedding

Mô hình fine-tuned **không** được commit vào git (quá lớn, ~4 GB).  
Có 2 lựa chọn:

### Lựa chọn A — Dùng mô hình gốc (không cần train)

Mặc định hệ thống fallback về `Alibaba-NLP/gte-multilingual-base` nếu không tìm thấy mô hình fine-tuned.

### Lựa chọn B — Train lại mô hình (cần GPU)

```bash
python run_train_gpu.py
```

Mô hình được lưu vào `models/gte_multilingual_resume_match/`.

### Lựa chọn C — Re-embed occupation profiles

Sau khi có mô hình fine-tuned, chạy để tạo lại embeddings:

```bash
python reembed_occupations.py
```

---

## Cấu trúc thư mục

```
SonThesis/
├── data/
│   ├── occupation_profiles/   # 16 nhóm nghề (JSON)
│   └── ...                    # dataset training
├── models/                    # model weights (gitignored)
├── src/
│   ├── api/                   # FastAPI backend
│   ├── frontend/              # Streamlit UI
│   │   ├── assets/            # Ảnh mascot shiba
│   │   ├── components/        # Gauge, cards, badges
│   │   ├── pages/             # landing / home / result
│   │   └── utils/             # styling, api_client
│   ├── offline/               # Pipeline xử lý offline (9 bước)
│   └── training/              # Fine-tune embedding model
├── run_offline.py             # Chạy offline pipeline
├── run_train_gpu.py           # Train mô hình trên GPU
├── reembed_occupations.py     # Re-embed sau khi train
├── requirements.txt
└── .env                       # Tạo thủ công (gitignored)
```

---

## Offline Pipeline (tuỳ chọn)

Chạy toàn bộ pipeline xử lý dữ liệu từ đầu:

```bash
python run_offline.py
```

Gồm 9 bước: preprocessing → skill extraction → profile builder → frequency analysis → TF-IDF → skill weight → embedding → knowledge base.

---

## Lưu ý khi chạy trên máy mới

1. File `models/` không có trong git — xem **Mô hình embedding** bên trên.
2. File `data/app.db` (SQLite) tự tạo khi backend khởi động lần đầu.
3. Đảm bảo backend (`uvicorn`) đang chạy **trước** khi mở Streamlit.
