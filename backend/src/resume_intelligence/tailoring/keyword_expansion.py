"""
Related-keyword expansion for ATS matching ("keyword stuffing", but gated
to genuinely adjacent skills only -- not free invention).

Problem: a JD asking for Azure gets zero ATS-keyword credit from a resume
that only lists AWS, even though cloud infra experience is obviously
transferable. The tailoring engine already measures keyword coverage
(engine_v1.py._compute_keyword_coverage) but never acts on the gap.

Design constraints, deliberately conservative:
  - Only ever ADD a keyword the candidate doesn't have, never remove or
    rewrite an existing one.
  - Only add when it's adjacent to a skill the candidate genuinely already
    has (same cluster below) -- this is not "does the JD want it", it's
    "is it a close neighbor of something real on this resume". A GCP-only
    candidate's resume can pick up "Azure" (same cloud cluster) but not
    "Kubernetes" just because a JD mentions it with no adjacency to
    anything the candidate actually lists.
  - Zero LLM calls. This is a static adjacency lookup, not a generative
    call -- deterministic, auditable, free, instant. (An embedding-based
    fallback for skills outside this map is a natural extension, not
    built tonight -- see module docstring bottom.)
  - Hard cap on additions per resume (default 3) -- the point is closing
    an obvious gap, not padding the skills section.
  - Every addition is returned with what it was added because of, for the
    diff log / provenance report, so it's visible and auditable, not a
    silent change.
  - Insertion is a pure string append onto an existing skill-category
    line already in the resume -- never a restructure or freehand LaTeX
    generation. If the expected line pattern isn't found, that addition
    is dropped rather than risking a malformed .tex.

Curated clusters below cover the areas real JDs most often penalize a
close-but-not-exact skill for (cloud, one language/framework family
misses another, common DB substitutes). Extend as new false-negatives
turn up in real coverage numbers -- this is meant to grow with use, not
be exhaustive on day one.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

SKILL_CLUSTERS: list[set[str]] = [
    {"aws", "amazon web services", "azure", "microsoft azure", "gcp", "google cloud", "google cloud platform"},
    {"docker", "kubernetes", "k8s", "containerization"},
    {"react", "reactjs", "react.js", "vue", "vuejs", "vue.js", "angular", "angularjs"},
    {"postgresql", "postgres", "mysql", "mariadb", "sql server", "oracle db"},
    {"mongodb", "dynamodb", "cassandra", "couchbase"},
    {"redis", "memcached"},
    {"tensorflow", "pytorch", "keras", "jax"},
    {"pandas", "numpy", "polars"},
    {"jenkins", "github actions", "gitlab ci", "circleci", "travis ci"},
    {"terraform", "cloudformation", "pulumi", "ansible"},
    {"rest api", "restful api", "graphql", "grpc"},
    {"langchain", "langgraph", "llamaindex", "crewai", "autogen"},
    {"java", "kotlin", "scala"},
    {"javascript", "typescript"},
    {"c++", "c", "rust"},
    {"jira", "linear", "asana", "trello"},
    {"figma", "sketch", "adobe xd"},
    {"tableau", "power bi", "looker", "metabase"},
    {"spark", "hadoop", "flink"},
    {"kafka", "rabbitmq", "sqs", "pubsub"},
]

MAX_ADDITIONS = 3


def _normalize(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def _cluster_for(term: str) -> Optional[set[str]]:
    """Real resume/JD skill strings are rarely the bare cluster term --
    "AWS EC2", "Amazon Web Services (AWS)", "React.js" all need to match
    their cluster ("aws", "react") via substring, not exact equality."""
    norm = _normalize(term)
    for cluster in SKILL_CLUSTERS:
        if any(_terms_match(norm, member) for member in cluster):
            return cluster
    return None


def _terms_match(a: str, b: str) -> bool:
    if a == b:
        return True
    # Word-boundary substring check both directions -- avoids "r" matching
    # "react" or "c" matching "c++"/"c#" style false positives that a bare
    # `in` check would produce.
    return bool(
        re.search(rf"\b{re.escape(b)}\b", a) or re.search(rf"\b{re.escape(a)}\b", b)
    )


@dataclass
class KeywordAddition:
    keyword: str          # exact JD phrasing to insert, e.g. "Azure"
    because_of: str        # the candidate's existing adjacent skill, e.g. "AWS"
    category_line: str     # the skills-block line it was appended to (for the diff log)


def find_related_keywords(
    candidate_skills: list[str],
    jd_required_skills: list[str],
    max_additions: int = MAX_ADDITIONS,
) -> list[KeywordAddition]:
    """Pure function, no I/O -- candidate_skills/jd_required_skills are
    plain strings (already-extracted skill names, not full sentences)."""
    candidate_norm = {_normalize(s) for s in candidate_skills}
    additions: list[KeywordAddition] = []

    for jd_skill in jd_required_skills:
        if len(additions) >= max_additions:
            break
        jd_norm = _normalize(jd_skill)
        if jd_norm in candidate_norm:
            continue  # already on the resume, nothing to add

        cluster = _cluster_for(jd_skill)
        if not cluster:
            continue  # no curated adjacency for this term -- skip, don't guess

        # Find which of the candidate's real skills is the neighbor that
        # justifies this addition (for provenance -- "added Azure because
        # candidate already has AWS", not just "seemed related").
        neighbor = next(
            (
                s for s in candidate_skills
                if _normalize(s) != jd_norm and any(_terms_match(_normalize(s), member) for member in cluster)
            ),
            None,
        )
        if not neighbor:
            continue

        additions.append(KeywordAddition(keyword=jd_skill, because_of=neighbor, category_line=""))

    return additions


# Matches one categorized skill line in the Jake-style resume format:
#   \textbf{Category:} skill1, skill2, skill3 \\
# or the last line in the block, which omits the trailing \\
_SKILL_LINE_RE = re.compile(
    r"(\\textbf\{[^}]*\}\s*[^\\\n]*?)(\s*\\\\|\s*\n\s*\}\})",
)


def compute_gap_report(
    candidate_skills: list[str],
    jd_required_skills: list[str],
    applied_additions: list[KeywordAddition],
) -> dict:
    """Deterministic (zero-LLM) breakdown of how well candidate_skills covers
    jd_required_skills: matched / adjacent (added to resume) / gap (nothing
    found, not added). This is plain comparison against the same
    SKILL_CLUSTERS adjacency table find_related_keywords already uses for
    additions -- never an LLM's self-report of its own coverage, which
    can't be trusted to faithfully admit what it didn't cover.

    "gaps" is the actionable output: JD requirements this resume genuinely
    doesn't support, surfaced honestly rather than silently invented or
    silently dropped."""
    applied_by_keyword = {_normalize(a.keyword): a for a in applied_additions}

    matched: list[dict] = []
    adjacent: list[dict] = []
    gaps: list[dict] = []

    for jd_skill in jd_required_skills:
        jd_norm = _normalize(jd_skill)
        if not jd_norm:
            continue
        # Word-boundary substring match both directions (same _terms_match
        # helper the cluster-adjacency path already uses), not bare set
        # membership -- a literal-equality-only check meant "llm" never
        # matched an existing "LLM APIs" skill, wrongly reporting a gap
        # the candidate's resume already covers. Confirmed live, 2026-08-22.
        exact_hit = next((s for s in candidate_skills if _terms_match(jd_norm, _normalize(s))), None)
        if exact_hit:
            matched.append({"jd_skill": jd_skill, "matched_to": exact_hit})
            continue
        if jd_norm in applied_by_keyword:
            a = applied_by_keyword[jd_norm]
            adjacent.append({
                "jd_skill": jd_skill,
                "adjacent_to": a.because_of,
                "added_to_resume": True,
                "note": f"candidate has {a.because_of}, not {jd_skill} -- review before submitting",
            })
            continue
        cluster = _cluster_for(jd_skill)
        neighbor = None
        if cluster:
            neighbor = next(
                (s for s in candidate_skills if any(_terms_match(_normalize(s), m) for m in cluster)),
                None,
            )
        if neighbor:
            adjacent.append({
                "jd_skill": jd_skill,
                "adjacent_to": neighbor,
                "added_to_resume": False,
                "note": f"candidate has {neighbor} (adjacent) but it wasn't added -- addition cap reached or skills line not found",
            })
        else:
            gaps.append({
                "jd_skill": jd_skill,
                "in_candidate_profile": False,
                "note": "no evidence chain -- not added, genuine gap",
            })

    return {"matched": matched, "adjacent": adjacent, "gaps": gaps}


def apply_keyword_additions(skills_block: str, additions: list[KeywordAddition]) -> tuple[str, list[KeywordAddition]]:
    """Appends each addition's keyword onto the skill-category line whose
    existing content contains `because_of` (case-insensitive substring
    match on the real .tex text, not the normalized form, since that's
    what's actually being edited). Returns (new_skills_block, applied) --
    `applied` only includes additions that actually found a matching line
    and were inserted; anything else is dropped silently rather than risk
    a malformed edit, and the caller should only report `applied` as real
    changes."""
    applied: list[KeywordAddition] = []
    updated = skills_block

    for addition in additions:
        lines = updated.split("\\\\")
        matched_idx = None
        for i, line in enumerate(lines):
            if addition.because_of.lower() in line.lower():
                matched_idx = i
                break
        if matched_idx is None:
            continue  # because_of skill not found verbatim in the block -- skip

        line = lines[matched_idx]
        # Guard against a line that doesn't look like a plain trailing
        # skill list (e.g. it's the very last line of the block, which
        # carries the closing `}}` -- handled separately below).
        if line.rstrip().endswith("}}"):
            continue

        lines[matched_idx] = line.rstrip() + f", {addition.keyword}"
        updated = "\\\\".join(lines)
        applied.append(KeywordAddition(keyword=addition.keyword, because_of=addition.because_of, category_line=line.strip()))

    return updated, applied
