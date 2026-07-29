"""
Deterministic text-overlap scoring — no LLM calls, no embedding model, no new
dependencies. Used to compare a JD's responsibilities against a candidate's
experience/project text, which JIE's skill-list matching alone can't capture
(e.g. "owned end-to-end delivery of a payments platform" vs "led migration of
legacy services" share no exact skill keywords but are clearly related work).

Two-document TF-IDF cosine similarity: within the pair (text_a, text_b), terms
appearing in both documents are down-weighted relative to terms unique to one
side, which is what keeps generic words (the whole reason for stopword
filtering isn't perfect on its own) from dominating the score.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import List

_STOPWORDS = frozenset(
    """
    a an the and or for to of in on with by is are was were be been being
    this that those these you your we our as at from will can may must
    should shall it its into over under about across per within without
    do does did have has had not no yes if then than so such other more
    most some any all each their they them he she his her i we us out up
    down while during after before between when where who whom which what
    also etc using use used via across per
    """.split()
)
_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.]{1,}")


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in _STOPWORDS]


def cosine_similarity(text_a: str, text_b: str) -> float:
    """Returns 0.0-1.0. 0.0 if either text has no usable tokens."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0

    vocab = set(tokens_a) | set(tokens_b)
    doc_freq = Counter()
    for term in set(tokens_a):
        doc_freq[term] += 1
    for term in set(tokens_b):
        doc_freq[term] += 1

    def _vector(tokens: List[str]) -> dict:
        term_freq = Counter(tokens)
        vec = {}
        for term, tf in term_freq.items():
            # doc_freq is 1 (term unique to one side) or 2 (shared) here —
            # idf = ln(2/df) + 1 gives shared terms a smaller (but nonzero) weight.
            idf = math.log(2.0 / doc_freq[term]) + 1.0
            vec[term] = tf * idf
        return vec

    vec_a = _vector(tokens_a)
    vec_b = _vector(tokens_b)

    dot = sum(vec_a.get(t, 0.0) * vec_b.get(t, 0.0) for t in vocab)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return max(0.0, min(1.0, dot / (norm_a * norm_b)))
