import uuid
from typing import List
from src.career_intelligence.models.comparison import ComparisonResult
from src.career_intelligence.models.evidence import Evidence
from src.career_intelligence.models.common import SourceReference
from src.career_intelligence.pipeline.interfaces import EvidenceBuilder

class DefaultEvidenceBuilder(EvidenceBuilder):
    def build_evidence(self, comparison: ComparisonResult) -> List[Evidence]:
        """Constructs explainable Evidence objects from comparison indicators."""
        evidence_list = []
        
        # 1. Exact Matches
        for tech in comparison.technologies.exact_matches:
            evidence_list.append(Evidence(
                evidence_id=str(uuid.uuid4()),
                evidence_type="exact_match",
                source_symbol=tech,
                target_symbol=tech,
                weight=1.0,
                explanation=f"Exact match identified for technology '{tech}' on candidate profile.",
                confidence=1.0,
                references=[SourceReference(source_type="resume", source_id=comparison.candidate_id or "c1")]
            ))

        # 2. Semantic Matches
        for tech in comparison.technologies.semantic_matches:
            evidence_list.append(Evidence(
                evidence_id=str(uuid.uuid4()),
                evidence_type="semantic_inference",
                source_symbol=tech,
                target_symbol=tech,
                weight=0.9,
                explanation=f"Semantic relation resolved for tech '{tech}' using Career Ontology.",
                confidence=0.9,
                references=[SourceReference(source_type="ontology", source_id="career_ontology")]
            ))

        # 3. Missing Requirements
        for tech in comparison.technologies.missing:
            evidence_list.append(Evidence(
                evidence_id=str(uuid.uuid4()),
                evidence_type="missing_requirement",
                source_symbol=tech,
                target_symbol=tech,
                weight=1.0,
                explanation=f"Required technology '{tech}' not found on candidate profile.",
                confidence=1.0,
                references=[SourceReference(source_type="job_description", source_id=comparison.job_id or "j1")]
            ))
            
        return evidence_list
