"""
Local, self-hosted text embeddings for semantic job/candidate matching.

Uses fastembed (ONNX runtime, no PyTorch) instead of sentence-transformers —
this runs entirely on the VM's CPU with a small memory/disk footprint
(~100-200MB total including the model weights), no external API calls, no
GPU required. Model: BAAI/bge-small-en-v1.5, 384 dimensions — small enough
to be cheap to store/index across 1.4M+ job rows, while still meaningfully
capturing semantic similarity (e.g. "ML Engineer" near "Machine Learning
Engineer" near "AI Engineer" in vector space, without a hand-maintained
synonym dictionary).
"""

import logging
from typing import List

logger = logging.getLogger("embeddings")

EMBEDDING_DIM = 384
_MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        logger.info(f"Loading embedding model {_MODEL_NAME} (first call — downloads once, then cached on disk)...")
        _model = TextEmbedding(model_name=_MODEL_NAME)
    return _model


def embed_text(text: str) -> List[float]:
    """Embeds a single string. Returns a 384-dim vector as a plain list."""
    return embed_batch([text])[0]


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Embeds a batch of strings in one model call — much faster per-item
    than calling embed_text in a loop for bulk backfill work."""
    model = _get_model()
    # bge models expect non-empty input; guard against blank descriptions
    # rather than letting the ONNX runtime choke on them mid-batch.
    safe_texts = [t if t and t.strip() else " " for t in texts]
    vectors = list(model.embed(safe_texts))
    return [v.tolist() for v in vectors]


def job_embedding_text(title: str, description: str) -> str:
    """What actually gets embedded for a job — title weighted by repetition
    since it's the strongest relevance signal and descriptions can be long
    enough to dilute it otherwise."""
    title = (title or "").strip()
    description = (description or "").strip()
    return f"{title}. {title}. {description}"[:8000]


def candidate_embedding_text(profile_data: dict) -> str:
    """What gets embedded for a candidate — most-recent role + skills +
    summary, mirroring the fields that actually carry job-relevant signal
    rather than embedding the entire raw resume text verbatim."""
    parts = []
    personal = profile_data.get("personal_info") or {}
    if profile_data.get("summary"):
        parts.append(str(profile_data["summary"]))

    for exp in (profile_data.get("experience") or [])[:5]:
        role = exp.get("role") or exp.get("title") or ""
        company = exp.get("company") or ""
        desc = exp.get("description") or ""
        parts.append(f"{role} at {company}. {desc}")

    skills = profile_data.get("skills") or {}
    flat_skills = [s for group in skills.values() if isinstance(group, list) for s in group]
    if flat_skills:
        parts.append("Skills: " + ", ".join(flat_skills))

    for proj in (profile_data.get("projects") or [])[:5]:
        name = proj.get("name") or ""
        desc = proj.get("description") or ""
        parts.append(f"Project {name}: {desc}")

    text = " ".join(p for p in parts if p.strip())
    return text[:8000] if text.strip() else (personal.get("full_name") or "candidate")
