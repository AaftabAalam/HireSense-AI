from __future__ import annotations

import math
from functools import lru_cache

from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer

from app.config import Settings


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


@lru_cache(maxsize=1)
def get_bge_m3_model(model_name: str):
    try:
        from FlagEmbedding import BGEM3FlagModel

        return BGEM3FlagModel(model_name, use_fp16=False)
    except Exception:
        return None


@lru_cache(maxsize=1)
def get_reranker_model(model_name: str):
    try:
        from FlagEmbedding import FlagReranker

        return FlagReranker(model_name, use_fp16=False)
    except Exception:
        return None


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def compute_skill_relevance(settings: Settings, resume_skills: list[str], answer_text: str) -> float:
    if not resume_skills or not answer_text.strip():
        return 0.0

    skill_blob = ", ".join(resume_skills)
    bge_m3 = get_bge_m3_model(settings.embedding_model)
    reranker = get_reranker_model(settings.reranker_model)

    if bge_m3 is not None and reranker is not None:
        score_payload = bge_m3.compute_score(
            [[skill_blob, answer_text]],
            max_passage_length=256,
            weights_for_different_modes=[0.45, 0.15, 0.40],
        )
        dense_score = float(score_payload["dense"][0])
        sparse_score = float(score_payload["sparse"][0])
        colbert_score = float(score_payload["colbert"][0])
        bge_m3_score = (0.45 * dense_score) + (0.15 * sparse_score) + (0.40 * colbert_score)
        rerank_score = reranker.compute_score([[skill_blob, answer_text]])
        rerank_value = rerank_score[0] if isinstance(rerank_score, list) else float(rerank_score)
        rerank_normalized = sigmoid(rerank_value)
        final_score = (0.55 * sigmoid(bge_m3_score * 4)) + (0.45 * rerank_normalized)
        return round(max(0.0, min(1.0, final_score)), 4)

    embedder = get_embedding_model("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = embedder.encode([skill_blob, answer_text], normalize_embeddings=True)
    dense_score = float(embeddings[0] @ embeddings[1])
    lexical_score = fuzz.token_set_ratio(skill_blob.lower(), answer_text.lower()) / 100.0
    final_score = (0.7 * max(0.0, dense_score)) + (0.3 * lexical_score)
    return round(max(0.0, min(1.0, final_score)), 4)
