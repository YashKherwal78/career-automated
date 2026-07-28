"""
Test Suite — Production Tailoring Engine V1.

Tests are deterministic (no LLM calls).
The engine is tested with mock LLM responses to verify correctness of every
phase independently: parser, macro guard, guardrails, confidence filter, patcher.

Run: python -m pytest backend/src/resume_intelligence/tests/test_tailoring_v1.py -v
"""

from __future__ import annotations

import json
import textwrap
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# ── Test fixtures ──────────────────────────────────────────────────────────────

BASE_TEX = textwrap.dedent(r"""
\documentclass[letterpaper,10.5pt]{article}
\begin{document}

\begin{center}
    \textbf{\Huge \scshape Yash Kherwal} \\ \vspace{1pt}
    \small +91 9891148156 $|$ yash.kherwal78@gmail.com
\end{center}

\section{Experience}
\resumeSubHeadingListStart

  \resumeSubheading
    {OrangeLabs}{Feb 2026 -- Apr 2026}
    {AI Product Manager Intern}{}
  \resumeItemListStart
    \resumeItem{Owned end-to-end product development of two AI features; \kw{AI Attendance System} eliminated manual roll calls.}
    \resumeItem{Conducted \kw{customer discovery} with school administrators; shipped \kw{AI Video Lecture Generator}.}
    \resumeItem{Contributed to \kw{product roadmap} in collaboration with co-founders.}
  \resumeItemListEnd

  \resumeSubheading
    {ScoreMe Solutions}{May 2025 -- June 2025}
    {Software Development Intern}{}
  \resumeItemListStart
    \resumeItem{Scoped and shipped a \kw{two-stage PDF classification pipeline}; automated ~80\% of document volume.}
    \resumeItem{Defined \kw{confidence threshold} as an explicit \kw{human-in-the-loop gate}.}
  \resumeItemListEnd

\resumeSubHeadingListEnd

\section{Projects}
\resumeSubHeadingListStart

  \resumeProjectHeading
    {\textbf{CareerAutomated} $|$ \emph{Python, LangGraph}}{2025}
  \resumeItemListStart
    \resumeItem{Building an \kw{autonomous AI recruiting platform} orchestrating multi-agent workflows.}
    \resumeItem{Designed a \kw{Generator-Critic architecture} for personalised outreach.}
    \resumeItem{Engineered \kw{scalable data pipelines} using \kw{SQLite} and \kw{Pandas}.}
  \resumeItemListEnd

\resumeSubHeadingListEnd

\section{Technical Skills}
\begin{itemize}
  \small{\item{
    \textbf{AI/ML:} LangGraph, LangChain, Groq/LLaMA \\
  }}
\end{itemize}

\end{document}
""").strip()

SAMPLE_JD_PROFILE: Dict[str, Any] = {
    "job_id": "test_job_001",
    "company_name": "Acme AI",
    "role_title": "AI Engineer",
    "ats_keywords": [
        {"keyword": "LangGraph", "normalized_keyword": "langgraph", "weight": 1.0},
        {"keyword": "FastAPI", "normalized_keyword": "fastapi", "weight": 0.9},
    ],
    "required_skills": [],
    "technologies": ["python", "langgraph"],
    "responsibilities": ["Build AI agents", "Design scalable systems"],
    "strategy_signals": {
        "role_type": "AI Engineer",
        "primary_domain": "AI",
        "summary_strategy": "Calibrate towards AI engineering.",
        "bullet_strategy": "Emphasize system design and LLM usage.",
        "preferred_ownership_style": "OWNER",
        "priority_keywords": ["LangGraph", "multi-agent"],
        "priority_project_types": ["AI Engineer", "AI"],
    },
}


# ── Parser tests ───────────────────────────────────────────────────────────────

