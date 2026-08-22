"""
Prompt Builder — section-level LLM prompt construction.

Builds three prompts per tailor() session (bounded by MAX_SECTION_CALLS = 5):
  1. SummaryPrompt
  2. ExperienceBatchPrompt   ← ALL experience entries in ONE call
  3. ProjectsBatchPrompt     ← ALL project entries in ONE call

Rules loaded from resume_knowledge2 (lazy, cached per instance):
  - summary_rules.yaml      → summary constraints
  - bullet_rules.yaml       → bullet constraints
  - action_verbs.yaml       → verb upgrade examples
  - validation_rules.yaml   → no_invented_numbers constraint
  - keyword_rules.yaml      → injection strategy

Design principles:
  - LLM returns JSON patch ops, never raw text (change #8)
  - Keywords are embedded directly in the prompt — no post-processing injector (change #6)
  - Prompt tokens are bounded per prompt_rules.yaml: target ≤ 400, hard max ≤ 600
  - Macros are already replaced with placeholders before prompts are built
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from textwrap import dedent
from typing import Any, Dict, List, Optional

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

from src.resume_intelligence.tailoring.jake_tex_parser import ParsedEntry, ParsedResumeTree


# ---------------------------------------------------------------------------
# Rule loader (lazy, cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _load_yaml_rule(rules_dir: str, filename: str) -> Dict[str, Any]:
    """Load and cache a single YAML rule file from resume_knowledge/rules/."""
    path = os.path.join(rules_dir, "rules", filename)
    if not os.path.exists(path):
        return {}
    if not _HAS_YAML:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_rules(kb_path: str) -> Dict[str, Any]:
    """Load all relevant rule files for prompt construction."""
    rule_files = [
        "bullet_rules.yaml",
        "summary_rules.yaml",
        "action_verbs.yaml",
        "validation_rules.yaml",
        "keyword_rules.yaml",
    ]
    merged: Dict[str, Any] = {}
    for fname in rule_files:
        merged[fname] = _load_yaml_rule(kb_path, fname)
    return merged


# ---------------------------------------------------------------------------
# JSON schema instructions injected into every prompt
# ---------------------------------------------------------------------------

_SUMMARY_JSON_SCHEMA = json.dumps({
    "summary": "<rewritten summary — 2-3 lines max>",
    "summary_confidence": 0.95,
}, indent=2)

_EXPERIENCE_JSON_SCHEMA = json.dumps({
    "experience": [
        {
            "entry": 0,
            "bullet": 0,
            "replace_with": "<rewritten bullet content>",
            "keywords_added": ["keyword1"],
            "confidence": 0.92,
        }
    ]
}, indent=2)

_PROJECTS_JSON_SCHEMA = json.dumps({
    "projects": [
        {
            "entry": 0,
            "bullet": 0,
            "replace_with": "<rewritten bullet content>",
            "keywords_added": ["keyword1"],
            "confidence": 0.90,
        }
    ]
}, indent=2)

# Shared constraint block injected into every prompt
_HARD_CONSTRAINTS = dedent("""\
HARD CONSTRAINTS (non-negotiable):
- Never invent facts, numbers, technologies, or achievements not present in the original
- Never remove or omit existing numbers, metrics, or percentages (e.g., 500+, ~80%, 10,000+, 3, 2, ~10, 50, sub-2s)
- Never remove or replace technology/framework/domain names (e.g., EUROCONTROL, ASTERIX, BGE-M3, AstraDB, Tesseract, SQLite, Pandas, Playwright, React Native, FastAPI, AWS EC2)
- Never change company names, job titles, project names, or dates
- Never drop or merge bullet points — output MUST contain exactly one patch op per bullet
- Preserve all __PLACEHOLDER__ tokens exactly as-is (they are LaTeX macros)
- Do not add new bullet points
- Max 28 words per bullet
- Start each bullet with a strong action verb
- No passive voice, no first-person pronouns
- If confidence < 0.70 for any bullet, set replace_with to the ORIGINAL text exactly
""")

# Confirmed real (2026-08-22): a bullet reading "Worked with engineering team
# on AI teacher-cloning voice pipeline" got rewritten with "Architected"/
# "Owned" as the lead verb -- upgrading a partial/supporting contribution
# into sole-ownership language the candidate never claimed. _HARD_CONSTRAINTS
# above already says "never invent facts" but has no explicit rule tying
# verb choice to the ORIGINAL bullet's stated contribution level, so the
# model filled that gap with whatever verb sounded most impressive.
_CONTRIBUTION_LEVEL_GUARDRAIL = dedent("""\
CONTRIBUTION LEVEL — determine this before choosing a verb for each bullet:

