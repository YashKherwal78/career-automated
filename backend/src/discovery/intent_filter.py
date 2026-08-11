"""
IntentFilter — wraps JIE (JDExtractor + FitAnalyzer) to score jobs.

This is the existing JIE integration layer. It:
  1. Runs JDExtractor on job descriptions → StructuredJob
  2. Runs FitAnalyzer against CandidateProfile → CandidateFit
  3. Returns scored jobs with intent_score (0.0–1.0)

Do NOT modify JIE internals (extractor.py, analyzer.py, models.py).
"""

import logging
from typing import Any, Dict, List, Tuple

from src.discovery.jie.extractor import JDExtractor
from src.discovery.jie.normalizer import Normalizer
from src.discovery.jie.analyzer import FitAnalyzer
from src.discovery.jie.analyzer import CandidateProfile as JIECandidateProfile
from src.discovery.jie.candidate_profile import CandidateProfile
from src.discovery.text_similarity import cosine_similarity

logger = logging.getLogger("IntentFilter")


def _build_jie_profile(profile: CandidateProfile, normalizer: Normalizer) -> JIECandidateProfile:
    """
    Bridge: CandidateProfile (real per-user data) → JIE's internal CandidateProfile
    (pydantic). Only adapts the interface; JIE internals are untouched.

    Candidate skills are run through the same synonym normalizer applied to
    JD-extracted skill names (see Normalizer.normalize()) — without this, a
    resume listing "ReactJS" would never match a JD requirement canonicalized
    to "React", even though both mean the same thing.
    """
    return JIECandidateProfile(
        role_families=profile.target_roles,
        experience_years=profile.years_experience,
        skills=normalizer.normalize_skill_list(profile.skills),
        preferred_locations=profile.preferred_locations,
        remote=profile.remote_allowed,
        employment=profile.employment_types,
    )