class TestJakeTexParser:

    def _parser(self):
        from src.resume_intelligence.tailoring.jake_tex_parser import JakeTexParser
        return JakeTexParser()

    def test_parses_experience_section(self):
        tree = self._parser().parse(BASE_TEX)
        exp_sections = [s for s in tree.sections if s.name == "Experience"]
        assert len(exp_sections) == 1
        assert len(exp_sections[0].entries) == 2

    def test_parses_correct_bullet_count(self):
        tree = self._parser().parse(BASE_TEX)
        exp = next(s for s in tree.sections if s.name == "Experience")
        assert len(exp.entries[0].bullets) == 3   # OrangeLabs
        assert len(exp.entries[1].bullets) == 2   # ScoreMe

    def test_parses_project_section(self):
        tree = self._parser().parse(BASE_TEX)
        proj_sections = [s for s in tree.sections if s.name == "Projects"]
        assert len(proj_sections) == 1
        assert len(proj_sections[0].entries[0].bullets) == 3

    def test_contact_block_locked(self):
        tree = self._parser().parse(BASE_TEX)
        assert "Yash Kherwal" in tree.contact_block

    def test_skills_block_locked(self):
        tree = self._parser().parse(BASE_TEX)
        assert "LangGraph" in tree.skills_block

    def test_heading_tokens_extracted(self):
        tree = self._parser().parse(BASE_TEX)
        exp = next(s for s in tree.sections if s.name == "Experience")
        assert exp.entries[0].heading_tokens[0] == "OrangeLabs"
        assert exp.entries[0].heading_tokens[2] == "AI Product Manager Intern"

    def test_char_offsets_are_correct(self):
        """Verify char_start/char_end offsets point to actual bullet content."""
        tree = self._parser().parse(BASE_TEX)
        exp = next(s for s in tree.sections if s.name == "Experience")
        bullet = exp.entries[0].bullets[0]
        extracted = BASE_TEX[bullet.char_start:bullet.char_end]
        assert "Owned end-to-end" in extracted


# ── Macro guard tests ──────────────────────────────────────────────────────────

class TestMacroGuard:

    def _mg(self):
        from src.resume_intelligence.tailoring.macro_guard import MacroGuard
        return MacroGuard

    def test_masks_kw_macro(self):
        MG = self._mg()
        text = r"Built \kw{Python} pipeline."
        masked, pmap, _ = MG.mask(text)
        assert r"\kw{Python}" not in masked
        assert "__KW_" in masked
        assert r"\kw{Python}" in pmap.from_placeholder.values()

    def test_restores_kw_macro(self):
        MG = self._mg()
        text = r"Built \kw{Python} pipeline."
        masked, pmap, _ = MG.mask(text)
        restored = MG.restore(masked, pmap)
        assert restored == text

    def test_masks_href_macro(self):
        MG = self._mg()
        text = r"See \href{https://example.com}{link} for details."
        masked, pmap, _ = MG.mask(text)
        assert r"\href" not in masked

    def test_roundtrip_multiple_macros(self):
        MG = self._mg()
        text = r"Used \kw{LangGraph} and \textbf{FastAPI} to build \kw{agents}."
        masked, pmap, _ = MG.mask(text)
        restored = MG.restore(masked, pmap)
        assert restored == text

    def test_globally_unique_counters(self):
        MG = self._mg()
        t1 = r"\kw{A}"
        t2 = r"\kw{B}"
        m1, p1, counter = MG.mask(t1, counter_start=1)
        m2, p2, _ = MG.mask(t2, counter_start=counter)
        # No placeholder collision
        assert set(p1.from_placeholder.keys()).isdisjoint(set(p2.from_placeholder.keys()))

    def test_raise_on_unrestored_placeholder(self):
        from src.resume_intelligence.tailoring.macro_guard import MacroRestoreError, PlaceholderMap
        MG = self._mg()
        pmap = PlaceholderMap()
        with pytest.raises(MacroRestoreError):
            MG.restore("Hello __KW_99__ world", pmap)

    def test_has_unrestored_placeholders_true(self):
        MG = self._mg()
        assert MG.has_unrestored_placeholders("text __KW_1__ here")

    def test_has_unrestored_placeholders_false(self):
        MG = self._mg()
        assert not MG.has_unrestored_placeholders("clean text here")


