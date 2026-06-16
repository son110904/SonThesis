"""
trainer.py – Fine-tune gte-multilingual-base với CosineSimilarityLoss.

Sử dụng SentenceTransformerTrainer API (sentence-transformers ≥ 3.0).
API cũ model.fit() đã bị bỏ từ v3.x.

Pipeline:
  1. Load dataset → train/val split → chuyển sang HuggingFace Dataset
  2. Load pretrained SentenceTransformer
  3. Khởi tạo CosineSimilarityLoss
  4. Cấu hình SentenceTransformerTrainingArguments
  5. Chạy SentenceTransformerTrainer.train()
  6. Lưu best model bằng save_pretrained() → đúng format để load lại
  7. Final evaluation + export metrics

Loss function:
  CosineSimilarityLoss học để:
      cosine_similarity(emb_resume, emb_job) ≈ ai_match_score / 100

  Nội bộ dùng MSELoss(cosine_sim(u,v), label).
  Phù hợp với bài toán regression liên tục (score 0→1).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import torch
from datasets import Dataset
from sentence_transformers import SentenceTransformer
from sentence_transformers import SentenceTransformerTrainer, SentenceTransformerTrainingArguments
from sentence_transformers.sentence_transformer.losses import CosineSimilarityLoss

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.config import (
    EMBEDDING_MODEL_NAME,
    FINE_TUNED_MODEL_DIR,
    TRAIN_EPOCHS,
    TRAIN_BATCH_SIZE,
    EVAL_BATCH_SIZE,
    TRAIN_WARMUP_STEPS,
    TRAIN_EVAL_STEPS,
)

logger = logging.getLogger(__name__)


def _examples_to_dataset(examples) -> Dataset:
    """
    Chuyển List[InputExample] → HuggingFace Dataset.

    SentenceTransformerTrainer yêu cầu Dataset với columns:
        sentence1, sentence2, label
    """
    return Dataset.from_dict({
        "sentence1": [ex.texts[0] for ex in examples],
        "sentence2": [ex.texts[1] for ex in examples],
        "label":     [float(ex.label) for ex in examples],
    })


def train(
    model_name: str = EMBEDDING_MODEL_NAME,
    output_dir: Path = FINE_TUNED_MODEL_DIR,
    epochs: int = TRAIN_EPOCHS,
    train_batch_size: int = TRAIN_BATCH_SIZE,
    warmup_steps: int = TRAIN_WARMUP_STEPS,
    eval_steps: int = TRAIN_EVAL_STEPS,
    val_ratio: float = 0.1,
    seed: int = 42,
    resume_from: str | None = None,
) -> SentenceTransformer:
    """
    Fine-tune SentenceTransformer với CosineSimilarityLoss.

    Args:
        model_name:       Tên model pretrained trên HuggingFace.
        output_dir:       Thư mục lưu fine-tuned model.
        epochs:           Số epoch huấn luyện.
        train_batch_size: Batch size khi train.
        warmup_steps:     Linear warmup steps.
        eval_steps:       Số steps giữa mỗi lần evaluate & save checkpoint.
        val_ratio:        Tỷ lệ validation split.
        seed:             Random seed.
        resume_from:      Path checkpoint để resume (optional).

    Returns:
        SentenceTransformer instance đã fine-tune.
    """
    from src.training.dataset import load_training_data, log_score_distribution
    from src.training.evaluator import make_evaluator, evaluate_model, print_eval_report

    logger.info("=== Bước 8: Fine-tune Semantic Matching Model ===")

    # ── 1. Dataset ────────────────────────────────────────────────────────────
    train_examples, val_examples = load_training_data(val_ratio=val_ratio, seed=seed)
    log_score_distribution(train_examples, "train")
    log_score_distribution(val_examples,   "val")

    train_dataset = _examples_to_dataset(train_examples)
    eval_dataset  = _examples_to_dataset(val_examples)

    logger.info(f"Train dataset: {train_dataset}")
    logger.info(f"Eval  dataset: {eval_dataset}")

    # ── 2. Model ──────────────────────────────────────────────────────────────
    if resume_from and Path(resume_from).exists():
        logger.info(f"Resume từ checkpoint: {resume_from}")
        model = SentenceTransformer(resume_from, trust_remote_code=True)
    else:
        logger.info(f"Load pretrained: {model_name}")
        model = SentenceTransformer(model_name, trust_remote_code=True)

    model.max_seq_length = 512

    # Workaround: trên Python 3.14 + PyTorch 2.12, buffer position_ids
    # (persistent=False) bị corrupt ở index 0 do memory reuse khi init model.
    # Re-register lại với giá trị đúng để tránh IndexError khi indexing rope_cos.
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

    logger.info(
        f"Model loaded — dim={model.get_sentence_embedding_dimension()}, "
        f"max_seq_length={model.max_seq_length}, "
        f"device={model.device}"
    )

    # ── 3. Loss ───────────────────────────────────────────────────────────────
    loss = CosineSimilarityLoss(model=model)

    # ── 4. Evaluator ──────────────────────────────────────────────────────────
    evaluator = make_evaluator(val_examples, name="val")

    # ── 5. Training arguments ─────────────────────────────────────────────────
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Thư mục tạm để Trainer lưu checkpoints trong quá trình training
    checkpoints_dir = output_dir / "checkpoints"

    args = SentenceTransformerTrainingArguments(
        output_dir=str(checkpoints_dir),

        # Training
        num_train_epochs=epochs,
        per_device_train_batch_size=train_batch_size,
        per_device_eval_batch_size=EVAL_BATCH_SIZE,
        warmup_steps=warmup_steps,
        fp16=False,
        bf16=torch.cuda.is_available(),   # bf16 ổn định hơn fp16 với gte-multilingual-base   # mixed precision nếu có GPU

        # Evaluation & checkpointing
        eval_strategy="steps",
        eval_steps=eval_steps,
        save_strategy="steps",
        save_steps=eval_steps,
        save_total_limit=2,               # giữ tối đa 2 checkpoints
        load_best_model_at_end=True,
        metric_for_best_model="val_spearman_cosine",

        # Logging
        logging_steps=eval_steps // 2,
        report_to="none",                 # tắt wandb/tensorboard
        seed=seed,
    )

    total_steps = (len(train_examples) // train_batch_size) * epochs
    logger.info(
        f"Training config: epochs={epochs}, batch={train_batch_size}, "
        f"total_steps={total_steps}, warmup={warmup_steps}, eval_every={eval_steps}"
    )

    # ── 6. Train ──────────────────────────────────────────────────────────────
    trainer = SentenceTransformerTrainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        loss=loss,
        evaluator=evaluator,
    )

    start_time = datetime.now()
    trainer.train()
    elapsed = datetime.now() - start_time
    logger.info(f"Training hoàn tất trong {elapsed}")

    # ── 7. Lưu best model bằng save_pretrained ────────────────────────────────
    # Dùng save_pretrained() thay vì output_path của fit() cũ
    # → tạo đúng config.json, tokenizer, modules.json để load lại được
    logger.info(f"Lưu best model vào: {output_dir}")
    trainer.model.save_pretrained(str(output_dir))

    # Lưu thêm tokenizer để load_pretrained hoạt động hoàn chỉnh
    try:
        tokenizer = trainer.model.tokenizer
        if tokenizer is not None:
            tokenizer.save_pretrained(str(output_dir))
    except Exception:
        pass

    logger.info(f"Model đã lưu tại: {output_dir}")

    # ── 8. Final evaluation ───────────────────────────────────────────────────
    logger.info("Đang đánh giá best model trên validation set...")
    best_model = SentenceTransformer(str(output_dir), trust_remote_code=True)
    metrics = evaluate_model(best_model, val_examples, batch_size=EVAL_BATCH_SIZE)
    print_eval_report(metrics)

    # Lưu metrics
    metrics_path = output_dir / "eval_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    logger.info(f"Metrics lưu tại: {metrics_path}")

    return best_model


def load_finetuned_model(
    model_dir: Path = FINE_TUNED_MODEL_DIR,
) -> SentenceTransformer:
    """
    Load fine-tuned model đã lưu bằng save_pretrained().

    Args:
        model_dir: Thư mục chứa config.json và weights.

    Returns:
        SentenceTransformer instance.

    Raises:
        FileNotFoundError: Nếu chưa có fine-tuned model.
    """
    if not model_dir.exists():
        raise FileNotFoundError(
            f"Fine-tuned model không tìm thấy tại: {model_dir}\n"
            f"Hãy chạy trainer.py trước để huấn luyện model."
        )
    logger.info(f"Load fine-tuned model từ: {model_dir}")
    model = SentenceTransformer(str(model_dir), trust_remote_code=True)
    try:
        emb = model._first_module().auto_model.embeddings
        if hasattr(emb, "position_ids"):
            emb.register_buffer(
                "position_ids",
                torch.arange(emb.position_ids.size(0)),
                persistent=False,
            )
    except Exception:
        pass
    return model


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    )

    import argparse
    parser = argparse.ArgumentParser(description="Fine-tune gte-multilingual-base")
    parser.add_argument("--epochs",      type=int,   default=TRAIN_EPOCHS)
    parser.add_argument("--batch-size",  type=int,   default=TRAIN_BATCH_SIZE)
    parser.add_argument("--warmup",      type=int,   default=TRAIN_WARMUP_STEPS)
    parser.add_argument("--eval-steps",  type=int,   default=TRAIN_EVAL_STEPS)
    parser.add_argument("--val-ratio",   type=float, default=0.1)
    parser.add_argument("--output-dir",  type=str,   default=str(FINE_TUNED_MODEL_DIR))
    parser.add_argument("--resume-from", type=str,   default=None)
    args = parser.parse_args()

    model = train(
        output_dir=Path(args.output_dir),
        epochs=args.epochs,
        train_batch_size=args.batch_size,
        warmup_steps=args.warmup,
        eval_steps=args.eval_steps,
        val_ratio=args.val_ratio,
        resume_from=args.resume_from,
    )

    print(f"\nFine-tuned model sẵn sàng tại: {args.output_dir}")
    print("   Bước tiếp theo: chạy knowledge_base_builder.py")