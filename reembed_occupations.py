"""
reembed_occupations.py – Sinh lại occupation_embedding bằng FINE-TUNED model.

Vì sao: sau khi retrain (Bước 8), phía candidate dùng fine-tuned model còn các
file data/occupation_profiles/*.json vẫn giữ embedding cũ (sinh bằng pretrained
qua fallback NaN). Hai bên lệch không gian vector → điểm semantic sai. Script này
re-embed TẠI CHỖ: giữ nguyên mọi field, chỉ thay `embedding` + cập nhật `_meta`.

Chạy: py -3.12 reembed_occupations.py

⚠️ PHẢI dùng Python 3.12. Trên 3.14 + torch 2.12, embedder tự reset position_ids
để khỏi crash nhưng embedding SUY GIẢM âm thầm — embedding sinh ra sẽ nằm ở
"không gian" khác hẳn (đo được: cosine với bản đúng chỉ ~0.34), khiến MỌI điểm
semantic về sau đều sai.
"""
import sys, json, logging
from pathlib import Path

# Tên file/nghề có dấu tiếng Việt; console Windows mặc định cp1252 sẽ ném
# UnicodeEncodeError giữa chừng — mà lúc đó JSON đã ghi được một phần, để lại KB
# ở trạng thái nửa cũ nửa mới (lệch không gian vector). Ép UTF-8 cho stdout.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s – %(message)s")

from src.config import OCCUPATION_PROFILES_DIR, FINE_TUNED_MODEL_DIR
from src.offline.embedding_step7.embedder import load_model, embed_occupation_profiles

files = sorted(OCCUPATION_PROFILES_DIR.glob("*.json"))
profiles, raw = {}, {}
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    raw[f] = d
    profiles[d.get("occupation", f.stem)] = d  # build_occupation_text đọc các field này

model = load_model(use_finetuned=True)
embs = embed_occupation_profiles(profiles, model=model)  # build_occupation_text + truncate + encode + L2-norm

# map occupation-name → file để ghi lại đúng chỗ
name_to_file = {d.get("occupation", f.stem): f for f, d in raw.items()}
for occ_name, vec in embs.items():
    f = name_to_file[occ_name]
    d = raw[f]
    d["embedding"] = vec
    meta = d.setdefault("_meta", {})
    meta["embedding_dim"] = len(vec)
    meta["embedding_model"] = str(FINE_TUNED_MODEL_DIR.name)
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  re-embedded: {f.name}  (dim={len(vec)})")

print(f"\nHoàn tất: {len(embs)} occupation re-embedded bằng fine-tuned model.")
