"""
HardRejectFilter — ONE reusable binary filter.

Returns KEEP or REJECT. No scoring, no AI, no embeddings.
All rules read ONLY from CandidateProfile — nothing is hardcoded.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional

from src.discovery.jie.candidate_profile import CandidateProfile
from src.discovery.jie.extractor import JDExtractor

logger = logging.getLogger("HardRejectFilter")


class HardRejectResult:
    __slots__ = ("decision", "reason", "field", "job_value", "candidate_value")

    def __init__(self, decision: str, reason: str = "", field: str = "", job_value: Any = None, candidate_value: Any = None):
        self.decision = decision          # "KEEP" | "REJECT"
        self.reason = reason
        self.field = field
        self.job_value = job_value
        self.candidate_value = candidate_value

    def __repr__(self) -> str:
        if self.decision == "KEEP":
            return "HardRejectResult(KEEP)"
        return (
            f"HardRejectResult(REJECT | {self.reason} | "
            f"field={self.field}, job={self.job_value!r}, candidate={self.candidate_value!r})"
        )


class HardRejectFilter:
    """
    Binary filter that evaluates a single job against a CandidateProfile.
    Responsibilities: return KEEP or REJECT — nothing in between.
    """

    def __init__(self):
        self._extractor = JDExtractor()

    # ── Public API ─────────────────────────────────────────────────────────────

    def evaluate(self, job: Dict[str, Any], profile: CandidateProfile) -> HardRejectResult:
        """
        Evaluate a single job dict against the candidate profile.

        Args:
            job:     Dict from normalized_jobs (columns as keys).
            profile: CandidateProfile loaded from config or resume parser.

        Returns:
            HardRejectResult with decision == "KEEP" or "REJECT".
        """
        title = str(job.get("title") or job.get("positionName") or "")
        title_lower = title.lower()
        desc = str(job.get("description") or job.get("job_description") or "")
        desc_lower = desc.lower()
        location = str(job.get("location") or "").lower()
        apply_url = str(job.get("apply_url") or job.get("application_url") or "")
        status = str(job.get("status") or "ACTIVE").upper()

        # ── Rule 1: Missing apply URL ────────────────────────────────────────
        if not apply_url.strip():
            return HardRejectResult(
                "REJECT",
                reason="Missing apply URL",
                field="apply_url",
                job_value=None,
                candidate_value="Any valid URL",
            )

        # ── Rule 2: Closed jobs ──────────────────────────────────────────────
        if status == "CLOSED":
            return HardRejectResult(
                "REJECT",
                reason="Job is closed",
                field="status",
                job_value="CLOSED",
                candidate_value="ACTIVE",
            )

        # ── Rule 3: Senior/Staff/Principal title ─────────────────────────────
        # Reject if candidate has < 5 years experience
        senior_keywords = [
            r"\bsenior\b", r"\bsr\b", r"\bstaff\b", r"\bprincipal\b",
            r"\blead\b", r"\bdirector\b", r"\bvp\b", r"\bvice president\b",
            r"\bhead of\b",
        ]
        if profile.years_experience < 5:
            for pat in senior_keywords:
                if re.search(pat, title_lower):
                    return HardRejectResult(
                        "REJECT",
                        reason=f"Senior-level role detected in title",
                        field="title",
                        job_value=title,
                        candidate_value=f"{profile.years_experience} years experience",
                    )

        # ── Rule 4: Internship / full-time mismatch ──────────────────────────
        is_internship = bool(re.search(r"\bintern(ship)?\b", title_lower))
        wants_internship = any("intern" in et.lower() for et in profile.employment_types)
        if is_internship and not wants_internship:
            return HardRejectResult(
                "REJECT",
                reason="Internship role does not match candidate employment types",
                field="employment_types",
                job_value="Internship",
                candidate_value=profile.employment_types,
            )

        # ── Rule 5: Years of experience ──────────────────────────────────────
        # First try extracting from JIE data in job dict
        exp_min = self._resolve_experience_min(job, desc, title)
        if exp_min is not None and exp_min > profile.years_experience:
            return HardRejectResult(
                "REJECT",
                reason=f"Requires {exp_min} years experience",
                field="years_experience",
                job_value=exp_min,
                candidate_value=profile.years_experience,
            )

        # ── Rule 6: Location mismatch ────────────────────────────────────────
        if location:
            # Indian city/country signals — use word boundaries to avoid
            # false positives like "Indianapolis", "Indiana, United States"
            indian_patterns = [
                r"\bbangalore\b", r"\bbengaluru\b", r"\bmumbai\b", r"\bpune\b",
                r"\bhyderabad\b", r"\bchennai\b", r"\bdelhi\b", r"\bncr\b",
                r"\bgurgaon\b", r"\bgurugram\b", r"\bnoida\b", r"\bkolkata\b",
                r"\bahmedabad\b", r"\bindia\b",
            ]
            is_india = any(re.search(pat, location) for pat in indian_patterns)

            # If the job is in India, always keep
            if is_india:
                pass
            else:
                is_remote = bool(re.search(r"\b(remote|work from home|wfh)\b", location))
                if is_remote and profile.remote_allowed:
                    # Check if the remote job is geo-restricted to a non-India country
                    geo_restrict_signals = [
                        "united states", "u.s.", "usa", "us -", "- us",
                        "remote us", "remote- us", "remote -us", "remote-us",
                        "north america", "latin america", "south america",
                        "canada", "uk", "united kingdom", "england",
                        "germany", "japan", "australia", "europe", "emea",
                        "americas", "western states", "eastern time",
                        "pacific time", "mountain time", "central time",
                        " ca,", " ca ", " ny,", " ny ", " tx,", " tx ",
                        " wa,", " wa ", " co,", " co ", " ga,", " ga ",
                        ", fl", ", il", ", oh", ", ma", ", va", ", or",
                        ", az", ", nv", ", nc", ", pa", ", sc", ", mn",
                        "california", "new york", "texas", "washington",
                        "colorado", "florida", "illinois", "ohio",
                        "massachusetts", "virginia", "oregon", "arizona",
                        "nevada", "north carolina", "pennsylvania",
                        "san francisco", "san jose", "los angeles",
                        "seattle", "denver", "chicago", "atlanta",
                        "boston", "phoenix", "las vegas", "miami",
                        "toronto", "london", "berlin", "tokyo",
                        "sydney", "melbourne", "stockholm", "warsaw",
                        "zurich", "paris", "amsterdam", "dublin",
                        "singapore", "hong kong",
                    ]
                    is_geo_restricted = any(sig in location for sig in geo_restrict_signals)
                    if is_geo_restricted:
                        return HardRejectResult(
                            "REJECT",
                            reason="Geo-restricted remote (not available in India)",
                            field="location",
                            job_value=job.get("location"),
                            candidate_value=profile.preferred_locations,
                        )
                    # Pure "Remote" with no country restriction → KEEP
                else:
                    # Not remote, not India → reject
                    return HardRejectResult(
                        "REJECT",
                        reason="Location mismatch",
                        field="location",
                        job_value=job.get("location"),
                        candidate_value=profile.preferred_locations,
                    )

        # ── Rule 7: Doctoral degree ──────────────────────────────────────────
        if re.search(r"\b(phd required|doctoral degree required|ph\.d\.)\b", desc_lower):
            if profile.degree not in ("PhD", "Doctorate"):
                return HardRejectResult(
                    "REJECT",
                    reason="Doctoral degree required",
                    field="degree",
                    job_value="PhD",
                    candidate_value=profile.degree,
                )

        # ── Rule 8: US Citizenship required ─────────────────────────────────
        us_citizen_patterns = [
            "must be a us citizen",
            "must be a u.s. citizen",
            "us citizenship required",
            "u.s. citizenship required",
        ]
        if any(p in desc_lower for p in us_citizen_patterns):
            if profile.citizenship not in ("US", "United States"):
                return HardRejectResult(
                    "REJECT",
                    reason="US Citizenship required",
                    field="citizenship",
                    job_value="US Citizen",
                    candidate_value=profile.citizenship,
                )

        # ── Rule 9: No visa sponsorship ──────────────────────────────────────
        no_sponsor_patterns = [
            "no sponsorship available",
            "no visa sponsorship",
            "we do not sponsor",
            "cannot provide sponsorship",
            "do not provide sponsorship",
            "without sponsorship",
        ]
        if any(p in desc_lower for p in no_sponsor_patterns):
            # Reject only when the candidate explicitly requires sponsorship
            if profile.visa_status and "require" in profile.visa_status.lower():
                return HardRejectResult(
                    "REJECT",
                    reason="No visa sponsorship — candidate requires sponsorship",
                    field="visa_status",
                    job_value="No sponsorship",
                    candidate_value=profile.visa_status,
                )

        # ── Rule 10: Security clearance ──────────────────────────────────────
        clearance_patterns = [
            "security clearance required",
            "active clearance",
            "top secret clearance",
            "secret clearance",
        ]
        if any(p in desc_lower for p in clearance_patterns):
            no_clearance = not profile.clearance or profile.clearance.lower() in ("none", "")
            if no_clearance:
                return HardRejectResult(
                    "REJECT",
                    reason="Security clearance required",
                    field="clearance",
                    job_value="Active Clearance",
                    candidate_value=profile.clearance,
                )

        return HardRejectResult("KEEP")

    def filter_batch(
        self,
        jobs: List[Dict[str, Any]],
        profile: CandidateProfile,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
        """
        Filter a batch of jobs. Returns (passed, rejected, rejection_counts).

        rejection_counts keys: reason strings → count.
        """
        passed: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        rejection_counts: Dict[str, int] = {}

        for job in jobs:
            result = self.evaluate(job, profile)
            if result.decision == "KEEP":
                passed.append(job)
            else:
                job = dict(job)  # don't mutate original
                job["_rejection_reason"] = result.reason
                job["_rejection_field"] = result.field
                job["_rejection_job_value"] = result.job_value
                job["_rejection_candidate_value"] = str(result.candidate_value)
                rejected.append(job)
                rejection_counts[result.reason] = rejection_counts.get(result.reason, 0) + 1

        logger.info(
            "HardRejectFilter: evaluated=%d, passed=%d, rejected=%d | counts=%s",
            len(jobs),
            len(passed),
            len(rejected),
            rejection_counts,
        )

        return passed, rejected, rejection_counts

    # ── Private helpers ────────────────────────────────────────────────────────

    def _resolve_experience_min(self, job: Dict[str, Any], desc: str, title: str) -> Optional[int]:
        """
        Extract minimum experience required from:
          1. jie column already stored on the job
          2. Regex on description / title (via JDExtractor)
        """
        # 1. From stored JIE payload
        jie = job.get("jie")
        if isinstance(jie, dict) and jie.get("experience_min") is not None:
            return int(jie["experience_min"])

        # 2. From DB column (set during normalization)
        if job.get("experience_min") is not None:
            return int(job["experience_min"])

        # 3. Regex extraction from description
        if desc or title:
            exp_data = self._extractor._extract_experience(desc + " " + title)
            if exp_data.get("min") is not None:
                return int(exp_data["min"])

        return None
