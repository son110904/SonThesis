---
title: ShibaCV
emoji: 🐾
colorFrom: orange
colorTo: red
sdk: streamlit
sdk_version: 1.58.0
app_file: app.py
pinned: false
python_version: "3.11"
short_description: AI đánh giá độ phù hợp CV với nghề nghiệp
---

# ShibaCV — AI Career Intelligence

Hệ thống đánh giá độ phù hợp CV ↔ Nghề nghiệp sử dụng mô hình embedding fine-tuned và GPT-4o.

> **Deploy trên Hugging Face Spaces:** xem mục [Deploy lên Hugging Face Spaces](#deploy-lên-hugging-face-spaces) ở cuối. Frontmatter YAML phía trên là cấu hình cho Spaces (Streamlit SDK, entry `app.py`).

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
python -m uvicorn src.api.main:app --reload
```

Backend chạy tại `http://localhost:8000`  
Swagger docs: `http://localhost:8000/docs`

### Bước 2 — Khởi động Frontend (Streamlit)

Mở terminal mới:

```bash
python -m streamlit run src/frontend/app.py
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

## Cải tiến chất lượng dữ liệu & đánh giá (`scripts/`)

Các script bổ sung xử lý các điểm yếu về **chất lượng data**, **so khớp skill** và
**đánh giá** (phục vụ bảo vệ luận văn). Chạy từ thư mục gốc.

| Script | Mục đích | Lỗ hổng xử lý |
|--------|----------|----------------|
| `scripts/clean_occupation_profiles.py` | Gộp biến thể skill trùng (`REST API API`→`REST API`, `Node.JavaScript`→`Node.js`, `erp`/`ERP`…). Tự backup. | Chất lượng data (#3) |
| `scripts/build_sub_occupations.py` | Tách 1 lĩnh vực thành **vị trí con** (Backend/Frontend/DevOps/Designer…); TF-IDF tính trên corpus sub-role nên Photoshop hết "lọt" core CNTT. | Granularity thô (#7) + gốc rễ (#3) |
| `scripts/eval_baselines.py` | So sánh **fine-tuned vs base gte vs TF-IDF vs BM25** trên val split; báo Spearman/Pearson **và RMSE/MAE** (calibration điểm tuyệt đối). | Baseline (#6) + Calibration (#2) |
| `scripts/ablation.py` | Quét `MATCH_ALPHA/BETA`, chọn trọng số theo dữ liệu thay vì 0.5/0.5. | Trọng số tùy tiện (#4) |
| `scripts/calibrate_skill_threshold.py` | Chứng minh cosine trên skill ngắn không tách bạch đồng nghĩa/khác nghĩa → vì sao dùng synonym map thay vì semantic. | Skill matching (#5) |

```bash
python scripts/clean_occupation_profiles.py        # rồi: python reembed_occupations.py
python scripts/build_sub_occupations.py --only backend_developer
python scripts/eval_baselines.py
python scripts/ablation.py
```

**So khớp skill** (`src/config.py`): `SKILL_MATCH_MODE="exact"` (mặc định) dùng
canonicalize + `SYNONYM_MAP` song ngữ — bắt được `Học máy`=`Machine Learning` mà
không false positive. Đặt `"semantic"` để thử embedding-cosine (đã đánh giá là kém
tin cậy cho skill ngắn — xem `calibrate_skill_threshold.py`).

---

## Lưu ý khi chạy trên máy mới

1. File `models/` không có trong git — xem **Mô hình embedding** bên trên.
2. File `data/app.db` (SQLite) tự tạo khi backend khởi động lần đầu.
3. Đảm bảo backend (`uvicorn`) đang chạy **trước** khi mở Streamlit *(chỉ ở chế độ
   REMOTE — xem dưới)*.

---

## Hai chế độ chạy frontend

`src/frontend/utils/api_client.py` tự chọn chế độ theo biến môi trường `API_BASE_URL`:

| Chế độ | Khi nào | Cách hoạt động |
|--------|---------|----------------|
| **EMBEDDED** *(mặc định)* | KHÔNG đặt `API_BASE_URL` | Streamlit gọi thẳng service layer trong **cùng tiến trình** — chỉ cần 1 process, không cần uvicorn. Dùng cho HF Spaces / `streamlit run app.py`. |
| **REMOTE** | Đặt `API_BASE_URL=http://127.0.0.1:8000` | Gọi FastAPI qua HTTP (kiến trúc 2 service, dev local). Cần chạy `uvicorn` trước. |

Chạy gọn ở local (1 lệnh, không cần backend riêng):

```bash
streamlit run app.py
```

---

## Deploy lên Hugging Face Spaces

Spaces chạy `streamlit run app.py` ở chế độ EMBEDDED (không cần FastAPI riêng).
Cấu hình Space nằm trong **YAML frontmatter đầu README** (`sdk: streamlit`,
`app_file: app.py`).

### Bước 1 — Đưa model fine-tuned lên Hub *(quan trọng để điểm không sai)*

Model fine-tuned **không** có trong git. Occupation embeddings (trong các file
`data/occupation_profiles/*.json`) được sinh bằng model fine-tuned, nên runtime
phải dùng **cùng** model đó — nếu không cosine similarity sẽ lệch.

```bash
huggingface-cli login                       # hoặc export HF_TOKEN=hf_xxx
python tools/push_model_to_hub.py <username>/gte-resume-match --private
```

> *Bỏ qua bước này* → hệ thống fallback về `Alibaba-NLP/gte-multilingual-base`
> (model gốc). App vẫn chạy, **không lỗi "thiếu mô hình"**, nhưng điểm semantic
> kém chính xác hơn (lệch không gian vector). Muốn dùng base hoàn toàn thì nên
> chạy lại `python reembed_occupations.py` với model base để hai bên nhất quán.

### Bước 2 — Tạo Space & đẩy code

1. Tạo Space mới: **huggingface.co/new-space** → SDK **Streamlit**.
2. Đẩy repo lên Space (Space là 1 git repo):

   ```bash
   git remote add space https://huggingface.co/spaces/<username>/<space-name>
   git push space main
   ```

### Bước 3 — Đặt biến môi trường (Space → Settings → Variables and secrets)

| Tên | Loại | Giá trị |
|-----|------|---------|
| `FINETUNED_MODEL_REPO` | Variable | `<username>/gte-resume-match` *(nếu đã đẩy model ở Bước 1)* |
| `OPENAI_API_KEY` | **Secret** | `sk-...` *(để bật AI CV Review; thiếu vẫn chạy, chỉ trống phần khuyến nghị)* |

> **KHÔNG** đặt `API_BASE_URL` trên Space — để trống cho chế độ EMBEDDED.

### Lưu ý

- Lần khởi động đầu tải model từ Hub (~vài trăm MB) → build/cold-start hơi lâu;
  sau đó được cache.
- `data/app.db` (lịch sử) là **ephemeral** trên Spaces — reset khi rebuild. Không
  ảnh hưởng chức năng chính (chấm điểm + AI review).
- Free tier CPU 16GB RAM đủ cho gte-multilingual-base.