# ── Structural guard lock tests ────────────────────────────────────────────────

class TestStructuralGuardLock:

    def _lock(self):
        from src.resume_intelligence.tailoring.guardrails import StructuralGuardLock
        return StructuralGuardLock()

    def test_counts_resumeitem(self):
        snap = self._lock().snapshot(BASE_TEX)
        assert snap.resumeitem_count == 8  # 3+2 experience + 3 project

    def test_counts_resumesubheading(self):
        snap = self._lock().snapshot(BASE_TEX)
        assert snap.resumesubheading_count == 2

    def test_counts_resumeprojectheading(self):
        snap = self._lock().snapshot(BASE_TEX)
        assert snap.resumeprojectheading_count == 1

    def test_locked_field_tokens_include_company(self):
        snap = self._lock().snapshot(BASE_TEX)
        assert "OrangeLabs" in snap.locked_field_tokens
        assert "ScoreMe Solutions" in snap.locked_field_tokens


# ── Integrity gate tests ───────────────────────────────────────────────────────

class TestIntegrityGate:

    def _setup(self):
        from src.resume_intelligence.tailoring.guardrails import (
            FactualEntityExtractor, IntegrityGate, StructuralGuardLock
        )
        snap = StructuralGuardLock().snapshot(BASE_TEX)
        entities = FactualEntityExtractor().extract(BASE_TEX)
        gate = IntegrityGate()
        return gate, snap, entities

    def test_passes_on_identical_tex(self):
        gate, snap, entities = self._setup()
        report = gate.check(BASE_TEX, BASE_TEX, snap, entities)
        assert report.passed

    def test_detects_missing_company(self):
        gate, snap, entities = self._setup()
        tampered = BASE_TEX.replace("OrangeLabs", "SomeCorp")
        report = gate.check(BASE_TEX, tampered, snap, entities)
        assert not report.passed
        assert any("OrangeLabs" in v for v in report.violations)

    def test_detects_extra_resumeitem(self):
        gate, snap, entities = self._setup()
        tampered = BASE_TEX + r"\resumeItem{Injected bullet}"
        report = gate.check(BASE_TEX, tampered, snap, entities)
        assert not report.passed
        assert any("resumeItem" in v for v in report.violations)

    def test_detects_technology_substitution(self):
        gate, snap, entities = self._setup()
        tampered = BASE_TEX.replace("SQLite", "PostgreSQL").replace("Pandas", "Polars")
        report = gate.check(BASE_TEX, tampered, snap, entities)
        # SQLite is in _KNOWN_TECHNOLOGIES; check it's flagged
        assert any("SQLite" in v for v in report.violations)

    def test_detects_unrestored_placeholder(self):
        gate, snap, entities = self._setup()
        tampered = BASE_TEX.replace("OrangeLabs", "__KW_1__")
        report = gate.check(BASE_TEX, tampered, snap, entities)
        assert not report.passed
        assert any("UNRESTORED" in v for v in report.violations)


# ── Confidence filter tests ────────────────────────────────────────────────────

