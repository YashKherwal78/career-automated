import json
import logging
from typing import List, Dict, Any, Optional
from src.api.db import json_extract

logger = logging.getLogger("JobRepository")


class JobRepository:
    def __init__(self, db):
        self.db = db

    # ── Pipeline filter objects (lazy-loaded, singleton per instance) ──────────

    @property
    def _profile(self):
        if not hasattr(self, "_cached_profile"):
            try:
                from src.discovery.jie.candidate_profile import CandidateProfile
                self._cached_profile = CandidateProfile.from_yaml()
            except Exception as e:
                logger.warning("JobRepository: CandidateProfile load failed: %s", e)
                from src.discovery.jie.candidate_profile import CandidateProfile
                self._cached_profile = CandidateProfile()
        return self._cached_profile

    @property
    def _hard_reject(self):
        if not hasattr(self, "_cached_hard_reject"):
            from src.discovery.hard_reject_filter import HardRejectFilter
            self._cached_hard_reject = HardRejectFilter()
        return self._cached_hard_reject

    @property
    def _intent_filter(self):
        if not hasattr(self, "_cached_intent_filter"):
            from src.discovery.intent_filter import IntentFilter
            self._cached_intent_filter = IntentFilter()
        return self._cached_intent_filter

    # ── Main query ─────────────────────────────────────────────────────────────

    def get_jobs(
        self,
        page: int = 1,
        page_size: int = 50,
        provider: str = None,
        company: str = None,
        status: str = "ACTIVE",
        min_score: float = None,
        pipeline: str = "A",
        location: str = None,
        remote_type: str = None,
        employment_type: str = None,
        seniority: str = None,
        min_salary: float = None,
        sort_by: str = "newest",
    ) -> List[Dict[str, Any]]:
        """
        Load jobs from DB → HardRejectFilter → JIE (IntentFilter) → Sort → Paginate → Return.

        Filtering happens BEFORE pagination so the page_size refers to eligible jobs,
        not raw DB rows.
        """
        c = self.db.cursor()

        # ── 1. Load candidate rows (no LIMIT/OFFSET yet) ─────────────────────
        query = f"""
            SELECT COALESCE(i.canonical_name, {json_extract('n.raw_payload_json', '$.company')}, n.company_id) AS canonical_name,
                   n.job_id, n.title, 0 as job_score, n.provider, '{{}}' as score_breakdown,
                   0.0 as match_score, 0.0 as priority_score, 0.0 as scoring_confidence,
                   '' as recommendation_reason, 'NEW' as application_status,
                   n.location, n.remote_type as remote, n.employment_type,
                   n.salary_min, n.salary_max, n.posted_at, n.apply_url,
                   n.description, n.status
            FROM normalized_jobs n
            LEFT JOIN company_identities i ON n.company_id = i.company_id
            WHERE n.status = ?
        """
        params: List[Any] = [status]

        # Pipeline separation: B = external boards, A = ATS
        job_board_providers = ["linkedin", "google_jobs", "wellfound", "indeed"]
        if pipeline == "B":
            query += " AND n.provider IN (" + ",".join(["?"] * len(job_board_providers)) + ")"
            params.extend(job_board_providers)
        else:
            query += " AND n.provider NOT IN (" + ",".join(["?"] * len(job_board_providers)) + ")"
            params.extend(job_board_providers)

        if provider:
            query += " AND n.provider = ?"
            params.append(provider)
        if company:
            query += f" AND (COALESCE(i.canonical_name, {json_extract('n.raw_payload_json', '$.company')}, '') LIKE ? OR n.title LIKE ?)"
            params.extend([f"%{company}%", f"%{company}%"])
        if location:
            query += " AND n.location LIKE ?"
            params.append(f"%{location}%")
        if remote_type:
            query += " AND n.remote_type = ?"
            params.append(remote_type)
        if employment_type:
            query += " AND n.employment_type = ?"
            params.append(employment_type)
        if min_salary is not None:
            query += " AND (n.salary_max >= ? OR n.salary_min >= ?)"
            params.extend([min_salary, min_salary])

        # Load all matching rows (up to a sane ceiling to protect memory)
        query += " ORDER BY n.posted_at DESC LIMIT 2000"
        c.execute(query, params)
        raw_jobs = [dict(row) for row in c.fetchall()]

        for j in raw_jobs:
            try:
                j["score_breakdown"] = json.loads(j["score_breakdown"] or "[]")
            except Exception:
                j["score_breakdown"] = []

        jobs_loaded = len(raw_jobs)

        # ── 2. HardRejectFilter (binary eligibility) ──────────────────────────
        profile = self._profile
        passed, rejected, rejection_counts = self._hard_reject.filter_batch(raw_jobs, profile)
        jobs_rejected = len(rejected)
        jobs_passed = len(passed)

        # ── 3. IntentFilter / JIE scoring ────────────────────────────────────
        # Only eligible jobs are scored (do NOT run JIE on rejected jobs)
        scored_jobs, score_metrics = self._intent_filter.score_batch(passed, profile)

        # Apply min_score filter post-JIE if requested
        if min_score is not None:
            scored_jobs = [j for j in scored_jobs if j.get("intent_score", 0.0) >= min_score / 100.0]

        # ── 4. Sort ───────────────────────────────────────────────────────────
        if sort_by == "score":
            scored_jobs.sort(key=lambda x: x.get("intent_score", 0.0), reverse=True)
        else:
            # newest first; fall back to intent_score as tiebreaker
            scored_jobs.sort(
                key=lambda x: (x.get("posted_at") or "", x.get("intent_score", 0.0)),
                reverse=True,
            )

        # ── 5. Paginate ───────────────────────────────────────────────────────
        offset = (page - 1) * page_size
        page_jobs = scored_jobs[offset : offset + page_size]

        logger.info(
            "JobRepository.get_jobs: loaded=%d, rejected=%d (eligible=%d), "
            "scored=%d, avg_score=%.3f, returned=%d | rejections=%s",
            jobs_loaded,
            jobs_rejected,
            jobs_passed,
            score_metrics["jobs_scored"],
            score_metrics["avg_intent_score"],
            len(page_jobs),
            rejection_counts,
        )

        return page_jobs

    # ── Single-job lookup (no filter chain — direct by ID) ────────────────────

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        c = self.db.cursor()
        c.execute(
            """
            SELECT COALESCE(i.canonical_name, json_extract(n.raw_payload_json, '$.company'), n.company_id) AS canonical_name,
                   n.job_id, n.title, 0 as job_score, n.provider, '{}' as score_breakdown,
                   0.0 as match_score, 0.0 as priority_score, 0.0 as scoring_confidence,
                   '' as recommendation_reason, 'NEW' as application_status,
                   n.description, n.location, n.remote_type as remote,
                   n.salary_min, n.salary_max, n.apply_url, n.posted_at
            FROM normalized_jobs n
            LEFT JOIN company_identities i ON n.company_id = i.company_id
            WHERE n.job_id = ?
            """,
            (job_id,),
        )
        row = c.fetchone()
        if not row:
            return None
        j = dict(row)
        try:
            j["score_breakdown"] = json.loads(j["score_breakdown"] or "[]")
        except Exception:
            j["score_breakdown"] = []
        return j