PARTIAL — original contains: "worked with", "contributed to", "helped", "supported",
          "collaborated", "assisted", "worked closely with"
FULL    — original contains: "built", "designed", "owned", "architected", "implemented",
          "led", "created", "developed", "shipped"
UNCLEAR — cannot tell from the text — treat as PARTIAL, never guess upward

If PARTIAL: lead verb must be one of Contributed, Supported, Collaborated, Assisted,
Partnered. Do NOT use Architected, Designed, Owned, Built, Led, Spearheaded,
Engineered, or any verb implying sole ownership — that upgrades the contribution
level, which is fabrication even if every technical fact in the bullet stays true.
If FULL: use a strong ownership verb as usual, still never "Was"/"Responsible for"/
"Helped"/"Worked on".

Example — original "Worked with engineering team on AI voice pipeline..." is PARTIAL:
  correct:   "Collaborated with engineering team to define quality thresholds..."
  WRONG:     "Architected AI voice pipeline..." (upgrades partial -> sole ownership)

""")

# Candidate-chosen style knobs (Settings > AI Preferences) — these only ever
# shape prompt wording/voice, never the hard constraints above. Tone and
# aggressiveness are deliberately independent axes (a "Bold" rewrite is still
# just as "Warm" or "Professional" as requested).
_TONE_INSTRUCTIONS: Dict[str, str] = {
    "Professional": "clear, professional, measured language",
    "Confident": "bold, confident language that foregrounds ownership and impact",
    "Warm": "warm, personable language that still reads as professional",
}

_AGGRESSIVENESS_INSTRUCTIONS: Dict[str, str] = {
    "Conservative": "Make minimal wording changes — stay close to the original phrasing and structure, adjusting only what's needed for relevance.",
    "Balanced": "Rewrite naturally for this role, balancing fidelity to the original with improved clarity and relevance.",
    "Bold": "Rewrite assertively for maximum impact and relevance to this specific role — restructure sentences freely for stronger framing.",
}


def build_style_instruction(writing_tone: str, tailoring_aggressiveness: str) -> str:
    tone = _TONE_INSTRUCTIONS.get(writing_tone, _TONE_INSTRUCTIONS["Professional"])
    aggressiveness = _AGGRESSIVENESS_INSTRUCTIONS.get(
        tailoring_aggressiveness, _AGGRESSIVENESS_INSTRUCTIONS["Balanced"]
    )
    return f"STYLE: Use {tone}. {aggressiveness}"


# ---------------------------------------------------------------------------
# Summary Prompt Builder
# ---------------------------------------------------------------------------

class SummaryPromptBuilder:

    @staticmethod
    def build(
        jd_profile: Dict[str, Any],
        base_resume_facts: List[str],
        candidate_memory_evidence: List[str],
        summary_rules: Dict[str, Any],
        current_summary: Optional[str] = None,
        style_instruction: str = "",
    ) -> str:
        """
        Builds the summary rewrite prompt.
        Returns a string ready to send to the LLM.
        """
        strategy = jd_profile.get("strategy_signals", {})
        role_type = strategy.get("role_type", "Software Engineer")
        domain = strategy.get("primary_domain", "Tech")
        summary_strategy = strategy.get("summary_strategy", "")
        priority_keywords = strategy.get("priority_keywords", [])
        company = jd_profile.get("company_name", "the company")

        evidence_block = "\n".join(f"- {e}" for e in base_resume_facts[:8])
        memory_block = "\n".join(f"- {e}" for e in candidate_memory_evidence[:4])
        keywords_block = ", ".join(priority_keywords[:6])

        constraints = summary_rules.get("constraints", {})
        max_lines = constraints.get("max_lines", 3)

        current_block = ""
        if current_summary:
            current_block = f"\nCURRENT SUMMARY (rewrite this):\n{current_summary}\n"

        prompt = dedent(f"""\
You are a professional resume editor. Rewrite the candidate summary for this specific role.
{style_instruction}

TARGET ROLE: {role_type} at {company}
DOMAIN: {domain}
STRATEGY: {summary_strategy}
PRIORITY KEYWORDS TO WEAVE IN (only if factually accurate): {keywords_block}

CANDIDATE FACTS (only use these — do not invent):
{evidence_block}