class IntentFilter:
    """
    JIE integration layer used by the jobs repository to score eligible jobs.

    Usage:
        filter = IntentFilter()
        scored_jobs, metrics = filter.score_batch(jobs, profile)

    Each job in scored_jobs gets two new keys:
        intent_score (float 0.0–1.0): overall_fit_score from FitAnalyzer
        score_breakdown (list[dict]): matched/missing skill details for the frontend
    """

    def __init__(self):
        self._extractor = JDExtractor()
        self._normalizer = Normalizer()

    def score_job(self, job: Dict[str, Any], profile: CandidateProfile) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Score a single job using the existing JIE.

        Returns:
            (intent_score, score_breakdown)
            intent_score: float 0.0–1.0
            score_breakdown: list of {"keyword": str, "matched": bool}
        """
        title = str(job.get("title") or "")
        title_lower = title.lower()
        desc = str(job.get("description") or job.get("job_description") or "")
        has_desc = len(desc.strip()) > 100  # only trust JIE when there is meaningful text

        # ── Role-family title score (primary signal when no description) ──────
        # Check if the title matches the candidate's target roles.
        role_score = self._title_role_score(title_lower, profile)

        if not has_desc:
            # No description: base the score entirely on title relevance
            return role_score, []

        try:
            # Step 1: JDExtractor → StructuredJob
            structured = self._extractor.extract(title=title, jd_text=desc)
            # Step 2: Normalizer → canonicalize skill names
            structured = self._normalizer.normalize(structured)
            # Step 3: FitAnalyzer → CandidateFit
            jie_profile = _build_jie_profile(profile, self._normalizer)
            analyzer = FitAnalyzer(jie_profile)
            fit = analyzer.analyze(structured)

            # Step 4: Responsibility overlap — deterministic TF-IDF cosine
            # similarity between the candidate's experience/project text and
            # the JD's responsibilities. Catches relevant work that skill-list
            # matching alone misses (no LLM call, no embedding model).
            responsibilities_text = " ".join(structured.responsibilities)
            resp_score = (
                cosine_similarity(profile.experience_text, responsibilities_text)
                if responsibilities_text and profile.experience_text
                else None
            )

            # analyzer.py's coverage (and experience-fit) both default to 1.0
            # when there's nothing to evaluate against — total_req==0 means
            # "no disagreement found" gets scored identically to "every
            # requirement matched". Confirmed live: a German-language JD the
            # extractor pulled zero skill requirements from scored a perfect
            # fit.overall_fit_score=1.0 despite zero actual matched skills.
            # Don't blend that meaningless "1.0" in as real signal — fall
            # back to the independently-computed role/responsibility signals.
            required_skill_count = sum(
                1 for r in structured.requirements
                if r.type == "skill" and r.importance == "REQUIRED"
            )
            trust_fit_score = required_skill_count > 0

            if resp_score is None:
                combined = (
                    fit.overall_fit_score * 0.60 + role_score * 0.40
                    if trust_fit_score
                    else role_score
                )
            else:
                combined = (
                    fit.overall_fit_score * 0.45 + role_score * 0.25 + resp_score * 0.30
                    if trust_fit_score
                    else role_score * 0.40 + resp_score * 0.60
                )

            # Build score_breakdown for frontend (matches {keyword, matched} contract)
            breakdown = []
            for req in structured.requirements:
                if req.type == "skill":
                    matched = req.name in fit.skills.matched
                    breakdown.append({"keyword": req.name, "matched": matched})

            return min(1.0, max(0.0, combined)), breakdown

        except Exception as e:
            logger.debug("IntentFilter: JIE failed for job %r: %s", title, e)
            return role_score, []  # fallback to title-only on JIE failure

    # ── Role-family title scorer ───────────────────────────────────────────────

    # Keywords that boost the title score for each target role family
    _ROLE_SIGNALS: Dict[str, List[str]] = {
        "associate product manager": ["associate product", "apm"],
        "product manager": ["product manager", "pm ", " pm,"],
        "product analyst": ["product analyst"],
        "founder's office": ["founder", "chief of staff", "cxo"],
        "chief of staff": ["chief of staff"],
        "ai engineer": ["ai engineer", "applied ai", "genai", "llm engineer"],
        "machine learning engineer": ["machine learning", "ml engineer"],
        "software engineer": ["software engineer", "sde", "swe"],
        "data scientist": ["data scientist"],
    }

    # Title keywords that strongly indicate a wrong-domain role
    _WRONG_DOMAIN_SIGNALS = [
        "account executive", "sales", "recruiter", "marketing",
        "hr ", "nurse", "doctor", "dentist", "chef", "driver", "plumber",
    ]

    # Words that carry no role-matching signal on their own — stripped before
    # token-overlap comparison so "AI Product Manager Intern" (a real resume
    # experience title, not a curated role family) still meaningfully matches
    # "Product Manager" postings instead of only ever hitting the 0.0/0.3
    # exact-substring paths below.
    _ROLE_STOPWORDS = {
        "intern", "internship", "the", "a", "of", "and", "at", "for", "to",
        "senior", "junior", "sr", "jr", "i", "ii", "iii",
    }

    def _title_role_score(self, title_lower: str, profile: CandidateProfile) -> float:
        """Return 0.0–1.0 based on how well the job title matches target roles."""
        # Hard penalty for obvious wrong-domain titles
        if any(wd in title_lower for wd in self._WRONG_DOMAIN_SIGNALS):
            return 0.05

        title_tokens = set(title_lower.replace(",", " ").replace("/", " ").split())

        best = 0.0
        for role in profile.target_roles:
            role_lower = role.lower()
            signals = self._ROLE_SIGNALS.get(role_lower, [role_lower])
            for sig in signals:
                if sig in title_lower:
                    best = 1.0
                    break
            if best >= 1.0:
                break

            # Curated dict/exact-phrase match missed (e.g. a resume-derived
            # role like "AI Product Manager Intern" that isn't a canonical
            # role family) — fall back to token overlap: how many of the
            # role's meaningful words actually show up in this title.
            role_tokens = {
                t for t in role_lower.replace(",", " ").split() if t not in self._ROLE_STOPWORDS
            }
            # Require at least 2 meaningful tokens before trusting the
            # overlap ratio. A role like "Engineering Intern" strips down to
            # the single token {"engineering"} once "intern" is removed as a
            # stopword — with only one token, any title containing that one
            # generic word scores a "100% overlap" (e.g. Civil Engineering
            # Analyst, Naval Architecture and Marine Engineering, Electrical
            # Engineering Technician all matched an AI/SWE candidate this
            # way). A single generic word isn't enough signal on its own.
            if len(role_tokens) >= 2:
                overlap = len(role_tokens & title_tokens) / len(role_tokens)
                # Require real overlap (not just one generic shared word) to
                # avoid the same noise the plain generic-keyword check below
                # already causes on its own.
                if overlap >= 0.6:
                    best = max(best, 0.85)
                elif overlap >= 0.34:
                    best = max(best, 0.5)

        # Partial match — title shares a profession noun with one of the
        # candidate's own target roles (e.g. target "Software Engineer" ->
        # generic credit for "Engineer" titles). Previously this used a fixed
        # ["engineer", "analyst", "manager", "developer", "scientist"] list
        # regardless of the candidate's actual targets, so an AI/ML/SWE
        # candidate got 0.3 for "Territory Manager" or "Business Analyst"
        # postings purely because those titles contain "manager"/"analyst" —
        # words that carry zero signal outside the roles the candidate
        # actually targets.
        if best == 0.0:
            target_profession_words = {
                role.lower().split()[-1]
                for role in profile.target_roles
                if role.strip()
            } & {"engineer", "analyst", "manager", "developer", "scientist"}
            if any(g in title_lower for g in target_profession_words):
                best = 0.3  # plausible but not targeted

        return best

    # Minimum title role-score to even be considered for JD-based scoring.
    # Excludes the weak generic-profession-noun bucket (0.3) and the
    # wrong-domain penalty (0.05) — only a real signal/token-overlap title
    # match (>=0.5) earns a shot at JD scoring. Without this gate, JD text
    # alone (acronym collisions like clinical "GCP" vs. cloud "GCP", or
    # analyzer defaults that assume unstated requirements are satisfied) can
    # pull a completely off-domain job up to a misleadingly high score.
    TITLE_FILTER_THRESHOLD = 0.5

    def score_batch(
        self,
        jobs: List[Dict[str, Any]],
        profile: CandidateProfile,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Score a batch of jobs that already passed HardRejectFilter.

        Two stages: (1) title-only role match filters out jobs whose title
        doesn't plausibly belong to one of the candidate's target roles, (2)
        only surviving jobs get the full JD-based score.

        Returns:
            (scored_jobs, metrics)
            scored_jobs: list of jobs with intent_score and score_breakdown added
            metrics: {"jobs_scored": int, "avg_intent_score": float, "jobs_title_filtered": int}
        """
        title_filtered = 0
        candidates = []
        for job in jobs:
            title_lower = str(job.get("title") or "").lower()
            role_score = self._title_role_score(title_lower, profile)
            if role_score < self.TITLE_FILTER_THRESHOLD:
                title_filtered += 1
                continue
            candidates.append(job)

        scored = []
        total_score = 0.0

        for job in candidates:
            intent_score, breakdown = self.score_job(job, profile)
            j = dict(job)
            j["intent_score"] = round(intent_score, 4)
            # Preserve existing score_breakdown list format if already set, else use JIE breakdown
            if not j.get("score_breakdown"):
                j["score_breakdown"] = breakdown
            scored.append(j)
            total_score += intent_score

        n = len(scored)
        avg = round(total_score / n, 4) if n > 0 else 0.0

        logger.info(
            "IntentFilter: title_filtered=%d, scored=%d, avg_intent_score=%.3f",
            title_filtered,
            n,
            avg,
        )

        return scored, {"jobs_scored": n, "avg_intent_score": avg, "jobs_title_filtered": title_filtered}

    # ── Legacy compatibility ───────────────────────────────────────────────────
    # Scratch scripts call filter_opportunities(jobs, task) — keep signature.

    def filter_opportunities(
        self,
        jobs: List[Dict[str, Any]],
        task: Any = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Legacy interface used by scratch scripts.
        Returns (passed, rejected, metrics) — scoring done in-place on passed.
        """
        profile = CandidateProfile.from_yaml()
        from src.discovery.hard_reject_filter import HardRejectFilter
        hrf = HardRejectFilter()
        passed, rejected, rejection_counts = hrf.filter_batch(jobs, profile)
        scored, score_metrics = self.score_batch(passed, profile)

        metrics = {
            "jobs_loaded": len(jobs),
            "jobs_rejected": len(rejected),
            "jobs_passed": len(passed),
            "jobs_scored": score_metrics["jobs_scored"],
            "avg_intent_score": score_metrics["avg_intent_score"],
            "rejection_counts": rejection_counts,
        }
        return scored, rejected, metrics
