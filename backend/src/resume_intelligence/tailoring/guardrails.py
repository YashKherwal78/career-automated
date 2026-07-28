"""
Guardrails — IntegrityGate and PolicyGate.

Two separate gates with separate responsibilities (change #1):

IntegrityGate — "Is this still the same resume?"
  Checks structure, locked fields, factual entities, macro restoration.
  Any failure → HardBlockError. The tailored output is discarded.

PolicyGate — "Is this a good tailored resume?"
  Checks resume-writing quality against resume_knowledge2 policy rules.
  Errors → revert affected bullets. Warnings → log only.

FactualEntityExtractor — extracts all factual entities from base .tex
  for use by IntegrityGate (change #4 + #5).

StructuralGuardLock — pre-rewrite snapshot of LaTeX command counts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set

from src.resume_intelligence.tailoring.models_v1 import (
    FactualEntitySet,
    HardBlockError,
    IntegrityReport,
    PolicyReport,
    StructuralSnapshot,
)


# ---------------------------------------------------------------------------
# Technology / proper-noun vocabulary (seeded from resume_knowledge2 ontology)
# These are the factual entities we protect from silent LLM substitution.
# ---------------------------------------------------------------------------

_KNOWN_TECHNOLOGIES: FrozenSet[str] = frozenset({
    # Languages
    "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "Kotlin",
    "Swift", "C", "C++", "C#", "Ruby", "PHP", "Scala", "Dart", "R", "Julia",
    # Frameworks / libs
    "FastAPI", "Django", "Flask", "React", "Vue", "Angular", "Next.js",
    "LangChain", "LangGraph", "Pydantic", "SQLAlchemy", "Celery",
    "React Native", "Flutter", "EAS", "Expo",
    # AI / ML
    "LLaMA", "Groq", "OpenAI", "Gemini", "Anthropic", "PyTorch", "TensorFlow",
    "Keras", "Scikit-learn", "HuggingFace", "BERT", "GPT", "RAG", "BGE-M3",
    "AstraDB", "ChromaDB", "Pinecone", "Qdrant", "Weaviate",
    # Infra / cloud
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "EC2", "S3", "Lambda",
    "Terraform", "Ansible", "Helm", "Nginx", "Gunicorn", "Uvicorn",
    # Databases
    "PostgreSQL", "MySQL", "SQLite", "Redis", "MongoDB", "Cassandra",
    "DynamoDB", "Firestore", "Supabase", "PlanetScale",
    # Other tools
    "Playwright", "Selenium", "Kafka", "RabbitMQ", "Celery", "GraphQL",
    "gRPC", "Tesseract", "IMAP", "SMTP", "Pandas", "NumPy", "Spark",
    "Airflow", "dbt", "Looker", "Tableau", "Figma",
    # Specific project tech from base resume
    "AstraDB", "BM25", "EUROCONTROL", "ASTERIX", "CAT048",
})

# Regex patterns for metric extraction (standalone numbers, percentages, currency, time)
_METRIC_PATTERN = re.compile(
    r"""
    (?<![A-Za-z0-9_-])  # lookbehind: not preceded by alphanumeric or hyphen/underscore
    (?:
        \d{1,3}(?:,\d{3})+          # 10,000+
        (?:\.\d+)?
        (?:\s*[%xX×+])?
    |
        \d+(?:\.\d+)?\s*%            # 80%, 99.9%
    |
        \$\d+(?:\.\d+)?\s*[KMB]?     # $50K, $2M
    |
        \d+\s*(?:ms|s|min|hrs?|days?|mos?|yrs?|years?|minutes?)  # 2s, 10 minutes, 0 days
    |
        \sim\d+%?                    # ~80%
    |
        \d+\+                        # 500+, 10+
    )
    (?![A-Za-z0-9_-])  # lookahead: not followed by alphanumeric or hyphen/underscore
    """,
    re.VERBOSE | re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"""
    (?:
        (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}  # Jan 2024
    |
        \d{4}\s*--\s*\d{4}           # 2022 -- 2026
    |
        \d{4}\s*--\s*Present         # 2024 -- Present
    |
        (?:Q[1-4]\s+\d{4})           # Q1 2025
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Factual Entity Extractor
# ---------------------------------------------------------------------------

class FactualEntityExtractor:
    """
    Extracts factual entities from raw .tex before tailoring.
    Operates on the full .tex string; does not require a parsed tree.
    """

    def extract(self, tex: str) -> FactualEntitySet:
        """
        Extract all protected factual entity categories.
        Returns a FactualEntitySet for use in IntegrityGate.
        """
        return FactualEntitySet(
            companies=self._extract_companies(tex),
            dates=self._extract_dates(tex),
            universities=self._extract_universities(tex),
            technologies=self._extract_technologies(tex),
            metrics=self._extract_metrics(tex),
            locations=frozenset(),  # locations not on base resume — skip
            awards=frozenset(),
            certifications=frozenset(),
            proper_nouns=frozenset(),  # covered by companies + tech
        )

    def _extract_companies(self, tex: str) -> FrozenSet[str]:
        """Extract from \\resumeSubheading{COMPANY}{...}{...}{...}."""
        companies: Set[str] = set()
        for m in re.finditer(r"\\resumeSubheading\s*\{([^}]+)\}", tex):
            companies.add(m.group(1).strip())
        return frozenset(companies)

    def _extract_dates(self, tex: str) -> FrozenSet[str]:
        return frozenset(m.group(0).strip() for m in _DATE_PATTERN.finditer(tex))

    def _extract_universities(self, tex: str) -> FrozenSet[str]:
        """Extract from Education section \\resumeSubheading."""
        # Simple heuristic: subheadings containing 'University', 'Institute', 'College'
        unis: Set[str] = set()
        for m in re.finditer(r"\\resumeSubheading\s*\{([^}]+)\}", tex):
            val = m.group(1).strip()
            if any(k in val for k in ("University", "Institute", "College", "IIT", "NIT")):
                unis.add(val)
        return frozenset(unis)

    def _extract_technologies(self, tex: str) -> FrozenSet[str]:
        """
        Find known technology names present in the .tex.
        We check the full tex, including Skills and Projects sections.
        """
        found: Set[str] = set()
        for tech in _KNOWN_TECHNOLOGIES:
            # Word-boundary check (case-sensitive — 'Redis' ≠ 'redis')
            if re.search(r"\b" + re.escape(tech) + r"\b", tex):
                found.add(tech)
        return frozenset(found)

    def _extract_metrics(self, tex: str) -> FrozenSet[str]:
        """Extract all numeric/metric tokens from bullet and summary content."""
        if "\\resumeItem{" in tex:
            bullet_contents = re.findall(r"\\resumeItem\{([^}]+)\}", tex)
        else:
            bullet_contents = [tex]

        metrics: Set[str] = set()
        for b in bullet_contents:
            for m in _METRIC_PATTERN.finditer(b):
                metrics.add(m.group(0).strip())
        return frozenset(metrics)


# ---------------------------------------------------------------------------
# Structural Guard Lock
# ---------------------------------------------------------------------------

class StructuralGuardLock:
    """
    Takes a pre-rewrite snapshot of LaTeX command counts.
    These counts must be identical in the tailored .tex.
    """

    # LaTeX commands whose counts are protected
    _COUNTED_COMMANDS = {
        "section": r"\\section\{",
        "resumeItem": r"\\resumeItem\{",
        "resumeSubheading": r"\\resumeSubheading",
        "resumeProjectHeading": r"\\resumeProjectHeading",
    }

    def snapshot(self, tex: str) -> StructuralSnapshot:
        counts = {k: len(re.findall(p, tex)) for k, p in self._COUNTED_COMMANDS.items()}

        # Per-section bullet counts
        bullet_per_section: Dict[str, int] = {}
        section_names = re.findall(r"\\section\{([^}]+)\}", tex)
        for i, sec_name in enumerate(section_names):
            # Slice tex between this section header and the next
            sec_start = tex.find(f"\\section{{{sec_name}}}")
            if i + 1 < len(section_names):
                next_sec = tex.find(f"\\section{{{section_names[i+1]}}}", sec_start + 1)
            else:
                next_sec = len(tex)
            sec_body = tex[sec_start:next_sec]
            bullet_per_section[sec_name] = len(re.findall(r"\\resumeItem\{", sec_body))

        # Locked field tokens: company names and project names
        locked_tokens: Set[str] = set()
        for m in re.finditer(r"\\resumeSubheading\s*\{([^}]+)\}", tex):
            locked_tokens.add(m.group(1).strip())
        for m in re.finditer(r"\\resumeProjectHeading\s*\{([^}]+)\}", tex):
            # Project heading contains "Title | tech" — take the whole string
            locked_tokens.add(m.group(1).strip())

        return StructuralSnapshot(
            section_count=counts["section"],
            resumeitem_count=counts["resumeItem"],
            resumesubheading_count=counts["resumeSubheading"],
            resumeprojectheading_count=counts["resumeProjectHeading"],
            bullet_count_per_section=bullet_per_section,
            locked_field_tokens=frozenset(locked_tokens),
        )


# ---------------------------------------------------------------------------
# Integrity Gate — "Is this still the same resume?"
# ---------------------------------------------------------------------------

class IntegrityGate:
    """
    Runs structural + factual checks on the tailored .tex.
    Any failure appends to violations. Caller raises HardBlockError if violations exist.

    Check order mirrors validation_rules.yaml run_order:
      locked_field_integrity → metric_grounding → entity_grounding →
      command_count_integrity → section_count_integrity → macro_restoration
    """

    def check(
        self,
        original_tex: str,
        tailored_tex: str,
        before_snap: StructuralSnapshot,
        entity_set: FactualEntitySet,
    ) -> IntegrityReport:
        report = IntegrityReport()
        violations: List[str] = []

        # 1. Locked field integrity — every locked token must appear in tailored
        for token in before_snap.locked_field_tokens:
            if token and token not in tailored_tex:
                violations.append(f"LOCKED_FIELD_MISSING: '{token}' not found in tailored output")
                report.locked_fields_intact = False

        # 2. Factual entity preservation — technologies must not be swapped
        for tech in entity_set.technologies:
            if tech not in tailored_tex:
                violations.append(f"ENTITY_MISSING: technology '{tech}' disappeared from tailored output")
                report.factual_entities_preserved = False

        # 3. Metric preservation — every numeric value from original must be in tailored
        for metric in entity_set.metrics:
            if metric:
                raw_num = metric.rstrip("+").lstrip("~")
                if metric not in tailored_tex and raw_num not in tailored_tex:
                    violations.append(f"METRIC_MISSING: '{metric}' not found in tailored output")
                    report.factual_entities_preserved = False

        # 4. Command count integrity
        after_snap = StructuralGuardLock().snapshot(tailored_tex)

        if after_snap.resumeitem_count != before_snap.resumeitem_count:
            violations.append(
                f"COMMAND_COUNT: \\resumeItem count changed "
                f"{before_snap.resumeitem_count} → {after_snap.resumeitem_count}"
            )
            report.resumeitem_count_unchanged = False

        if after_snap.resumesubheading_count != before_snap.resumesubheading_count:
            violations.append(
                f"COMMAND_COUNT: \\resumeSubheading count changed "
                f"{before_snap.resumesubheading_count} → {after_snap.resumesubheading_count}"
            )
            report.resumesubheading_count_unchanged = False

        if after_snap.resumeprojectheading_count != before_snap.resumeprojectheading_count:
            violations.append(
                f"COMMAND_COUNT: \\resumeProjectHeading count changed "
                f"{before_snap.resumeprojectheading_count} → {after_snap.resumeprojectheading_count}"
            )
            report.resumeprojectheading_count_unchanged = False

        # 5. Section count integrity
        if after_snap.section_count != before_snap.section_count:
            violations.append(
                f"SECTION_COUNT: changed {before_snap.section_count} → {after_snap.section_count}"
            )
            report.section_count_unchanged = False

        if after_snap.bullet_count_per_section != before_snap.bullet_count_per_section:
            for sec, orig_count in before_snap.bullet_count_per_section.items():
                new_count = after_snap.bullet_count_per_section.get(sec, -1)
                if new_count != orig_count:
                    violations.append(
                        f"BULLET_COUNT[{sec}]: changed {orig_count} → {new_count}"
                    )
                    report.bullet_count_unchanged = False

        # 6. Macro restoration check — no __PLACEHOLDER__ should remain
        unrestored = re.findall(r"__[A-Z]+_\d+__", tailored_tex)
        if unrestored:
            violations.append(
                f"UNRESTORED_MACROS: {unrestored[:5]} still present in tailored output"
            )
            report.macros_restored = False

        report.violations = violations
        return report


# ---------------------------------------------------------------------------
# Policy Gate — "Is this a good tailored resume?"
# ---------------------------------------------------------------------------

_BANNED_PHRASES = [
    "responsible for",
    "worked on",
    "helped with",
    "duties included",
    "in charge of",
    "was tasked with",
    "assisted with",
    "in order to",
    "successfully",
    "was involved in",
]

_MAX_BULLET_WORDS = 28
_MAX_SUMMARY_LINES = 3
_MAX_KEYWORD_DENSITY = 2  # per section


class PolicyGate:
    """
    Enforces resume_knowledge2 writing quality rules independently of structure.
    Errors → revert affected bullet. Warnings → log only.
    """

    def __init__(self, jd_keywords: Optional[List[str]] = None):
        self.jd_keywords = [k.lower() for k in (jd_keywords or [])]

    def check(
        self,
        tailored_tex: str,
        summary: Optional[str],
        bullets_by_section: Dict[str, List[str]],
    ) -> PolicyReport:
        report = PolicyReport()
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Summary length
        if summary:
            lines = [ln.strip() for ln in summary.split("\n") if ln.strip()]
            if len(lines) > _MAX_SUMMARY_LINES:
                errors.append(
                    f"SUMMARY_TOO_LONG: {len(lines)} lines, max {_MAX_SUMMARY_LINES}"
                )
                report.summary_length_ok = False

        # 2. Bullet length + banned phrases
        all_ok = True
        for section, bullets in bullets_by_section.items():
            for i, bullet in enumerate(bullets):
                word_count = len(bullet.split())
                if word_count > _MAX_BULLET_WORDS:
                    errors.append(
                        f"BULLET_TOO_LONG [{section}][{i}]: {word_count} words, max {_MAX_BULLET_WORDS}"
                    )
                    all_ok = False

                lower = bullet.lower()
                for phrase in _BANNED_PHRASES:
                    if phrase in lower:
                        errors.append(
                            f"BANNED_PHRASE [{section}][{i}]: '{phrase}'"
                        )
                        all_ok = False
        report.bullet_lengths_ok = all_ok

        # 3. Keyword stuffing — no keyword > 2× in any single section
        for section, bullets in bullets_by_section.items():
            section_text = " ".join(bullets).lower()
            for kw in self.jd_keywords:
                count = section_text.count(kw)
                if count > _MAX_KEYWORD_DENSITY:
                    errors.append(
                        f"KEYWORD_STUFFING [{section}]: '{kw}' appears {count}× (max {_MAX_KEYWORD_DENSITY})"
                    )
                    report.no_keyword_stuffing = False

        # 4. XYZ compliance (warning only — metric is informational)
        total = sum(len(b) for b in bullets_by_section.values())
        xyz_hits = 0
        xyz_markers = ["resulting in", "reducing", "increasing", "improving",
                       "enabling", "saving", "growing", "achieving", "delivering"]
        for bullets in bullets_by_section.values():
            for b in bullets:
                if any(m in b.lower() for m in xyz_markers):
                    xyz_hits += 1
        report.xyz_compliance = round(xyz_hits / max(1, total), 2)
        if report.xyz_compliance < 0.3:
            warnings.append(
                f"LOW_XYZ_COMPLIANCE: only {report.xyz_compliance:.0%} of bullets use impact language"
            )

        # 5. ATS readability — no banned phrases remain
        lower_all = tailored_tex.lower()
        for phrase in _BANNED_PHRASES:
            if phrase in lower_all:
                errors.append(f"ATS_BANNED_PHRASE: '{phrase}' found in tailored tex")
                report.ats_readability = False

        report.errors = errors
        report.warnings = warnings
        return report