ADDITIONAL EVIDENCE:
{memory_block}
{current_block}
{_HARD_CONSTRAINTS}
SUMMARY RULES:
- Max {max_lines} lines
- Must mention role type
- Must be factually grounded in candidate facts above
- No generic phrases like "passionate problem solver"

OUTPUT: Return ONLY valid JSON matching this schema exactly:
{_SUMMARY_JSON_SCHEMA}
""")
        return prompt


# ---------------------------------------------------------------------------
# Experience Batch Prompt Builder
# ---------------------------------------------------------------------------

class ExperienceBatchPromptBuilder:

    @staticmethod
    def build(
        entries: List[ParsedEntry],
        jd_profile: Dict[str, Any],
        candidate_memory: Dict[str, Any],
        bullet_rules: Dict[str, Any],
        action_verbs: Dict[str, Any],
        style_instruction: str = "",
    ) -> str:
        """
        Builds a single prompt for ALL experience entries.
        All bullets are sent in one call; LLM returns patch ops for every bullet.
        """
        strategy = jd_profile.get("strategy_signals", {})
        role_type = strategy.get("role_type", "Software Engineer")
        bullet_strategy = strategy.get("bullet_strategy", "Emphasize impact and technical ownership.")
        priority_keywords = strategy.get("priority_keywords", [])
        ats_keywords = [k.get("keyword", "") for k in jd_profile.get("ats_keywords", [])][:8]
        keywords_block = ", ".join(list(dict.fromkeys(priority_keywords + ats_keywords))[:10])

        # Build entries block
        entries_lines: List[str] = []
        for ei, entry in enumerate(entries):
            company = entry.heading_tokens[0] if entry.heading_tokens else f"Entry {ei}"
            title = entry.heading_tokens[2] if len(entry.heading_tokens) > 2 else ""
            entries_lines.append(f"\nEntry {ei} — {company} ({title})")
            for bi, bullet in enumerate(entry.bullets):
                entries_lines.append(f"  Bullet {bi}: {bullet.raw_content}")

        entries_block = "\n".join(entries_lines)

        # Pull memory evidence relevant to experience
        global_evidence = candidate_memory.get("global", [])[:4]
        evidence_block = "\n".join(f"- {e}" for e in global_evidence)

        # Action verb examples from rules
        verb_examples = ""
        if action_verbs and isinstance(action_verbs, dict):
            strong = action_verbs.get("strong_verbs", {})
            if strong:
                sample = list(strong.items())[:3]
                verb_examples = "; ".join(f"'{k}' → '{v}'" for k, v in sample)

        prompt = dedent(f"""\
You are a professional resume editor. Rewrite the experience section bullets for this specific role.
{style_instruction}

TARGET ROLE: {role_type}
BULLET STRATEGY: {bullet_strategy}
KEYWORDS TO WEAVE IN (only if factually supported): {keywords_block}

ADDITIONAL CONTEXT (from candidate memory):
{evidence_block}

EXPERIENCE ENTRIES (with bullet indices):
{entries_block}

VERB UPGRADE EXAMPLES: {verb_examples}

{_HARD_CONSTRAINTS}
ABSOLUTE RULE FOR TECH NAMES AND NUMBERS:
Every technology name (e.g. ASTERIX, CAT048, EUROCONTROL, Tesseract, Random Forest) and every numeric metric (e.g. 500+, ~80%, 10,000+) present in the original bullet MUST be preserved in your rewritten bullet. Do NOT omit or simplify them. This is enforced downstream (any dropped name/number hard-blocks the whole tailoring run) so there is no room to trade evidence for better phrasing.

HOW TO REFRAME WITHOUT LOSING EVIDENCE:
Lead the bullet with whatever this JD cares about most (its own language, not generic filler) -- but that framing is an ADDITION, never a REPLACEMENT for the specifics already there. A rewrite that reads well but drops the scale/technology proof behind it is a worse bullet, not a more targeted one: it's the same failure as making the bullet vague. If the JD-relevant framing and the original evidence don't both fit comfortably, trim connective words, not facts.

{_CONTRIBUTION_LEVEL_GUARDRAIL}
CRITICAL: You must output a patch op for EVERY bullet listed above.
Missing a bullet means the resume is incomplete. Count entries and bullets carefully.

OUTPUT: Return ONLY valid JSON matching this schema exactly:
{_EXPERIENCE_JSON_SCHEMA}

