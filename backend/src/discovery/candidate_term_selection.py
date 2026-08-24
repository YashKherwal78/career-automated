"""
Candidate-side BM25 term selection for JobRepository.get_jobs_by_hybrid_search's
lexical retrieval leg.

Replaces the old "ORDER BY length(lexeme) DESC LIMIT 8" heuristic -- string
length is not a proxy for job-search relevance. Confirmed live against a
real candidate profile: it picked "careerautom" (the candidate's own
project name), "hunter.io" (a tool mentioned once), "openai/gemini/groq"
(a slash-joined label the tokenizer can't split), and "persistent-memori"
(a niche project phrase) over "typescript"/"postgresql"/"playwright".

New selection order:
  1. Canonical skills/technologies, via the SAME registries and matcher
     jie/'s JD-side extractors already use (skills.json, technologies.json,
     TrieMatcher) -- reused directly, not duplicated. When more than
     MAX_TERMS canonical terms are found, ranked by a TF-IDF blend (see
     _rank_canonical_terms) rather than pure corpus rarity -- pure rarity
     was tested live and structurally always prefers niche frameworks
     (e.g. "sqlite", 115 docs) over foundational languages used across
     the whole job market (e.g. "python", 39664 docs), for any candidate,
     since being foundational IS what makes a term common. Weighting by
     how often the candidate's own profile actually uses a term (TF) keeps
     declared-and-reused core skills from losing every tiebreak to a
     one-off niche mention.
  2. Any remaining term budget filled from the candidate's own raw profile
     lexemes, ranked by real corpus document frequency (rarer = more
     discriminative) via ONE indexed lookup against the precomputed
     term_document_frequency table (see migration 047 and
     scripts/refresh_term_document_frequency.py) -- never a live corpus
     scan.

Always excluded: the candidate's own project names and past employers
(profile_data.projects[].name / experience[].company) -- a term unique to
one person's own resume is the opposite of a useful search term, and
generic boilerplate stems (same list JobRepository already uses).

Callers should wrap select_bm25_terms in a try/except and fall back to the
old inline SQL heuristic on any error -- see repository.py's call site.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional

from src.discovery.embeddings import candidate_embedding_text
from src.discovery.jie.extractors.skills import SkillExtractor
from src.discovery.jie.extractors.technologies import TechnologyExtractor

MAX_TERMS = 8

# Corpus size changes slowly (active-job count) and is only used to scale an
# IDF score -- cached per-process (like the extractor singletons below)
# rather than re-queried on every call, since this module's ranking
# functions run on the live per-request search path.
_corpus_size_cache: Optional[int] = None

# Mirrors JobRepository._BM25_BOILERPLATE_STEMS (core/repositories/job/repository.py) --
# duplicated as a plain constant rather than imported, to avoid a circular
# import (repository.py imports this module, not the other way around).
_BOILERPLATE_STEMS = {
    "experi", "year", "skill", "intern", "manag", "develop", "solut",
    "also", "use", "work", "team", "role", "compani", "requir",
    "abil", "strong", "excel", "opportun",
}

_skill_extractor: Optional[SkillExtractor] = None
_technology_extractor: Optional[TechnologyExtractor] = None


def _get_skill_extractor() -> SkillExtractor:
    global _skill_extractor
    if _skill_extractor is None:
        _skill_extractor = SkillExtractor()
    return _skill_extractor


def _get_technology_extractor() -> TechnologyExtractor:
    global _technology_extractor
    if _technology_extractor is None:
        _technology_extractor = TechnologyExtractor()
    return _technology_extractor


def _normalize_for_compare(term: str) -> str:
    return re.sub(r"[^a-z0-9]", "", term.lower())


def _own_names(profile_data: Dict[str, Any]) -> set[str]:
    names = set()
    for proj in (profile_data.get("projects") or []):
        name = (proj or {}).get("name") or (proj or {}).get("title") or ""
        if name:
            names.add(_normalize_for_compare(name))
    for exp in (profile_data.get("experience") or []):
        company = (exp or {}).get("company") or ""
        if company:
            names.add(_normalize_for_compare(company))
    return names


def _tsquery_safe(term: str) -> str:
    """Canonical skill/technology names (skills.json/technologies.json) are
    arbitrary human-written strings ("C++", "Node.js", "React Native") --
    unlike the old code's lexemes, which came straight out of Postgres's own
    to_tsvector and were therefore already tsquery-safe by construction.
    to_tsquery() raises a syntax error on punctuation like "+"/"#", so each
    term is reduced to alphanumeric-and-space here before ever reaching SQL.
    A multi-word result (e.g. "node js") becomes an AND of both words in
    to_tsquery, which is a reasonable, safe reading of the original term --
    not exact-phrase matching, but never a query the parser can reject."""
    return re.sub(r"[^a-z0-9 ]", " ", term.lower()).strip()


def select_bm25_terms(profile_data: Dict[str, Any], conn) -> List[str]:
    """Returns up to MAX_TERMS query terms for the lexical retrieval leg,
    each already tsquery-safe (see _tsquery_safe) and ready to be OR-joined
    directly. `conn` is used only for one indexed lookup against
    term_document_frequency (WHERE term IN (...)) -- never a corpus scan."""
    profile_data = profile_data or {}
    text = candidate_embedding_text(profile_data)
    own_names = _own_names(profile_data)

    canonical: List[str] = []
    seen_normalized: set = set()

    for raw_term in _get_skill_extractor().extract(text) + _get_technology_extractor().extract(text):
        term = _tsquery_safe(raw_term)
        norm = _normalize_for_compare(term)
        if not norm or norm in own_names or norm in seen_normalized:
            continue
        seen_normalized.add(norm)
        canonical.append(term)

    # Real profiles routinely surface MORE than MAX_TERMS canonical matches
    # (confirmed live: 27 for one real profile) -- the extractors return
    # them in alphabetical order (SkillExtractor/TechnologyExtractor sort
    # their output), which is just as arbitrary a truncation as the old
    # "longest lexeme" heuristic this whole module replaces. Rank by real
    # corpus IDF here too, not just the fallback lexemes below, so e.g.
    # "Python"/"TypeScript" don't lose a slot to "Cloudflare"/"Docker"
    # purely for coming earlier in the alphabet.
    if len(canonical) > MAX_TERMS:
        canonical = _rank_canonical_terms(canonical, profile_data, conn)[:MAX_TERMS]

    if len(canonical) >= MAX_TERMS:
        return canonical[:MAX_TERMS]

    remaining_budget = MAX_TERMS - len(canonical)
    fallback = _rank_remaining_lexemes_by_idf(text, own_names, seen_normalized, conn, remaining_budget)
    return canonical + fallback


def _get_corpus_size(conn) -> int:
    """Total active-job count, used only to scale the IDF term below.
    Cached per-process: this changes slowly and this module runs on the
    live per-request search path, so it must not re-query on every call."""
    global _corpus_size_cache
    if _corpus_size_cache is None:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM public.normalized_jobs WHERE status = 'ACTIVE'"
        ).fetchone()
        _corpus_size_cache = (row["c"] if hasattr(row, "keys") else row[0]) or 1
    return _corpus_size_cache


def _entry_text_lower(entry: Dict[str, Any]) -> str:
    parts = [
        entry.get("role") or entry.get("title") or "",
        entry.get("company") or entry.get("name") or "",
        entry.get("description") or "",
    ]
    bullets = entry.get("bullet_points")
    if isinstance(bullets, list):
        parts.extend(b for b in bullets if isinstance(b, str))
    return " ".join(p for p in parts if p).lower()


def _profile_term_frequency(term: str, profile_data: Dict[str, Any]) -> int:
    """How many distinct places in the candidate's OWN profile evidence
    this term -- the candidate's declared Skills list (+1 if present) plus
    each experience/project entry whose text mentions it. A term declared
    once in Skills but reinforced across several real entries is more
    central to this candidate than one that appears exactly once anywhere,
    regardless of how rare or common the term is in the wider job corpus."""
    term_lower = term.lower()
    count = 0

    skills = profile_data.get("skills") or {}
    flat_skills = [s.lower() for group in skills.values() if isinstance(group, list) for s in group]
    if any(term_lower in s for s in flat_skills):
        count += 1

    for exp in (profile_data.get("experience") or []):
        if term_lower in _entry_text_lower(exp):
            count += 1
    for proj in (profile_data.get("projects") or []):
        if term_lower in _entry_text_lower(proj):
            count += 1

    return count


def _rank_canonical_terms(terms: List[str], profile_data: Dict[str, Any], conn) -> List[str]:
    """Ranks canonical terms (which may be multi-word, e.g. "Multi-Agent
    Systems") by a TF-IDF blend, highest score first: how many times THIS
    candidate's own profile evidences the term (TF), multiplied by how
    rare the term is across the real job corpus (IDF) -- rather than pure
    corpus rarity alone. Pure rarity was tested live against a real
    profile and always pushed foundational languages (python, typescript)
    out in favor of niche frameworks (sqlite, vite) purely because being
    foundational is what makes a term common in ANY large job corpus.
    A multi-word term's IDF uses its RAREST constituent word's doc_count
    (the word that would actually narrow a search the most), since
    term_document_frequency stores single stemmed lexemes (from
    ts_stat()), not multi-word phrases. An unknown/missing doc_count is
    treated as if the word were extremely common (not extremely rare) --
    unknown is a data gap, not evidence of value, and scoring it as
    "rare" would let missing data outrank real measurements."""
    words = sorted({w for term in terms for w in _tsquery_safe(term).split() if len(w) >= 3})
    doc_freqs = _lookup_doc_frequencies(words, conn)
    corpus_size = _get_corpus_size(conn)

    def score(term: str) -> float:
        term_words = [w for w in _tsquery_safe(term).split() if len(w) >= 3]
        if not term_words:
            return 0.0
        df = min(doc_freqs.get(w, corpus_size) for w in term_words)
        df = max(df, 1)
        idf = math.log(corpus_size / df) if corpus_size > df else 0.0
        tf = 1 + _profile_term_frequency(term, profile_data)
        return tf * idf

    return sorted(terms, key=score, reverse=True)


def _rank_remaining_lexemes_by_idf(
    text: str, own_names: set, already_selected: set, conn, limit: int
) -> List[str]:
    if limit <= 0:
        return []

    p = conn.dialect.placeholder()
    rows = conn.execute(
        f"SELECT DISTINCT lexeme FROM unnest(tsvector_to_array(to_tsvector('english', {p}))) AS lexeme",
        (text,),
    ).fetchall()

    candidates: List[str] = []
    for row in rows:
        lexeme = row["lexeme"] if hasattr(row, "keys") else row[0]
        if not lexeme or len(lexeme) < 3:
            continue
        norm = _normalize_for_compare(lexeme)
        if lexeme in _BOILERPLATE_STEMS or norm in own_names or norm in already_selected:
            continue
        candidates.append(lexeme)

    if not candidates:
        return []

    doc_freqs = _lookup_doc_frequencies(candidates, conn)
    # Rarer (lower doc_count) = more discriminative. A term with no row yet
    # in term_document_frequency (table not refreshed, or genuinely never
    # appears in any job) sorts LAST, not first -- unknown is not the same
    # as rare/valuable.
    ranked = sorted(candidates, key=lambda t: doc_freqs.get(t, float("inf")))
    return ranked[:limit]


def _lookup_doc_frequencies(terms: List[str], conn) -> Dict[str, int]:
    if not terms:
        return {}
    p = conn.dialect.placeholder()
    placeholders = ",".join([p] * len(terms))
    rows = conn.execute(
        f"SELECT term, doc_count FROM public.term_document_frequency WHERE term IN ({placeholders})",
        tuple(terms),
    ).fetchall()
    result = {}
    for row in rows:
        if hasattr(row, "keys"):
            result[row["term"]] = row["doc_count"]
        else:
            result[row[0]] = row[1]
    return result
