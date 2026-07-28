"""
Ownership-Aware Rule Engine & Global Rewriter (resume_knowledge 2).

Preserves exact candidate ownership levels (LEAD vs OWNER vs CONTRIBUTOR vs SUPPORT)
while enhancing action verbs, removing weak phrasing, and enforcing Google XYZ principles.
"""

import re
import yaml
from typing import List, Dict, Any, Tuple
from src.resume_intelligence.canonical.base_resume_contract import BulletProvenance, OwnershipLevel


class OwnershipAwareRuleEngine:
    """Global Writing Intelligence Engine preserving candidate ownership levels."""

    # Ownership Level Classification Patterns
    LEAD_KEYWORDS = ["led", "spearheaded", "architected", "founded", "headed", "directed"]
    OWNER_KEYWORDS = ["built", "engineered", "developed", "designed", "shipped", "launched", "created", "owned"]
    CONTRIBUTOR_KEYWORDS = ["helped", "contributed", "assisted", "collaborated", "co-developed"]
    SUPPORT_KEYWORDS = ["supported", "maintained", "monitored", "updated", "documented"]

    # Safe Ownership-Preserving Verb Maps
    SAFE_VERB_MAPS = {
        OwnershipLevel.LEAD: {
            "led": "Spearheaded",
            "headed": "Directed",
            "architected": "Architected",
            "founded": "Established"
        },
        OwnershipLevel.OWNER: {
            "built": "Engineered",
            "created": "Developed",
            "designed": "Designed",
            "shipped": "Shipped",
            "developed": "Developed"
        },
        OwnershipLevel.CONTRIBUTOR: {
            "helped": "Contributed to",
            "assisted": "Assisted in",
            "collaborated": "Collaborated on",
            "co-developed": "Co-developed"
        },
        OwnershipLevel.SUPPORT: {
            "maintained": "Maintained",
            "supported": "Supported",
            "monitored": "Monitored"
        }
    }

    FILLER_PHRASES = ["in order to", "successfully", "duties included", "worked directly to", "was involved in"]

    def infer_ownership(self, text: str) -> OwnershipLevel:
        """Infers candidate's claimed level of responsibility from bullet phrasing."""
        low = text.lower()
        first_words = low.split()[:3]
        fw_str = " ".join(first_words)

        if any(k in fw_str for k in self.CONTRIBUTOR_KEYWORDS):
            return OwnershipLevel.CONTRIBUTOR
        if any(k in fw_str for k in self.LEAD_KEYWORDS):
            return OwnershipLevel.LEAD
        if any(k in fw_str for k in self.SUPPORT_KEYWORDS):
            return OwnershipLevel.SUPPORT
        return OwnershipLevel.OWNER

    def rewrite_bullet(self, provenance: BulletProvenance) -> BulletProvenance:
        """Rewrites bullet preserving exact ownership level and metrics."""
        original = provenance.original_text.strip()
        rewritten = original
        applied_rules = []

        # 1. Infer & Lock Ownership Level
        ownership = self.infer_ownership(original)
        provenance.claimed_ownership = ownership

        # 2. Eliminate Weak Fillers (without altering verb level)
        for filler in self.FILLER_PHRASES:
            if filler in rewritten.lower():
                pattern = re.compile(re.escape(filler), re.IGNORECASE)
                rewritten = pattern.sub("", rewritten).strip()
                rewritten = re.sub(r'\s+', ' ', rewritten)
                applied_rules.append(f"✓ Removed filler phrase '{filler}'")

        # 3. Apply Safe Ownership-Preserving Action Verb Optimization
        words = rewritten.split()
        if words:
            first_word_clean = words[0].rstrip(',.').lower()
            verb_map = self.SAFE_VERB_MAPS.get(ownership, {})
            if first_word_clean in verb_map:
                strong_verb = verb_map[first_word_clean]
                if words[0] != strong_verb:
                    if first_word_clean == "helped" and len(words) > 1 and words[1].lower() == "to":
                        words = [strong_verb] + words[2:]
                    else:
                        words[0] = strong_verb
                    rewritten = " ".join(words)
                    applied_rules.append(f"✓ Optimized action verb '{first_word_clean}' -> '{strong_verb}' (Preserved Ownership: {ownership.value})")

        # 4. Enforce ATS Punctuation
        if rewritten and not rewritten.endswith('.'):
            rewritten += '.'
            applied_rules.append("✓ Enforced ATS punctuation standard")

        # 5. Metric Safety Assertion
        metrics_found = re.findall(r'\b\d+(?:\.\d+)?%?\b', original)
        for m in metrics_found:
            assert m in rewritten, f"Metric safety violation: {m} lost during rewrite!"

        provenance.rewritten_text = rewritten
        provenance.rules_applied = applied_rules
        return provenance