The "experience" array must contain one object per bullet across all entries.
Use entry=<entry index> and bullet=<bullet index within that entry>.
""")
        return prompt


# ---------------------------------------------------------------------------
# Projects Batch Prompt Builder
# ---------------------------------------------------------------------------

class ProjectsBatchPromptBuilder:

    @staticmethod
    def build(
        entries: List[ParsedEntry],
        jd_profile: Dict[str, Any],
        bullet_rules: Dict[str, Any],
        style_instruction: str = "",
    ) -> str:
        """
        Builds a single prompt for ALL project entries.
        """
        strategy = jd_profile.get("strategy_signals", {})
        role_type = strategy.get("role_type", "Software Engineer")
        priority_project_types = strategy.get("priority_project_types", [])
        ats_keywords = [k.get("keyword", "") for k in jd_profile.get("ats_keywords", [])][:6]
        keywords_block = ", ".join(ats_keywords)

        entries_lines: List[str] = []
        for ei, entry in enumerate(entries):
            title = entry.heading_tokens[0] if entry.heading_tokens else f"Project {ei}"
            entries_lines.append(f"\nProject {ei} — {title}")
            for bi, bullet in enumerate(entry.bullets):
                entries_lines.append(f"  Bullet {bi}: {bullet.raw_content}")

        entries_block = "\n".join(entries_lines)
        proj_types_block = ", ".join(priority_project_types[:4]) or role_type

        prompt = dedent(f"""\
You are a professional resume editor. Rewrite the project section bullets for this specific role.
{style_instruction}

TARGET ROLE: {role_type}
RELEVANT PROJECT TYPES: {proj_types_block}
KEYWORDS TO WEAVE IN (only if factually supported): {keywords_block}

PROJECT ENTRIES (with bullet indices):
{entries_block}

{_HARD_CONSTRAINTS}
ABSOLUTE RULE FOR TECH NAMES AND NUMBERS:
Every technology name (e.g. BGE-M3, BM25, AstraDB, FastAPI, AWS EC2, LangGraph, SQLite, Pandas, Playwright, React Native) and every numeric metric (e.g. 500+, 10,000+, sub-2s) present in the original bullet MUST be preserved in your rewritten bullet. Do NOT omit or simplify them.

CRITICAL: You must output a patch op for EVERY bullet listed above.

OUTPUT: Return ONLY valid JSON matching this schema exactly:
{_PROJECTS_JSON_SCHEMA}

The "projects" array must contain one object per bullet across all project entries.
Use entry=<project index> and bullet=<bullet index within that project>.
""")
        return prompt


# ---------------------------------------------------------------------------
# Prompt Builder (facade)
# ---------------------------------------------------------------------------

class PromptBuilder:
    """
    Facade: loads rules once and exposes build_* methods.
    """

    def __init__(
        self,
        kb_path: str,
        writing_tone: str = "Professional",
        tailoring_aggressiveness: str = "Balanced",
    ):
        self.kb_path = kb_path
        self._rules = _load_rules(kb_path)
        self._style_instruction = build_style_instruction(writing_tone, tailoring_aggressiveness)

    def build_summary_prompt(
        self,
        jd_profile: Dict[str, Any],
        base_resume_facts: List[str],
        candidate_memory_evidence: List[str],
        current_summary: Optional[str] = None,
    ) -> str:
        return SummaryPromptBuilder.build(
            jd_profile=jd_profile,
            base_resume_facts=base_resume_facts,
            candidate_memory_evidence=candidate_memory_evidence,
            summary_rules=self._rules.get("summary_rules.yaml", {}),
            current_summary=current_summary,
            style_instruction=self._style_instruction,
        )

    def build_experience_prompt(
        self,
        entries: List[ParsedEntry],
        jd_profile: Dict[str, Any],
        candidate_memory: Dict[str, Any],
    ) -> str:
        return ExperienceBatchPromptBuilder.build(
            entries=entries,
            jd_profile=jd_profile,
            candidate_memory=candidate_memory,
            bullet_rules=self._rules.get("bullet_rules.yaml", {}),
            action_verbs=self._rules.get("action_verbs.yaml", {}),
            style_instruction=self._style_instruction,
        )

    def build_projects_prompt(
        self,
        entries: List[ParsedEntry],
        jd_profile: Dict[str, Any],
    ) -> str:
        return ProjectsBatchPromptBuilder.build(
            entries=entries,
            jd_profile=jd_profile,
            bullet_rules=self._rules.get("bullet_rules.yaml", {}),
            style_instruction=self._style_instruction,
        )
