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


def job_embedding_text(
    title: str,
    description: str,
    technologies: List[str] = None,
    skills: List[str] = None,
    responsibilities: List[str] = None,
    experience_min: int = None,
    experience_max: int = None,
) -> str:
    """What actually gets embedded for a job.

    bge-small-en-v1.5 has a real effective context of ~512 tokens (roughly
    2000 characters of English text) -- text past that point contributes
    nothing to the embedding, it's silently dropped by the tokenizer, not
    just "given less weight". A 10-15k character raw job description
    frequently opens with generic company-mission boilerplate ("we're
    building a safer world...") before any real technical content --
    confirmed on real postings -- so truncating raw title+description
    alone can mean the actual skills/responsibilities the posting cares
    about never reach the model at all.

    Structured fields (technologies/skills/responsibilities, from
    src.discovery.jie.extractor.JDExtractor) are front-loaded when given,
    ahead of the raw description, so the dense, already-extracted signal
    survives truncation even when the raw text wouldn't have. Optional and
    backward compatible: callers with just title/description (or an
    extraction that returned nothing) get the previous behavior.

    experience_min/max add a soft semantic signal, NOT a filter -- a job
    embedding that says "Experience required: 5-8 years" naturally lands
    further from a junior candidate's profile embedding than one that
    doesn't mention seniority at all, which helps ranking even for jobs a
    hard experience filter doesn't directly touch. This does NOT replace
    max_experience_years as a real SQL WHERE clause (see
    JobRepository.get_jobs_by_vector_similarity's docstring) -- embeddings
    can't guarantee a hard cutoff, only nudge relative distance. Only
    meaningful if candidate_embedding_text below also states years of
    experience -- the model needs both sides for this to do anything.
    """
    title = (title or "").strip()
    description = (description or "").strip()

    parts = [title, title]
    if technologies:
        parts.append("Technologies: " + ", ".join(technologies[:15]))
    if skills:
        parts.append("Skills: " + ", ".join(skills[:15]))
    if responsibilities:
        parts.append("Responsibilities: " + " ".join(responsibilities[:5]))
    if experience_min is not None or experience_max is not None:
        if experience_min is not None and experience_max is not None and experience_max != experience_min:
            parts.append(f"Experience required: {experience_min}-{experience_max} years")
        elif experience_min is not None:
            parts.append(f"Experience required: {experience_min}+ years")
        else:
            parts.append(f"Experience required: up to {experience_max} years")
    parts.append(description)

    return ". ".join(p for p in parts if p)[:8000]


def candidate_embedding_text(profile_data: dict) -> str:
    """What gets embedded for a candidate — most-recent role + skills +
    summary, mirroring the fields that actually carry job-relevant signal
    rather than embedding the entire raw resume text verbatim.

    Years of experience is front-loaded (like job_embedding_text's
    "Experience required: ..." line) so the two sides can actually be
    compared -- a job embedding that mentions seniority has nothing to
    land near/far from if the candidate side never mentions it."""
    parts = []
    personal = profile_data.get("personal_info") or {}

    try:
        from src.discovery.jie.candidate_profile import CandidateProfile as _CP
        years = _CP._estimate_years_experience(profile_data.get("experience") or [])
        if years > 0:
            parts.append(f"{years} years of experience")
    except Exception:
        pass

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
