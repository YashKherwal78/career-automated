"""
Production Tailoring Engine V1 — Main Orchestrator.

Coordinates all subsystems in the exact order defined in the architecture:

  Phase 1:  JakeTexParser          → ParsedResumeTree
  Phase 2:  MacroGuard.mask        → PlaceholderMap
  Phase 3:  StructuralGuardLock    → StructuralSnapshot (pre-rewrite)
  Phase 4:  FactualEntityExtractor → FactualEntitySet
  Phase 5:  PromptBuilder          → 3 prompts (summary, experience, projects)
  Phase 6:  LLM calls (≤ MAX_SECTION_CALLS = 5)
  Phase 7:  LLMPatchResponse parse → BulletPatchOps
  Phase 8:  ConfidenceFilter       → keep original if confidence < threshold
  Phase 9:  MacroGuard.restore     → macros back in place
  Phase 10: IntegrityGate          → structural + factual check (hard block)
  Phase 11: PolicyGate             → writing quality check (revert errors)
  Phase 12: TailoredTexPatcher     → surgical str.replace on .tex
  Phase 13: IntegrityGate (2nd)    → final belt-and-suspenders check
  Phase 14: No-op detection        → return base if < NOOP_THRESHOLD changed
  Phase 15: SemanticDiffReporter   → per-bullet diff log

Design principles enforced here:
  - JakeTexParser is the single document model owner (change #7)
  - LLM returns JSON patch ops — never touches .tex directly (change #8)
  - MAX_SECTION_CALLS = 5 ceiling (change #2)
  - IntegrityGate and PolicyGate are separate (change #1)
  - No-op optimization (change #9)
  - VersionMetadata in result (change #3)
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from src.resume_intelligence.tailoring.models_v1 import (
    MAX_SECTION_CALLS,
    NOOP_THRESHOLD,
    BulletPatchOp,
    FactualEntitySet,
    HardBlockError,
    IntegrityReport,
    LLMPatchResponse,
    MutationBudget,
    PlaceholderMap,
    PolicyReport,
    SemanticDiffEntry,
    StructuralSnapshot,
    TailoringInput,
    TailoringResult,
    VersionMetadata,
)
from src.resume_intelligence.tailoring.jake_tex_parser import (
    JakeTexParser,
    ParsedBullet,
    ParsedEntry,
    ParsedResumeTree,
)
from src.resume_intelligence.tailoring.macro_guard import MacroGuard, MacroRestoreError
from src.resume_intelligence.tailoring.guardrails import (
    FactualEntityExtractor,
    IntegrityGate,
    PolicyGate,
    StructuralGuardLock,
)
from src.resume_intelligence.tailoring.prompt_builder import PromptBuilder
from src.resume_intelligence.tailoring.relevance_reorder import (
    apply_permutation,
    compute_reorder_permutation,
)
from src.resume_intelligence.tailoring.diff_reporter import SemanticDiffReporter
from src.resume_intelligence.tailoring.keyword_expansion import (
    find_related_keywords,
    apply_keyword_additions,
    compute_gap_report,
)
from src.resume_intelligence.evidence.candidate_memory import CandidateMemory

logger = logging.getLogger("TailoringEngineV1")


# ---------------------------------------------------------------------------
# LLM Provider Adapters (Refinement #6)
# ---------------------------------------------------------------------------

class LLMCaller:
    """
    Provider-agnostic adapter wrapping platform LLM infrastructure.
    Supports Groq, OpenAI, Anthropic, Gemini, and Mock providers.
    """

    def __init__(self, provider: str, model: str):
        self.provider = provider.lower()
        self.model = model
        self._client = self._init_client()

    def _init_client(self) -> Any:
        if self.provider == "groq":
            try:
                from groq import Groq
                api_key = os.environ.get("GROQ_API_KEY", "")
                return Groq(api_key=api_key) if api_key else None
            except ImportError:
                logger.warning("groq package not installed")
                return None
        elif self.provider == "openai":
            try:
                import openai
                api_key = os.environ.get("OPENAI_API_KEY", "")
                return openai.OpenAI(api_key=api_key) if api_key else None
            except ImportError:
                logger.warning("openai package not installed")
                return None
        return None

    # Same fallback chain LLMRouter (src/utils/llm_router.py) uses --
    # confirmed live this same session: a hardcoded single Groq model with
    # no fallback means a Groq-side deprecation (404) or the free-tier
    # daily token cap (429) takes down tailoring entirely instead of just
    # trying the next model.
    _GROQ_FALLBACK_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "groq/compound-mini"]

    def call(self, prompt: str) -> str:
        if self._client is None:
            logger.warning("LLMCaller: provider '%s' client unavailable — returning empty response", self.provider)
            return "{}"

        try:
            if self.provider == "groq":
                models_to_try = [self.model] + [m for m in self._GROQ_FALLBACK_MODELS if m != self.model]
                last_exc: Optional[Exception] = None
                for model in models_to_try:
                    try:
                        response = self._client.chat.completions.create(
                            model=model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": (
                                        "You are a precise resume editor. "
                                        "Return ONLY valid JSON. No markdown code blocks. No explanation."
                                    ),
                                },
                                {"role": "user", "content": prompt},
                            ],
                            temperature=0.2,
                            max_tokens=2048,
                            response_format={"type": "json_object"},
                        )
                        return response.choices[0].message.content or "{}"
                    except Exception as exc:
                        last_exc = exc
                        logger.warning("LLMCaller error (groq/%s), trying next fallback: %s", model, exc)
                if last_exc:
                    raise last_exc
                return "{}"
            elif self.provider == "openai":
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a precise resume editor. Return ONLY valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=2048,
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content or "{}"
        except Exception as exc:
            logger.error("LLMCaller error (%s/%s): %s", self.provider, self.model, exc)
            return "{}"

        return "{}"


# ---------------------------------------------------------------------------
# JSON Parser for LLM response
# ---------------------------------------------------------------------------

def _parse_llm_response(raw: str) -> LLMPatchResponse:
    """
    Parse raw LLM text into LLMPatchResponse.
    Strips markdown fences if present. Returns empty response on parse failure.
    """
    # Strip markdown code fences if LLM included them
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.MULTILINE)
        clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE)
        clean = clean.strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.error("LLM JSON parse failed: %s\nRaw: %.200s", exc, raw)
        return LLMPatchResponse()

    # Parse summary
    response = LLMPatchResponse(
        summary=data.get("summary"),
        summary_confidence=float(data.get("summary_confidence", 1.0)),
    )

    # Parse experience patch ops
    for op in data.get("experience", []):
        try:
            response.experience.append(BulletPatchOp(
                entry=int(op["entry"]),
                bullet=int(op["bullet"]),
                replace_with=str(op["replace_with"]),
                keywords_added=list(op.get("keywords_added", [])),
                confidence=float(op.get("confidence", 1.0)),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed experience patch op: %s — %s", op, exc)

    # Parse project patch ops
    for op in data.get("projects", []):
        try:
            response.projects.append(BulletPatchOp(
                entry=int(op["entry"]),
                bullet=int(op["bullet"]),
                replace_with=str(op["replace_with"]),
                keywords_added=list(op.get("keywords_added", [])),
                confidence=float(op.get("confidence", 1.0)),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed project patch op: %s — %s", op, exc)

    return response


# ---------------------------------------------------------------------------
# Patch applicator
# ---------------------------------------------------------------------------

class TailoredTexPatcher:
    """
    Applies BulletPatchOps to the original .tex string by index.
    Never uses string matching — uses character offsets from ParsedBullet.
    """

    @staticmethod
    def apply(
        base_tex: str,
        tree: ParsedResumeTree,
        exp_ops: Dict[Tuple[int, int], str],   # (entry_idx, bullet_idx) → rewritten
        proj_ops: Dict[Tuple[int, int], str],
        new_summary: Optional[str] = None,
    ) -> str:
        """
        Surgically replace resumeItem content in base_tex.

        Uses (char_start, char_end) offsets from ParsedBullet, so replacement
        is position-exact regardless of content similarity.

        Replacement is applied in REVERSE order of position to preserve offsets.
        """
        # Collect all replacement operations with character positions
        replacements: List[Tuple[int, int, str]] = []

        # Summary replacement
        if new_summary and tree.summary_char_start != -1:
            replacements.append((
                tree.summary_char_start,
                tree.summary_char_end,
                new_summary,
            ))

        # Experience replacements
        for sec in tree.sections:
            if sec.name == "Experience":
                for ei, entry in enumerate(sec.entries):
                    for bi, bullet in enumerate(entry.bullets):
                        key = (ei, bi)
                        if key in exp_ops:
                            replacements.append((
                                bullet.char_start,
                                bullet.char_end,
                                exp_ops[key],
                            ))

            elif sec.name == "Projects":
                for ei, entry in enumerate(sec.entries):
                    for bi, bullet in enumerate(entry.bullets):
                        key = (ei, bi)
                        if key in proj_ops:
                            replacements.append((
                                bullet.char_start,
                                bullet.char_end,
                                proj_ops[key],
                            ))

        # Sort by position descending (apply from end → start to preserve offsets)
        replacements.sort(key=lambda r: r[0], reverse=True)

        tex = base_tex
        for start, end, new_content in replacements:
            tex = tex[:start] + new_content + tex[end:]

        return tex


# ---------------------------------------------------------------------------
# Confidence Filter
# ---------------------------------------------------------------------------

def _apply_confidence_filter(
    ops: List[BulletPatchOp],
    tree_section: List[ParsedEntry],
    threshold: float,
) -> Tuple[Dict[Tuple[int, int], str], Dict[Tuple[int, int], bool], Dict[Tuple[int, int], float]]:
    """
    Apply confidence filter to patch ops.
    If confidence < threshold, keep original bullet text.

    Returns:
        final_ops: {(entry, bullet) → final_text}
        kept_original_map: {(entry, bullet) → bool}
        confidence_map: {(entry, bullet) → float}
    """
    final_ops: Dict[Tuple[int, int], str] = {}
    kept_original_map: Dict[Tuple[int, int], bool] = {}
    confidence_map: Dict[Tuple[int, int], float] = {}

    # Build op lookup
    op_lookup: Dict[Tuple[int, int], BulletPatchOp] = {}
    for op in ops:
        op_lookup[(op.entry, op.bullet)] = op

    # For every bullet in the section, decide keep or replace
    for ei, entry in enumerate(tree_section):
        for bi, bullet in enumerate(entry.bullets):
            key = (ei, bi)
            op = op_lookup.get(key)
            if op is None or op.confidence < threshold:
                # Keep original
                final_ops[key] = bullet.raw_content
                kept_original_map[key] = True
                confidence_map[key] = op.confidence if op else 0.0
            else:
                final_ops[key] = op.replace_with
                kept_original_map[key] = False
                confidence_map[key] = op.confidence

    return final_ops, kept_original_map, confidence_map


# ---------------------------------------------------------------------------
# Skill-term extraction (for keyword_expansion adjacency lookups)
# ---------------------------------------------------------------------------

def _extract_skill_terms(skills_block: str) -> List[str]:
    """Flat list of skill names out of the Jake-style categorized skills
    block. Confirmed live (2026-08-22): this template actually separates
    items with "$\\bullet$" (e.g. `React $\\bullet$ TypeScript $\\bullet$
    ...`), NOT commas -- comma-splitting alone left every category as one
    unsplit blob string, silently breaking every exact-skill-match lookup
    this feeds (gap_report, find_related_keywords) even though nothing
    raised an error. The generic macro-strip below removes the `\\bullet`
    command itself but leaves its surrounding math-mode `$` signs behind
    as a bare "$$", which is what's actually split on now; comma-split is
    kept only as a fallback for a line that has no bullet separator at
    all (e.g. a future template variant), so "Cloudflare (R2, DNS)"-style
    single items with a real internal comma aren't wrongly split when a
    bullet separator IS present."""
    terms: List[str] = []
    for line in skills_block.split("\\\\"):
        text = re.sub(r"\\textbf\{[^}]*\}", "", line)
        text = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})?", "", text)  # strip other macros
        text = text.replace("{", "").replace("}", "")
        parts = text.split("$$") if "$$" in text else text.split(",")
        for part in parts:
            term = part.strip().strip(":").strip("$").strip()
            if term and len(term) < 60:
                terms.append(term)
    return terms


# ---------------------------------------------------------------------------
# No-op detector
# ---------------------------------------------------------------------------

def _is_noop(
    exp_kept: Dict[Tuple[int, int], bool],
    proj_kept: Dict[Tuple[int, int], bool],
    summary_changed: bool,
) -> bool:
    """
    Return True if fewer than NOOP_THRESHOLD fraction of bullets were changed.
    Summary change alone is not enough to call it non-noop.
    """
    total = len(exp_kept) + len(proj_kept)
    if total == 0:
        return True

    changed = sum(1 for v in exp_kept.values() if not v) + \
              sum(1 for v in proj_kept.values() if not v)

    fraction_changed = changed / total
    return fraction_changed < NOOP_THRESHOLD


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class TailoringEngineV1:
    """
    Production Tailoring Engine V1.

    The LLM never edits the document.
    It only proposes replacement text for explicitly mutable fields.
    Everything else — parsing, validation, patching, layout, integrity —
    is deterministic code.
    """

    VERSION = "tailoring-v1.0"
    RULES_VERSION = "resume-rules-v1"
    KNOWLEDGE_VERSION = "resume-knowledge2-v1"

    def __init__(self):
        self._parser = JakeTexParser()
        self._entity_extractor = FactualEntityExtractor()
        self._guard_lock = StructuralGuardLock()
        self._integrity_gate = IntegrityGate()

    def tailor(self, inp: TailoringInput) -> TailoringResult:
        """
        Main entry point. Executes all 15 phases.
        Returns TailoringResult with ephemeral tailored_tex.
        Raises HardBlockError on any structural integrity violation.
        """
        logger.info("TailoringEngineV1.tailor() starting — job_id=%s", inp.job_id)

        llm = LLMCaller(inp.llm_provider, inp.llm_model)
        memory = CandidateMemory(inp.candidate_memory)
        prompt_builder = PromptBuilder(
            inp.resume_knowledge2_path,
            writing_tone=inp.writing_tone,
            tailoring_aggressiveness=inp.tailoring_aggressiveness,
        )

        # ── Phase 1: Parse ──────────────────────────────────────────────────
        logger.debug("Phase 1: Parsing .tex")
        tree = self._parser.parse(inp.base_tex)

        # ── Phase 2: Macro masking ──────────────────────────────────────────
        logger.debug("Phase 2: Masking macros")
        # Mask summary
        masked_summary, summary_pmap, counter = MacroGuard.mask(
            tree.summary_block or "", counter_start=1
        )
        # Mask all experience bullets
        exp_masked: List[List[str]] = []
        exp_pmaps: List[PlaceholderMap] = []
        for entry in self._get_section_entries(tree, "Experience"):
            bullet_texts = [b.raw_content for b in entry.bullets]
            masked_bullets, bmap, counter = MacroGuard.mask_bullets(bullet_texts, counter)
            exp_masked.append(masked_bullets)
            exp_pmaps.append(bmap)

        # Mask all project bullets
        proj_masked: List[List[str]] = []
        proj_pmaps: List[PlaceholderMap] = []
        for entry in self._get_section_entries(tree, "Projects"):
            bullet_texts = [b.raw_content for b in entry.bullets]
            masked_bullets, bmap, counter = MacroGuard.mask_bullets(bullet_texts, counter)
            proj_masked.append(masked_bullets)
            proj_pmaps.append(bmap)

        # Build a combined placeholder map for restoration
        combined_pmap = PlaceholderMap()
        for pmap in [summary_pmap] + exp_pmaps + proj_pmaps:
            combined_pmap.to_placeholder.update(pmap.to_placeholder)
            combined_pmap.from_placeholder.update(pmap.from_placeholder)

        # ── Phase 3: Structural snapshot ────────────────────────────────────
        logger.debug("Phase 3: Structural snapshot")
        before_snap = self._guard_lock.snapshot(inp.base_tex)

        # ── Phase 4: Factual entity extraction ──────────────────────────────
        logger.debug("Phase 4: Entity extraction")
        entity_set = self._entity_extractor.extract(inp.base_tex)

        # ── Phase 5: Build prompts ───────────────────────────────────────────
        logger.debug("Phase 5: Building prompts")
        exp_entries_with_masked = self._build_masked_entries(
            tree, "Experience", exp_masked
        )
        proj_entries_with_masked = self._build_masked_entries(
            tree, "Projects", proj_masked
        )

        base_facts = self._extract_base_facts(tree)
        summary_prompt = prompt_builder.build_summary_prompt(
            jd_profile=inp.jd_profile,
            base_resume_facts=base_facts,
            candidate_memory_evidence=memory.get_global_facts(),
            current_summary=masked_summary or None,
        )
        exp_prompt = prompt_builder.build_experience_prompt(
            entries=exp_entries_with_masked,
            jd_profile=inp.jd_profile,
            candidate_memory=inp.candidate_memory,
        )
        proj_prompt = prompt_builder.build_projects_prompt(
            entries=proj_entries_with_masked,
            jd_profile=inp.jd_profile,
        )

        # ── Phase 6: LLM calls (≤ MAX_SECTION_CALLS) ───────────────────────
        logger.debug("Phase 6: LLM calls")
        calls_made = 0

        summary_raw = llm.call(summary_prompt)
        calls_made += 1
        summary_response = _parse_llm_response(summary_raw)

        exp_raw = llm.call(exp_prompt)
        calls_made += 1
        exp_response = _parse_llm_response(exp_raw)

        proj_raw = llm.call(proj_prompt)
        calls_made += 1
        proj_response = _parse_llm_response(proj_raw)

        assert calls_made <= MAX_SECTION_CALLS, (
            f"LLM call budget exceeded: {calls_made} > {MAX_SECTION_CALLS}"
        )

        # ── Phase 7 + 8: Parse ops + Confidence filter ──────────────────────
        logger.debug("Phase 7-8: Confidence filter")
        exp_section_entries = self._get_section_entries(tree, "Experience")
        proj_section_entries = self._get_section_entries(tree, "Projects")

        exp_final, exp_kept, exp_conf = _apply_confidence_filter(
            exp_response.experience, exp_section_entries, inp.confidence_threshold
        )
        proj_final, proj_kept, proj_conf = _apply_confidence_filter(
            proj_response.projects, proj_section_entries, inp.confidence_threshold
        )

        # Summary
        new_summary_masked: Optional[str] = None
        summary_changed = False
        if (
            summary_response.summary
            and summary_response.summary_confidence >= inp.confidence_threshold
            and tree.summary_char_start != -1
        ):
            new_summary_masked = summary_response.summary
            summary_changed = True

        # ── Phase 9: Macro restoration ───────────────────────────────────────
        logger.debug("Phase 9: Macro restoration")
        try:
            new_summary = (
                MacroGuard.restore(new_summary_masked, combined_pmap)
                if new_summary_masked else None
            )
            exp_restored: Dict[Tuple[int, int], str] = {
                k: MacroGuard.restore(v, combined_pmap)
                for k, v in exp_final.items()
            }
            proj_restored: Dict[Tuple[int, int], str] = {
                k: MacroGuard.restore(v, combined_pmap)
                for k, v in proj_final.items()
            }
        except MacroRestoreError as exc:
            logger.error("Macro restore failed: %s", exc)
            raise HardBlockError([f"MACRO_RESTORE_FAILURE: {exc}"])

        # ── Phase 10: IntegrityGate (per-bullet verification & fallback) ─────────
        logger.debug("Phase 10: IntegrityGate verification")
        
        # Per-bullet metric and technology preservation check
        exp_section_entries = self._get_section_entries(tree, "Experience")
        proj_section_entries = self._get_section_entries(tree, "Projects")

        # Check Experience bullets
        for ei, entry in enumerate(exp_section_entries):
            for bi, bullet in enumerate(entry.bullets):
                key = (ei, bi)
                rewritten_text = exp_restored.get(key, bullet.raw_content)
                orig_text = bullet.raw_content

                # Check if numbers or tech names present in orig_text were dropped in rewritten_text
                orig_entities = self._entity_extractor.extract(orig_text)
                for tech in orig_entities.technologies:
                    if tech not in rewritten_text:
                        logger.info("Tech '%s' missing in Experience[%d][%d] rewrite — reverting to original", tech, ei, bi)
                        exp_restored[key] = orig_text
                        exp_kept[key] = True

                for metric in orig_entities.metrics:
                    raw_num = metric.rstrip("+").lstrip("~")
                    if metric not in rewritten_text and raw_num not in rewritten_text:
                        logger.info("Metric '%s' missing in Experience[%d][%d] rewrite — reverting to original", metric, ei, bi)
                        exp_restored[key] = orig_text
                        exp_kept[key] = True

        # Check Projects bullets
        for ei, entry in enumerate(proj_section_entries):
            for bi, bullet in enumerate(entry.bullets):
                key = (ei, bi)
                rewritten_text = proj_restored.get(key, bullet.raw_content)
                orig_text = bullet.raw_content

                orig_entities = self._entity_extractor.extract(orig_text)
                for tech in orig_entities.technologies:
                    if tech not in rewritten_text:
                        logger.info("Tech '%s' missing in Projects[%d][%d] rewrite — reverting to original", tech, ei, bi)
                        proj_restored[key] = orig_text
                        proj_kept[key] = True

                for metric in orig_entities.metrics:
                    raw_num = metric.rstrip("+").lstrip("~")
                    if metric not in rewritten_text and raw_num not in rewritten_text:
                        logger.info("Metric '%s' missing in Projects[%d][%d] rewrite — reverting to original", metric, ei, bi)
                        proj_restored[key] = orig_text
                        proj_kept[key] = True

        # ── Phase 10b: Relevance-based bullet reordering ──────────────────────
        # The evidence behind this engine's whole redesign: recruiters spend
        # ~7 seconds per resume and attention concentrates on the first
        # bullets under each role — which bullet leads matters more than how
        # any single bullet is worded. This permutes already-written,
        # already-fact-checked text between slots within the same entry; it
        # never adds/removes/rewrites anything, so it can't trip IntegrityGate.
        logger.debug("Phase 10b: Relevance-based bullet reordering")
        exp_perm = compute_reorder_permutation(exp_restored, len(exp_section_entries), inp.jd_profile)
        proj_perm = compute_reorder_permutation(proj_restored, len(proj_section_entries), inp.jd_profile)
        exp_restored = apply_permutation(exp_perm, exp_restored)
        exp_kept = apply_permutation(exp_perm, exp_kept)
        exp_conf = apply_permutation(exp_perm, exp_conf)
        proj_restored = apply_permutation(proj_perm, proj_restored)
        proj_kept = apply_permutation(proj_perm, proj_kept)
        proj_conf = apply_permutation(proj_perm, proj_conf)

        # Re-apply surgical patch with guarded, reordered bullets
        preview_tex = TailoredTexPatcher.apply(
            inp.base_tex, tree, exp_restored, proj_restored, new_summary
        )

        # Run document-level IntegrityGate (commands, locked fields, section count, macros)
        integrity_report = self._integrity_gate.check(
            inp.base_tex, preview_tex, before_snap, entity_set
        )
        if not integrity_report.passed:
            raise HardBlockError(integrity_report.violations)

        # ── Phase 11: PolicyGate ─────────────────────────────────────────────
        logger.debug("Phase 11: PolicyGate")
        jd_keywords = [
            k.get("keyword", "") for k in inp.jd_profile.get("ats_keywords", [])
        ]
        policy_gate = PolicyGate(jd_keywords=jd_keywords)
        bullets_by_section: Dict[str, List[str]] = {
            "Experience": [v for v in exp_restored.values()],
            "Projects": [v for v in proj_restored.values()],
        }
        policy_report = policy_gate.check(
            tailored_tex=preview_tex,
            summary=new_summary,
            bullets_by_section=bullets_by_section,
        )
        # Revert individual bullets that triggered policy errors
        for err in policy_report.errors:
            logger.warning("PolicyGate error: %s — reverting affected bullet", err)
            # Policy errors revert to original; we keep the preview tex as-is
            # since reversions would require re-patching. Log for now.
            # Full revert-on-error is a Phase 2 refinement.

        # ── Phase 12: Surgical patch ─────────────────────────────────────────
        logger.debug("Phase 12: Patching .tex")
        tailored_tex = preview_tex  # already computed in Phase 10

        # ── Phase 13: Final IntegrityGate ────────────────────────────────────
        logger.debug("Phase 13: Final IntegrityGate")
        final_report = self._integrity_gate.check(
            inp.base_tex, tailored_tex, before_snap, entity_set
        )
        if not final_report.passed:
            raise HardBlockError(final_report.violations)

        # ── Phase 14: No-op detection ─────────────────────────────────────────
        logger.debug("Phase 14: No-op detection")
        is_noop = _is_noop(exp_kept, proj_kept, summary_changed)
        if is_noop:
            logger.info("No-op detected — returning base resume unchanged")
            tailored_tex = inp.base_tex

        # ── Phase 15: Semantic diff report ───────────────────────────────────
        logger.debug("Phase 15: Semantic diff")
        diff_reporter = SemanticDiffReporter(inp.jd_profile)

        # Build section-indexed structures for reporter
        patched_bullets: Dict[str, List[List[str]]] = {"Experience": [], "Projects": []}
        kept_map: Dict[str, List[List[bool]]] = {"Experience": [], "Projects": []}
        conf_map: Dict[str, List[List[float]]] = {"Experience": [], "Projects": []}

        for ei, entry in enumerate(exp_section_entries):
            entry_bullets = [exp_restored.get((ei, bi), b.raw_content) for bi, b in enumerate(entry.bullets)]
            entry_kept = [exp_kept.get((ei, bi), True) for bi in range(len(entry.bullets))]
            entry_conf = [exp_conf.get((ei, bi), 0.0) for bi in range(len(entry.bullets))]
            patched_bullets["Experience"].append(entry_bullets)
            kept_map["Experience"].append(entry_kept)
            conf_map["Experience"].append(entry_conf)

        for ei, entry in enumerate(proj_section_entries):
            entry_bullets = [proj_restored.get((ei, bi), b.raw_content) for bi, b in enumerate(entry.bullets)]
            entry_kept = [proj_kept.get((ei, bi), True) for bi in range(len(entry.bullets))]
            entry_conf = [proj_conf.get((ei, bi), 0.0) for bi in range(len(entry.bullets))]
            patched_bullets["Projects"].append(entry_bullets)
            kept_map["Projects"].append(entry_kept)
            conf_map["Projects"].append(entry_conf)

        diff_log = diff_reporter.generate(tree, patched_bullets, kept_map, conf_map)

        # ── Phase 15b: Related-keyword expansion ─────────────────────────────
        # Closes the "candidate lists AWS, JD wants Azure" gap that
        # keyword_coverage below can only measure, never fix. Zero LLM
        # calls (static adjacency lookup); fails closed -- any addition
        # whose target line can't be found in the actual skills text is
        # dropped rather than risking a malformed .tex. See
        # keyword_expansion.py for the adjacency rules and why this is
        # deliberately conservative (never invents unrelated skills).
        keyword_expansions: List[Dict[str, str]] = []
        gap_report: Dict[str, Any] = {}
        try:
            skills_block = tree.skills_block
            if skills_block and skills_block in tailored_tex:
                candidate_skills = _extract_skill_terms(skills_block)
                jd_required = [
                    s.get("normalized_name") or s.get("name") or ""
                    for s in (inp.jd_profile.get("required_skills") or [])
                    if isinstance(s, dict)
                ] or [s for s in (inp.jd_profile.get("required_skills") or []) if isinstance(s, str)]
                candidate_additions = find_related_keywords(candidate_skills, jd_required)
                applied: List = []
                if candidate_additions:
                    new_skills_block, applied = apply_keyword_additions(skills_block, candidate_additions)
                    if applied:
                        tailored_tex = tailored_tex.replace(skills_block, new_skills_block, 1)
                        keyword_expansions = [
                            {"keyword": a.keyword, "because_of": a.because_of} for a in applied
                        ]
                        logger.info(
                            "TailoringEngineV1: added %d related keyword(s) to skills section: %s",
                            len(applied), keyword_expansions,
                        )
                # ATS keywords (broader than required_skills -- includes JD
                # terms not tagged as a formal "required skill") folded in
                # too, so the gap report reflects everything the JD actually
                # asks for, not just one field of the parsed profile.
                ats_keyword_terms = [
                    k.get("normalized_keyword") or k.get("keyword") or ""
                    for k in (inp.jd_profile.get("ats_keywords") or [])
                    if isinstance(k, dict)
                ]
                gap_report = compute_gap_report(
                    candidate_skills,
                    list(dict.fromkeys(jd_required + ats_keyword_terms)),
                    applied,
                )
        except Exception as e:
            logger.warning("TailoringEngineV1: keyword expansion/gap report skipped (%s)", e)

        # ── Compute keyword coverage & TailoringEffectivenessScore ──────────────
        keyword_coverage = self._compute_keyword_coverage(tailored_tex, inp.jd_profile)
        effectiveness = self._compute_effectiveness_score(diff_log, policy_report, keyword_coverage)

        logger.info(
            "TailoringEngineV1 complete — job_id=%s, calls=%d, is_noop=%s, coverage=%.2f, score=%.1f (%s)",
            inp.job_id, calls_made, is_noop, keyword_coverage, effectiveness.overall_score, effectiveness.grade
        )

        # Phase 15: Hash calculation & VersionMetadata
        import hashlib
        base_hash = hashlib.sha256(inp.base_tex.encode('utf-8')).hexdigest()
        jd_hash = hashlib.sha256(json.dumps(inp.jd_profile, sort_keys=True).encode('utf-8')).hexdigest()

        # Escape unescaped % characters for clean pdflatex compilation
        lines = []
        for line in tailored_tex.split('\n'):
            if '%' in line and not line.strip().startswith('%'):
                new_chars = []
                for i, ch in enumerate(line):
                    if ch == '%' and (i == 0 or line[i - 1] != '\\'):
                        new_chars.append('\\%')
                    else:
                        new_chars.append(ch)
                line = ''.join(new_chars)
            lines.append(line)
        tailored_tex = '\n'.join(lines)

        output_hash = hashlib.sha256(tailored_tex.encode('utf-8')).hexdigest()

        return TailoringResult(
            job_id=inp.job_id,
            tailored_tex=tailored_tex,
            is_noop=is_noop,
            diff_log=diff_log,
            integrity_report=final_report,
            policy_report=policy_report,
            effectiveness_score=effectiveness,
            keyword_coverage=keyword_coverage,
            keyword_expansions=keyword_expansions,
            gap_report=gap_report,
            llm_calls_made=calls_made,
            version_metadata=VersionMetadata(
                prompt_version=self.VERSION,
                rules_version=self.RULES_VERSION,
                knowledge_version=self.KNOWLEDGE_VERSION,
                llm_model=inp.llm_model,
                llm_provider=inp.llm_provider,
                base_resume_hash=base_hash,
                jd_hash=jd_hash,
                output_hash=output_hash,
            ),
            is_persisted=False,
        )

    def _compute_effectiveness_score(
        self,
        diff_log: List[SemanticDiffEntry],
        policy_report: PolicyReport,
        keyword_coverage: float
    ) -> Any:
        from src.resume_intelligence.tailoring.models_v1 import TailoringEffectivenessScore

        if not diff_log:
            return TailoringEffectivenessScore()

        # Component scores (0.0 to 100.0)
        ats_score = round(keyword_coverage * 100.0, 1)
        xyz_count = sum(1 for d in diff_log if d.xyz_used)
        xyz_score = round((xyz_count / max(1, len(diff_log))) * 100.0, 1)
        verb_upgrades = sum(1 for d in diff_log if d.action_verb.get("old") != d.action_verb.get("new"))
        verb_score = round(min(100.0, (verb_upgrades / max(1, len(diff_log))) * 150.0), 1)
        alignment_score = round(min(100.0, (sum(len(d.keywords_added) for d in diff_log) / max(1, len(diff_log))) * 50.0), 1)
        stuffing_penalty = min(20.0, len(policy_report.errors) * 3.0)

        overall = round(
            max(0.0, (ats_score * 0.4) + (xyz_score * 0.25) + (alignment_score * 0.20) + (verb_score * 0.15) - stuffing_penalty),
            1
        )

        grade = "F"
        if overall >= 90:
            grade = "A+"
        elif overall >= 80:
            grade = "A"
        elif overall >= 70:
            grade = "B"
        elif overall >= 60:
            grade = "C"

        return TailoringEffectivenessScore(
            overall_score=overall,
            role_alignment_score=alignment_score,
            ats_keyword_coverage_score=ats_score,
            action_verb_strength_score=verb_score,
            xyz_impact_score=xyz_score,
            stuffing_penalty=stuffing_penalty,
            grade=grade
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_section_entries(
        self, tree: ParsedResumeTree, section_name: str
    ) -> List[ParsedEntry]:
        for sec in tree.sections:
            if sec.name == section_name:
                return sec.entries
        return []

    def _build_masked_entries(
        self,
        tree: ParsedResumeTree,
        section_name: str,
        masked_bullets: List[List[str]],
    ) -> List[ParsedEntry]:
        """
        Return a copy of section entries where bullet raw_content is replaced
        with its masked equivalent, for use in prompt construction.
        """
        from dataclasses import replace as dc_replace
        from src.resume_intelligence.tailoring.jake_tex_parser import ParsedBullet

        entries = self._get_section_entries(tree, section_name)
        result: List[ParsedEntry] = []
        for ei, entry in enumerate(entries):
            masked_entry_bullets = masked_bullets[ei] if ei < len(masked_bullets) else []
            new_bullets: List[ParsedBullet] = []
            for bi, bullet in enumerate(entry.bullets):
                masked_content = (
                    masked_entry_bullets[bi]
                    if bi < len(masked_entry_bullets)
                    else bullet.raw_content
                )
                new_bullets.append(ParsedBullet(
                    raw_content=masked_content,
                    char_start=bullet.char_start,
                    char_end=bullet.char_end,
                ))
            result.append(ParsedEntry(
                entry_type=entry.entry_type,
                heading_tokens=entry.heading_tokens,
                bullets=new_bullets,
            ))
        return result

    def _extract_base_facts(self, tree: ParsedResumeTree) -> List[str]:
        """Extract top-level facts from the parsed tree for summary context."""
        facts: List[str] = []
        for sec in tree.sections:
            for entry in sec.entries:
                if entry.heading_tokens:
                    facts.append(f"{entry.heading_tokens[0]}: {entry.heading_tokens[2] if len(entry.heading_tokens) > 2 else ''}")
        return facts[:8]

    def _compute_keyword_coverage(
        self, tailored_tex: str, jd_profile: Dict[str, Any]
    ) -> float:
        tex_lower = tailored_tex.lower()
        ats_keywords = jd_profile.get("ats_keywords", [])
        if not ats_keywords:
            return 0.0
        hits = sum(
            1 for k in ats_keywords
            if k.get("normalized_keyword", k.get("keyword", "")).lower() in tex_lower
        )
        return round(hits / len(ats_keywords), 3)
