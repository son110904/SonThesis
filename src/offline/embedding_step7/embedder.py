"""
embedder.py – Sinh occupation_embedding từ Occupation Profile đã enriched.

Chiến lược xây dựng văn bản đầu vào cho embedding:
    Ghép core_skills (ưu tiên cao) + optional_skills + responsibilities
    thành một đoạn văn bản đại diện cho occupation.

    Ví dụ:
        "Occupation: Công nghệ thông tin kỹ thuật số.
         Core skills: Python, SQL, Docker, Agile, JavaScript, Java.
         Skills: Figma, MongoDB, Azure, DevOps.
         Responsibilities: Phát triển API backend RESTful. Triển khai CI/CD."

Mô hình:
    gte-multilingual-base (Alibaba-NLP) — đa ngôn ngữ, hỗ trợ cả EN + VI.
    Nếu đã fine-tune (Bước 8 xong), load từ FINE_TUNED_MODEL_DIR.
    Nếu chưa, dùng pretrained gốc.

Output:
    Dict[occupation_key → List[float]]  (vector embedding, dim=768)
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.config import EMBEDDING_MODEL_NAME, FINE_TUNED_MODEL_DIR

logger = logging.getLogger(__name__)

# Số responsibilities tối đa đưa vào text để embed
MAX_RESP_IN_TEXT = 5
# Số core/optional skills tối đa trong text
MAX_CORE_SKILLS = 20
MAX_OPT_SKILLS = 10


def build_occupation_text(profile: dict) -> str:
    """
    Xây dựng văn bản đại diện cho một occupation để embed.

    Cấu trúc:
        "Occupation: <tên>.
         Core skills: <skill1>, <skill2>, ...
         Skills: <optional1>, <optional2>, ...
         Responsibilities: <resp1>. <resp2>."

    Core skills được đặt trước và lặp lại để tăng trọng số trong embedding.

    Args:
        profile: Một entry từ weight_result_to_profile_format()
                 Keys: occupation, core_skills, optional_skills, responsibilities

    Returns:
        Chuỗi văn bản đại diện.
    """
    occupation = profile.get("occupation", "")
    core_skills = list(profile.get("core_skills", {}).keys())[:MAX_CORE_SKILLS]
    opt_skills  = list(profile.get("optional_skills", {}).keys())[:MAX_OPT_SKILLS]
    resps       = profile.get("responsibilities", [])[:MAX_RESP_IN_TEXT]

    parts: list[str] = []

    parts.append(f"Occupation: {occupation}.")

    if core_skills:
        parts.append(f"Core skills: {', '.join(core_skills)}.")
        # Lặp core skills để tăng trọng số trong embedding
        parts.append(f"Key competencies: {', '.join(core_skills[:10])}.")

    if opt_skills:
        parts.append(f"Additional skills: {', '.join(opt_skills)}.")

    if resps:
        resp_text = " ".join(r.strip().rstrip(".") + "." for r in resps if r.strip())
        if resp_text:
            parts.append(f"Responsibilities: {resp_text}")

    return " ".join(parts)


def _reset_position_ids(model) -> None:
    """
    Workaround: Python 3.14 + PyTorch 2.12 — buffer position_ids (persistent=False)
    bị corrupt do memory reuse khi init model, gây IndexError tại rope_cos[position_ids].
    Re-register lại với giá trị đúng (torch.arange).
    """
    try:
        emb = model._first_module().auto_model.embeddings
        if hasattr(emb, "position_ids"):
            emb.register_buffer(
                "position_ids",
                torch.arange(emb.position_ids.size(0)),
                persistent=False,
            )
    except Exception as _e:
        logger.warning(f"Không thể reset position_ids: {_e}")


def _has_nan_weights(model) -> bool:
    """Kiểm tra model có tensor NaN không (vd fine-tuned model từ training bị diverge)."""
    return any(torch.isnan(p).any().item() for p in model.parameters())


def load_model(use_finetuned: bool = True):
    """
    Load SentenceTransformer model.

    Args:
        use_finetuned: Nếu True và FINE_TUNED_MODEL_DIR tồn tại → load fine-tuned.
                       Ngược lại → load pretrained gốc.

    Returns:
        SentenceTransformer instance.
    """
    from sentence_transformers import SentenceTransformer

    if use_finetuned and FINE_TUNED_MODEL_DIR.exists():
        model_path = str(FINE_TUNED_MODEL_DIR)
        logger.info(f"Load fine-tuned model từ: {model_path}")
    else:
        model_path = EMBEDDING_MODEL_NAME
        if use_finetuned:
            logger.warning(
                f"Fine-tuned model không tìm thấy tại {FINE_TUNED_MODEL_DIR}. "
                f"Dùng pretrained: {EMBEDDING_MODEL_NAME}"
            )
        else:
            logger.info(f"Load pretrained model: {model_path}")

    model = SentenceTransformer(model_path, trust_remote_code=True)
    model.max_seq_length = 512
    _reset_position_ids(model)

    # Phát hiện fine-tuned model bị hỏng (NaN weights do training diverge với mixed
    # precision). Nếu hỏng → fallback sang pretrained để embedding không ra NaN.
    if _has_nan_weights(model):
        if model_path != EMBEDDING_MODEL_NAME:
            logger.error(
                f"Model tại {model_path} chứa NaN weights (training diverged). "
                f"Fallback sang pretrained: {EMBEDDING_MODEL_NAME}. "
                f"Hãy fine-tune lại (fp32) để dùng được fine-tuned model."
            )
            model = SentenceTransformer(EMBEDDING_MODEL_NAME, trust_remote_code=True)
            model.max_seq_length = 512
            _reset_position_ids(model)
        else:
            raise RuntimeError(
                "Pretrained model chứa NaN weights — không thể dùng để embed."
            )

    logger.info(
        f"Model loaded. Embedding dim: {model.get_sentence_embedding_dimension()}, "
        f"max_seq_length={model.max_seq_length}"
    )
    return model


def embed_occupation_profiles(
    enriched_profiles: dict[str, dict],
    model=None,
    use_finetuned: bool = True,
    batch_size: int = 16,
    normalize: bool = True,
) -> dict[str, list[float]]:
    """
    Sinh occupation_embedding cho tất cả occupation.

    Args:
        enriched_profiles: Output weight_result_to_profile_format()
        model:            SentenceTransformer instance (nếu None sẽ load tự động)
        use_finetuned:    Ưu tiên dùng fine-tuned model
        batch_size:       Batch size khi encode
        normalize:        L2-normalize vector (tốt cho cosine similarity)

    Returns:
        Dict[occupation_key → List[float]]  (embedding vector)
    """
    if model is None:
        model = load_model(use_finetuned=use_finetuned)

    logger.info(f"Đang embed {len(enriched_profiles)} occupation profiles...")

    # Xây dựng texts và giữ thứ tự key
    occ_keys = list(enriched_profiles.keys())
    texts = [build_occupation_text(enriched_profiles[k]) for k in occ_keys]

    logger.debug(f"Sample text:\n{texts[0][:300]}")

    # Truncate texts thủ công qua tokenizer trước khi encode
    # Tránh position_ids overflow trong gte-multilingual-base
    MAX_TOKENS = 512
    tokenizer = model.tokenizer
    truncated_texts = []
    for text in texts:
        tokens = tokenizer(
            text,
            max_length=MAX_TOKENS,
            truncation=True,
            return_tensors=None,
        )
        truncated = tokenizer.decode(
            tokens["input_ids"],
            skip_special_tokens=True,
        )
        truncated_texts.append(truncated)

    # Encode
    embeddings = model.encode(
        truncated_texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=normalize,
        convert_to_numpy=True,
    )

    result: dict[str, list[float]] = {
        occ_key: embeddings[i].tolist()
        for i, occ_key in enumerate(occ_keys)
    }

    dim = len(next(iter(result.values())))
    logger.info(f"Hoàn tất embedding: {len(result)} occupation, dim={dim}")
    return result


def compute_similarity(
    emb1: list[float],
    emb2: list[float],
) -> float:
    """
    Tính cosine similarity giữa hai embedding vector (đã L2-normalized → dot product).

    Args:
        emb1, emb2: Embedding vectors (đã normalize).

    Returns:
        Cosine similarity ∈ [-1, 1]
    """
    v1 = np.array(emb1, dtype=np.float32)
    v2 = np.array(emb2, dtype=np.float32)
    return float(np.dot(v1, v2))


def find_most_similar_occupation(
    query_embedding: list[float],
    occupation_embeddings: dict[str, list[float]],
    top_k: int = 3,
) -> list[tuple[str, float]]:
    """
    Tìm các occupation gần nhất với một embedding query.

    Args:
        query_embedding:       Embedding vector của CV/resume.
        occupation_embeddings: Dict từ embed_occupation_profiles().
        top_k:                 Số kết quả trả về.

    Returns:
        List[(occupation_key, similarity_score)] sắp xếp giảm dần.
    """
    scores: list[tuple[str, float]] = [
        (occ_key, compute_similarity(query_embedding, emb))
        for occ_key, emb in occupation_embeddings.items()
    ]
    return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    from src.offline.preprocessing_step1.data_loader import load_jd_dataset
    from src.offline.preprocessing_step1.text_cleaner import clean_jd_dataframe
    from src.offline.skill_extraction_step2.extractor import extract_all
    from src.offline.profile_builder_step3.occupation_profile_builder import build_occupation_profiles
    from src.offline.frequency_analysis_step4.frequency_analyzer import compute_frequency
    from src.offline.tfidf_analysis_step5.tfidf_analyzer import compute_tfidf
    from src.offline.skill_weight_step6.skill_weight_calculator import (
        compute_skill_weights, weight_result_to_profile_format
    )

    # Pipeline 1→6
    df = clean_jd_dataframe(load_jd_dataset())
    records = extract_all(df)
    profiles = build_occupation_profiles(records)
    freq_result = compute_frequency(profiles)
    tfidf_result = compute_tfidf(profiles, freq_result)
    weight_result = compute_skill_weights(freq_result, tfidf_result)
    enriched = weight_result_to_profile_format(weight_result, profiles)

    # Xem text sẽ được embed
    print("\n=== Sample occupation texts ===")
    for key in list(enriched.keys())[:3]:
        text = build_occupation_text(enriched[key])
        print(f"\n[{key}]")
        print(f"  {text[:300]}...")

    # Embed (dùng pretrained vì chưa fine-tune)
    print("\n=== Embedding occupation profiles ===")
    model = load_model(use_finetuned=False)
    occ_embeddings = embed_occupation_profiles(enriched, model=model, use_finetuned=False)

    print(f"\nEmbedding dim: {len(next(iter(occ_embeddings.values())))}")
    print(f"Số occupation đã embed: {len(occ_embeddings)}")

    # Kiểm tra cosine similarity giữa các occupation
    print("\n=== Cosine similarity giữa các occupation ===")
    keys = list(occ_embeddings.keys())
    it_key  = "công_nghệ_thông_tin_kỹ_thuật_số"
    mkt_key = "marketing_truyền_thông_quảng_cáo_nội_dung"
    fin_key = "tài_chính_kế_toán_ngân_hàng_bảo_hiểm"
    elec_key = "kỹ_thuật_điện_điện_tử_viễn_thông"

    pairs = [
        (it_key, mkt_key, "IT vs Marketing"),
        (it_key, elec_key, "IT vs Kỹ thuật điện"),
        (it_key, fin_key, "IT vs Tài chính"),
        (mkt_key, fin_key, "Marketing vs Tài chính"),
    ]
    for k1, k2, label in pairs:
        sim = compute_similarity(occ_embeddings[k1], occ_embeddings[k2])
        print(f"  {label:<35} sim={sim:.4f}")

    # Test find_most_similar
    print(f"\n=== Most similar to IT ===")
    results = find_most_similar_occupation(occ_embeddings[it_key], occ_embeddings)
    for occ, score in results:
        print(f"  {occ:<55} {score:.4f}")


def embed_with_mock(
    enriched_profiles: dict[str, dict],
    dim: int = 768,
) -> dict[str, list[float]]:
    """
    Mock embedding dùng để test pipeline khi không có model (offline/CI).

    Tạo vector ngẫu nhiên L2-normalized cho mỗi occupation.
    KHÔNG dùng trong production.

    Args:
        enriched_profiles: Output weight_result_to_profile_format().
        dim: Embedding dimension (768 cho gte-multilingual-base).

    Returns:
        Dict[occupation_key → List[float]] (random normalized vectors).
    """
    import numpy as np
    logger.warning("Dùng mock embedding — chỉ dùng để test pipeline, không dùng production!")
    rng = np.random.default_rng(seed=42)
    result: dict[str, list[float]] = {}
    for occ_key in enriched_profiles:
        vec = rng.standard_normal(dim).astype(np.float32)
        vec /= np.linalg.norm(vec)
        result[occ_key] = vec.tolist()
    return result