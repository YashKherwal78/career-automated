"""
Decoupled Normalization Subsystem (Refinement 3).

Standardizes RawExtraction blocks into structured Candidate Evidence.
Handles date normalization, entity recognition, contact extraction, and skill categorization.
"""

import re
from typing import List, Dict, Any
from src.resume_intelligence.parser.document_parser import RawExtraction
from src.resume_intelligence.evidence.merge_engine import EvidenceItem
from src.resume_intelligence.canonical.taxonomy import SkillTaxonomy


class Normalizer:
    """Decoupled Normalizer translating RawExtraction into normalized EvidenceItems."""

    def __init__(self):
        self.taxonomy = SkillTaxonomy()

    def normalize_extraction(self, raw: RawExtraction, source_type: str = "uploaded_resume") -> List[EvidenceItem]:
        evidence_items = []
        text = raw.raw_text

        # 1. Contact Extraction
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if emails:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"ev_email_{source_type}",
                    source_type=source_type,
                    confidence=0.99,
                    field_name="personal.email",
                    raw_value=emails[0],
                    normalized_value=emails[0].lower()
                )
            )

        phones = re.findall(r'\+?\d[\d\s-]{8,14}\d', text)
        if phones:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"ev_phone_{source_type}",
                    source_type=source_type,
                    confidence=0.95,
                    field_name="personal.phone",
                    raw_value=phones[0],
                    normalized_value=re.sub(r'\s+', ' ', phones[0])
                )
            )

        # 2. LinkedIn / GitHub
        linkedin = re.findall(r'linkedin\.com/in/[a-zA-Z0-9-]+', text)
        if linkedin:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"ev_linkedin_{source_type}",
                    source_type=source_type,
                    confidence=0.98,
                    field_name="social.linkedin",
                    raw_value=linkedin[0],
                    normalized_value=f"https://{linkedin[0]}"
                )
            )

        github = re.findall(r'github\.com/[a-zA-Z0-9-]+', text)
        if github:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"ev_github_{source_type}",
                    source_type=source_type,
                    confidence=0.98,
                    field_name="social.github",
                    raw_value=github[0],
                    normalized_value=f"https://{github[0]}"
                )
            )

        # 3. Name Inference (first non-empty header/line)
        for block in raw.blocks:
            if block.block_type in ["header", "text"] and len(block.content.split()) in [2, 3] and "@" not in block.content:
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=f"ev_name_{source_type}",
                        source_type=source_type,
                        confidence=0.90,
                        field_name="personal.full_name",
                        raw_value=block.content,
                        normalized_value=block.content.title()
                    )
                )
                break

        # 4. Skill Taxonomy Normalization
        found_skills = set()
        for word in ["Python", "FastAPI", "Docker", "SQL", "React Native", "LangGraph", "LangChain", "AstraDB", "BGE-M3", "AWS", "Pandas", "Scikit-learn"]:
            if re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE):
                canonical_name = self.taxonomy.canonicalize(word)
                found_skills.add(canonical_name)

        for sk in found_skills:
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"ev_skill_{sk.lower()}_{source_type}",
                    source_type=source_type,
                    confidence=0.95,
                    field_name="skills.item",
                    raw_value=sk,
                    normalized_value=sk
                )
            )

        return evidence_items
