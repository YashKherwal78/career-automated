"""
Production Tailoring Engine V1 — Data Contracts (Final Architecture).

All Pydantic models and dataclasses used across the engine.
No LLM or I/O code lives here — pure data contracts only.

Design principles reflected here:
  - LLM returns JSON patch ops, never raw text blobs (change #8)
  - IntegrityGate and PolicyGate are separate concerns (change #1)
  - MAX_SECTION_CALLS = 5 contract ceiling (change #2)
  - VersionMetadata in TailoringResult (change #3)
  - FactualEntitySet for entity-level preservation (change #4 + #5)
  - MutationBudget for explicit policy (change #6)
  - is_noop flag for no-op optimization (change #9)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Engine-level constants
# ---------------------------------------------------------------------------

MAX_SECTION_CALLS: int = 5
"""
Ceiling on LLM calls per tailor() invocation.
Current usage: summary(1) + experience(1) + projects(1) = 3.
Reserved capacity for: cover_letter(1), linkedin_summary(1).
"""

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.70
"""Bullets with LLM confidence below this threshold keep the original."""

NOOP_THRESHOLD: float = 0.05
"""
If fewer than this fraction of bullets were meaningfully changed,
the engine returns the base resume unchanged (no-op optimization).
"""


# ---------------------------------------------------------------------------
# Mutation Budget — explicit policy, not implicit assumption
# ---------------------------------------------------------------------------

@dataclass
class MutationBudget:
    """
    Defines what percentage of each section is allowed to change.
    0.0 = fully locked, 1.0 = fully rewritable.

    The engine enforces these limits as hard constraints, not guidelines.
    """
    summary: float = 1.0
    """Summary may be completely rewritten."""

    experience_bullets: float = 1.0
    """Experience bullet *wording* may be fully rewritten; facts are locked."""

    project_bullets: float = 1.0
    """Project bullet *wording* may be fully rewritten; facts are locked."""

    contact_block: float = 0.0
    """Name, phone, email, LinkedIn — absolutely locked."""

    education: float = 0.0
    """Institution, degree, dates, GPA — absolutely locked."""

    skills_section: float = 0.0
    """Skill list — absolutely locked (no reorder, no add, no remove)."""

    section_structure: float = 0.0
    """Section order, section names, section count — absolutely locked."""

    heading_tokens: float = 0.0
    """Company names, job titles, dates, project names — absolutely locked."""


DEFAULT_MUTATION_BUDGET = MutationBudget()


# ---------------------------------------------------------------------------
# Factual Entity Set — pre-extracted before tailoring
# ---------------------------------------------------------------------------

@dataclass
class FactualEntitySet:
    """
    All factual entities extracted from the Base Resume before any rewrite.
    After tailoring, every entity here must still be present in the
    section where it originally appeared (unless that section is locked entirely).

    Extracted entity categories (change #4 + #5):
        companies, dates, universities, technologies, awards, certs,
        metrics, locations, proper_nouns
    """
    companies: FrozenSet[str] = field(default_factory=frozenset)
    dates: FrozenSet[str] = field(default_factory=frozenset)
    universities: FrozenSet[str] = field(default_factory=frozenset)
    technologies: FrozenSet[str] = field(default_factory=frozenset)
    """
    Technology names like 'Redis', 'FastAPI', 'TensorFlow'.
    The LLM must never silently replace Redis with Memcached,
    or TensorFlow with PyTorch — those are factual, not stylistic.
    """
    awards: FrozenSet[str] = field(default_factory=frozenset)
    certifications: FrozenSet[str] = field(default_factory=frozenset)
    metrics: FrozenSet[str] = field(default_factory=frozenset)
    """Numeric tokens: '80%', '10,000+', '$2M', '2s', etc."""
    locations: FrozenSet[str] = field(default_factory=frozenset)
    proper_nouns: FrozenSet[str] = field(default_factory=frozenset)
    """Any remaining capitalized proper nouns not caught above."""


# ---------------------------------------------------------------------------
# Input contract
# ---------------------------------------------------------------------------

class TailoringInput(BaseModel):
    """Everything the engine needs. Caller assembles this; engine never fetches."""

    base_tex: str
    """Raw .tex content of the canonical Base Resume. Source of truth."""

    candidate_memory: Dict[str, Any] = Field(default_factory=dict)
    """Evidence store: {bullet_key → [evidence strings], 'global' → [facts]}."""

    jd_profile: Dict[str, Any] = Field(default_factory=dict)
    """
    Pre-parsed StructuredJobProfile from normalized_jobs (serialized as dict).
    Engine MUST consume this. It must never re-parse a raw JD.
    """

    resume_knowledge2_path: str = "resume_knowledge"
    """Absolute or relative path to the resume_knowledge/ directory."""

    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    llm_provider: str = "groq"
    llm_model: str = "llama3-70b-8192"
    job_id: str = ""
    mutation_budget: MutationBudget = Field(default_factory=MutationBudget)


# ---------------------------------------------------------------------------
# LLM output — JSON patch operations (change #8)
# ---------------------------------------------------------------------------

class BulletPatchOp(BaseModel):
    """
    A single patch operation proposed by the LLM.
    The patcher applies this to the ParsedResumeTree by index,
    never by string matching.
    """
    entry: int
    """Zero-based index of the entry (experience or project) within its section."""

    bullet: int
    """Zero-based index of the bullet within the entry."""

    replace_with: str
    """
    Proposed replacement content for \\resumeItem{CONTENT}.
    LaTeX macros are still placeholders (__KW_1__ etc.) at this point.
    """

    keywords_added: List[str] = Field(default_factory=list)
    """JD keywords the LLM claims to have woven in."""

    confidence: float = 1.0
    """LLM self-reported confidence 0.0–1.0 for this specific rewrite."""


class LLMPatchResponse(BaseModel):
    """
    Structured JSON the LLM returns for each section-level call.
    Using explicit patch ops instead of text blobs prevents positional ambiguity.
    """

    # Summary call output
    summary: Optional[str] = None
    summary_confidence: float = 1.0

    # Experience batch call output
    experience: List[BulletPatchOp] = Field(default_factory=list)

    # Projects batch call output
    projects: List[BulletPatchOp] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Structural snapshot (pre-rewrite)
# ---------------------------------------------------------------------------

@dataclass
class StructuralSnapshot:
    """
    Command counts extracted from raw .tex BEFORE any rewrite.
    All counts must be identical in the tailored .tex after patching.
    These are computed by simple string counting — no parsing needed.
    """
    section_count: int = 0
    resumeitem_count: int = 0
    resumesubheading_count: int = 0
    resumeprojectheading_count: int = 0
    bullet_count_per_section: Dict[str, int] = field(default_factory=dict)
    locked_field_tokens: FrozenSet[str] = field(default_factory=frozenset)


# ---------------------------------------------------------------------------
# Macro placeholder map
# ---------------------------------------------------------------------------

@dataclass
class PlaceholderMap:
    """
    Bidirectional mapping between LaTeX macros and their placeholders.
    Placeholder keys are always __MACRO_N__ where N is a 1-based integer.
    """
    to_placeholder: Dict[str, str] = field(default_factory=dict)
    """original_latex → __MACRO_N__"""

    from_placeholder: Dict[str, str] = field(default_factory=dict)
    """__MACRO_N__ → original_latex"""


# ---------------------------------------------------------------------------
# Integrity Gate — "Is this still the same resume?" (change #1)
# ---------------------------------------------------------------------------

class IntegrityReport(BaseModel):
    """
    Result of IntegrityGate.check().
    Answers: is this still structurally identical to the base resume?
    Does NOT enforce resume quality — that belongs to PolicyGate.
    """
    locked_fields_intact: bool = True
    """Company names, titles, dates, education, contact — byte-identical."""

    factual_entities_preserved: bool = True
    """All technologies, metrics, proper nouns from FactualEntitySet still present."""

    bullet_count_unchanged: bool = True
    section_count_unchanged: bool = True
    resumeitem_count_unchanged: bool = True
    resumesubheading_count_unchanged: bool = True
    resumeprojectheading_count_unchanged: bool = True

    macros_restored: bool = True
    """No __PLACEHOLDER__ strings remain in tailored output."""

    violations: List[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0


# ---------------------------------------------------------------------------
# Policy Gate — "Is this a good tailored resume?" (change #1)
# ---------------------------------------------------------------------------

class PolicyReport(BaseModel):
    """
    Result of PolicyGate.check().
    Answers: does this tailored resume meet writing quality standards?
    Enforces resume_knowledge2 policy rules independently of structure.
    """
    no_keyword_stuffing: bool = True
    """No JD keyword appears more than 2× per section in unnatural proximity."""

    summary_length_ok: bool = True
    """Summary is within summary_rules.yaml max_lines = 3."""

    bullet_lengths_ok: bool = True
    """All bullets within bullet_rules.yaml max_words = 28."""

    xyz_compliance: float = 0.0
    """Fraction of rewritten bullets that follow Google XYZ structure."""

    ats_readability: bool = True
    """No banned phrases (bullet_rules.yaml: banned_phrases) remain."""

    warnings: List[str] = Field(default_factory=list)
    """Non-blocking warnings. Engine does not revert on warnings."""

    errors: List[str] = Field(default_factory=list)
    """Blocking errors. Engine reverts affected bullet to original."""

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# Fact Classification Tiers (Refinement #2)
# ---------------------------------------------------------------------------

class FactTier(str, Enum):
    TIER_1_HARD_LOCKED = "TIER_1_HARD_LOCKED"
    """Company, Title, Dates, Education, Contact, Metrics, Awards. Absolute non-negotiable."""

    TIER_2_DOMAIN_TECH = "TIER_2_DOMAIN_TECH"
    """Technologies, Frameworks, Protocols (ASTERIX, CAT048, EUROCONTROL, Tesseract, BGE-M3). Bullet-scoped."""

    TIER_3_STYLISTIC = "TIER_3_STYLISTIC"
    """Action verbs, adjectives, sentence structure, Google XYZ phrasing."""


# ---------------------------------------------------------------------------
# Quantitative Tailoring Effectiveness Evaluator (Refinement #5)
# ---------------------------------------------------------------------------

class TailoringEffectivenessScore(BaseModel):
    """
    Objective scoring of tailoring quality (0.0 to 100.0).
    Separates LLM rewrite quality from engine structural correctness.
    """
    overall_score: float = 0.0
    role_alignment_score: float = 0.0
    ats_keyword_coverage_score: float = 0.0
    action_verb_strength_score: float = 0.0
    xyz_impact_score: float = 0.0
    stuffing_penalty: float = 0.0
    grade: str = "F"  # 'A+', 'A', 'B', 'C', 'F'


# ---------------------------------------------------------------------------
# Abstract LLMProvider Interface (Refinement #6)
# ---------------------------------------------------------------------------

class LLMProviderInterface(BaseModel):
    """
    Abstract interface for LLM providers.
    Engine remains completely provider-agnostic (Groq, OpenAI, Anthropic, Gemini, Local).
    """
    provider_name: str = "mock"
    model_name: str = "mock-v1"

    def generate_json(self, prompt: str) -> str:
        """Subclasses or adapters implement this to return raw JSON string."""
        return "{}"


# ---------------------------------------------------------------------------
# Version metadata (change #3)
# ---------------------------------------------------------------------------

class VersionMetadata(BaseModel):
    """
    Provenance tags stored in TailoringResult.
    Provides complete reproducibility for regression testing and auditing.
    """
    prompt_version: str = "tailoring-v1.0"
    rules_version: str = "resume-rules-v1"
    knowledge_version: str = "resume-knowledge2-v1"
    llm_model: str = ""
    llm_provider: str = ""
    base_resume_hash: str = ""
    """SHA-256 digest of the canonical base .tex input."""
    jd_hash: str = ""
    """SHA-256 digest of the StructuredJobProfile input."""
    output_hash: str = ""
    """SHA-256 digest of the resulting tailored .tex output."""


# ---------------------------------------------------------------------------
# Semantic diff report with full provenance
# ---------------------------------------------------------------------------

class SemanticDiffEntry(BaseModel):
    """Per-bullet semantic diff produced after all rewrites are finalized with Quality Scorer provenance."""

    section: str
    company_or_project: str
    bullet_index: int
    original: str
    rewritten: str

    keywords_added: List[str] = Field(default_factory=list)

    action_verb: Dict[str, str] = Field(default_factory=dict)
    """{'old': 'Built', 'new': 'Engineered'}"""

    xyz_used: bool = False
    ownership_preserved: bool = True
    confidence: float = 1.0

    kept_original: bool = False
    """True when confidence < threshold — original was preserved unchanged."""

    before_score: int = 0
    after_score: int = 0
    rewrite_level: str = "KEEP"
    reason: str = ""

    evidence_sources: List[str] = Field(default_factory=list)
    jd_keywords_targeted: List[str] = Field(default_factory=list)
    rules_applied: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Final output
# ---------------------------------------------------------------------------

class TailoringResult(BaseModel):
    """
    Everything the caller receives.
    tailored_tex is the only mutable artifact; all other fields are observability.
    """

    job_id: str = ""

    tailored_tex: str = ""
    """
    The tailored .tex string. Differs from base_tex ONLY in:
      - Summary block content (if summary section exists)
      - \\resumeItem{} content strings
    LaTeX structure, section order, bullet count, locked fields — all identical.
    """

    is_noop: bool = False
    """
    True when fewer than NOOP_THRESHOLD fraction of bullets changed meaningfully.
    Caller should serve the base resume directly in this case.
    """

    diff_log: List[SemanticDiffEntry] = Field(default_factory=list)
    integrity_report: IntegrityReport = Field(default_factory=IntegrityReport)
    policy_report: PolicyReport = Field(default_factory=PolicyReport)
    effectiveness_score: TailoringEffectivenessScore = Field(default_factory=TailoringEffectivenessScore)

    keyword_coverage: float = 0.0
    """Fraction of jd_profile.ats_keywords present in tailored output, 0.0–1.0."""

    llm_calls_made: int = 0
    """Bounded by MAX_SECTION_CALLS = 5."""

    version_metadata: VersionMetadata = Field(default_factory=VersionMetadata)

    is_persisted: bool = False
    """Guaranteed False. Tailored resumes are always ephemeral."""


# ---------------------------------------------------------------------------
# Hard block error
# ---------------------------------------------------------------------------

class HardBlockError(RuntimeError):
    """
    Raised when IntegrityGate detects a structural violation.
    Caller must discard tailored output and surface the violations.
    """
    def __init__(self, violations: List[str]):
        self.violations = violations
        super().__init__(
            f"TailoringEngine HardBlock — {len(violations)} violation(s): "
            + "; ".join(violations)
        )