class TestConfidenceFilter:

    def _run(self, ops, entries_bullets, threshold=0.70):
        from src.resume_intelligence.tailoring.engine_v1 import _apply_confidence_filter
        from src.resume_intelligence.tailoring.jake_tex_parser import ParsedBullet, ParsedEntry

        parsed_entries = []
        for bullet_texts in entries_bullets:
            bullets = [
                ParsedBullet(raw_content=t, char_start=0, char_end=len(t))
                for t in bullet_texts
            ]
            parsed_entries.append(
                ParsedEntry(entry_type="experience", heading_tokens=["Co"], bullets=bullets)
            )

        final, kept, conf = _apply_confidence_filter(ops, parsed_entries, threshold)
        return final, kept, conf

    def test_high_confidence_accepted(self):
        from src.resume_intelligence.tailoring.models_v1 import BulletPatchOp
        ops = [BulletPatchOp(entry=0, bullet=0, replace_with="Engineered X.", confidence=0.95)]
        final, kept, _ = self._run(ops, [["Original text."]])
        assert final[(0, 0)] == "Engineered X."
        assert kept[(0, 0)] is False

    def test_low_confidence_keeps_original(self):
        from src.resume_intelligence.tailoring.models_v1 import BulletPatchOp
        ops = [BulletPatchOp(entry=0, bullet=0, replace_with="Rewritten.", confidence=0.50)]
        final, kept, _ = self._run(ops, [["Original text."]], threshold=0.70)
        assert final[(0, 0)] == "Original text."
        assert kept[(0, 0)] is True

    def test_missing_op_keeps_original(self):
        final, kept, _ = self._run([], [["Only bullet."]])
        assert final[(0, 0)] == "Only bullet."
        assert kept[(0, 0)] is True


# ── No-op detection tests ──────────────────────────────────────────────────────

class TestNoopDetection:

    def test_all_kept_is_noop(self):
        from src.resume_intelligence.tailoring.engine_v1 import _is_noop
        exp_kept = {(0, 0): True, (0, 1): True, (1, 0): True}
        proj_kept = {(0, 0): True, (0, 1): True}
        assert _is_noop(exp_kept, proj_kept, summary_changed=False) is True

    def test_enough_changes_is_not_noop(self):
        from src.resume_intelligence.tailoring.engine_v1 import _is_noop
        exp_kept = {(0, 0): False, (0, 1): False, (1, 0): False}
        proj_kept = {(0, 0): False, (0, 1): True}
        assert _is_noop(exp_kept, proj_kept, summary_changed=True) is False

    def test_empty_sections_is_noop(self):
        from src.resume_intelligence.tailoring.engine_v1 import _is_noop
        assert _is_noop({}, {}, summary_changed=True) is True


# ── LLM response parser tests ──────────────────────────────────────────────────

class TestLLMResponseParser:

    def _parse(self, raw):
        from src.resume_intelligence.tailoring.engine_v1 import _parse_llm_response
        return _parse_llm_response(raw)

    def test_parses_experience_ops(self):
        raw = json.dumps({
            "experience": [
                {"entry": 0, "bullet": 0, "replace_with": "Engineered X.", "keywords_added": ["LangGraph"], "confidence": 0.92},
                {"entry": 0, "bullet": 1, "replace_with": "Shipped Y.", "keywords_added": [], "confidence": 0.88},
            ]
        })
        resp = self._parse(raw)
        assert len(resp.experience) == 2
        assert resp.experience[0].replace_with == "Engineered X."
        assert resp.experience[0].confidence == 0.92

    def test_strips_markdown_fences(self):
        raw = "```json\n{\"summary\": \"Test summary.\", \"summary_confidence\": 0.9}\n```"
        resp = self._parse(raw)
        assert resp.summary == "Test summary."

    def test_invalid_json_returns_empty(self):
        resp = self._parse("not json at all {{")
        assert resp.experience == []
        assert resp.summary is None

    def test_skips_malformed_ops(self):
        raw = json.dumps({
            "experience": [
                {"entry": 0, "bullet": 0, "replace_with": "Good op.", "confidence": 0.9},
                {"no_entry_key": True},  # malformed — should be skipped
            ]
        })
        resp = self._parse(raw)
        assert len(resp.experience) == 1


# ── Semantic diff reporter tests ───────────────────────────────────────────────

class TestSemanticDiffReporter:

    def _reporter(self):
        from src.resume_intelligence.tailoring.diff_reporter import SemanticDiffReporter
        return SemanticDiffReporter(SAMPLE_JD_PROFILE)

    def test_detects_verb_change(self):
        reporter = self._reporter()
        entry = reporter._diff_bullet(
            section="Experience",
            heading="OrangeLabs",
            bullet_index=0,
            original="Built the system.",
            rewritten="Engineered the system.",
            kept_original=False,
            confidence=0.9,
        )
        assert entry.action_verb["old"] == "Built"
        assert entry.action_verb["new"] == "Engineered"

    def test_detects_keyword_added(self):
        reporter = self._reporter()
        entry = reporter._diff_bullet(
            section="Experience",
            heading="OrangeLabs",
            bullet_index=0,
            original="Built the pipeline.",
            rewritten="Built the LangGraph pipeline.",
            kept_original=False,
            confidence=0.9,
        )
        assert "langgraph" in entry.keywords_added

    def test_xyz_detected(self):
        reporter = self._reporter()
        entry = reporter._diff_bullet(
            section="Experience",
            heading="OrangeLabs",
            bullet_index=0,
            original="Built the pipeline.",
            rewritten="Engineered the pipeline, resulting in 50% latency reduction.",
            kept_original=False,
            confidence=0.9,
        )
        assert entry.xyz_used is True

    def test_ownership_demotion_detected(self):
        reporter = self._reporter()
        entry = reporter._diff_bullet(
            section="Experience",
            heading="OrangeLabs",
            bullet_index=0,
            original="Led the team to ship the feature.",
            rewritten="Assisted the team in shipping the feature.",
            kept_original=False,
            confidence=0.9,
        )
        assert entry.ownership_preserved is False


# ── Edge Case Test: All bullets failing fallback returns Base Resume ───────────

class TestAllBulletsFailingFallback:

    def test_all_bullets_failing_fallback_returns_base_resume(self):
        """
        Verify invariant: If every rewritten bullet fails validation (e.g. low confidence),
        the engine returns the original base resume with a valid report and is_noop = True.
        """
        from unittest.mock import patch
        from src.resume_intelligence.tailoring.engine_v1 import TailoringEngineV1
        from src.resume_intelligence.tailoring.models_v1 import TailoringInput
        from src.resume_intelligence.tests.test_tailoring_v1 import BASE_TEX, SAMPLE_JD_PROFILE

        # Mock LLM response where all confidence scores are 0.10 (below threshold 0.60)
        mock_summary = json.dumps({"summary": "Low conf summary", "summary_confidence": 0.10})
        mock_exp = json.dumps({
            "experience": [
                {"entry": 0, "bullet": 0, "replace_with": "Bad 1", "confidence": 0.10},
                {"entry": 0, "bullet": 1, "replace_with": "Bad 2", "confidence": 0.10},
                {"entry": 0, "bullet": 2, "replace_with": "Bad 3", "confidence": 0.10},
                {"entry": 1, "bullet": 0, "replace_with": "Bad 4", "confidence": 0.10},
                {"entry": 1, "bullet": 1, "replace_with": "Bad 5", "confidence": 0.10},
            ]
        })
        mock_proj = json.dumps({
            "projects": [
                {"entry": 0, "bullet": 0, "replace_with": "Bad 6", "confidence": 0.10},
                {"entry": 0, "bullet": 1, "replace_with": "Bad 7", "confidence": 0.10},
                {"entry": 0, "bullet": 2, "replace_with": "Bad 8", "confidence": 0.10},
            ]
        })

        with patch("src.resume_intelligence.tailoring.engine_v1.LLMCaller.call") as mock_call:
            mock_call.side_effect = [mock_summary, mock_exp, mock_proj]
            inp = TailoringInput(
                base_tex=BASE_TEX,
                candidate_memory={},
                jd_profile=SAMPLE_JD_PROFILE,
                confidence_threshold=0.60,
                llm_provider="mock",
                job_id="test_fallback_job"
            )
            engine = TailoringEngineV1()
            res = engine.tailor(inp)

        assert res.is_noop is True
        assert res.tailored_tex == BASE_TEX
        assert res.integrity_report.passed is True
        assert all(d.kept_original for d in res.diff_log)

