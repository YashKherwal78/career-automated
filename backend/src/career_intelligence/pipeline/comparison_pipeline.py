from typing import List
from src.career_intelligence.models.comparison import ComparisonResult
from src.career_intelligence.models.candidate import CandidateProfile
from src.discovery.jie.models import StructuredJob
from src.career_intelligence.pipeline.interfaces import ComparisonPipeline, EvidenceBuilder, SnapshotBuilder
from src.career_intelligence.comparison.engine import CareerComparisonEngine
from src.career_intelligence.capability.extractor import DefaultCapabilityExtractor
from src.career_intelligence.capability.registry import CapabilityRegistry
from src.career_intelligence.capability.mapper import DefaultCapabilityMapper
from src.career_intelligence.capability.normalizer import DefaultCapabilityNormalizer

class DefaultComparisonPipeline(ComparisonPipeline):
    def __init__(
        self,
        comparison_engine: CareerComparisonEngine,
        evidence_builder: EvidenceBuilder,
        snapshot_builder: SnapshotBuilder
    ):
        self.comparison_engine = comparison_engine
        self.evidence_builder = evidence_builder
        self.snapshot_builder = snapshot_builder
        
        # Capability layer setup
        registry = CapabilityRegistry()
        normalizer = DefaultCapabilityNormalizer()
        mapper = DefaultCapabilityMapper(registry, normalizer)
        self.capability_extractor = DefaultCapabilityExtractor(registry, mapper)

    def execute(self, profile: CandidateProfile, job: StructuredJob) -> ComparisonResult:
        """Coordinates: Capability Extraction -> Comparison -> Evidence -> Snapshot."""
        # 1. Extract capabilities from text and attach to metadata
        caps_cand = self.capability_extractor.extract_from_text(profile.summary or "")
        
        # 2. Run core domain comparers
        comparison = self.comparison_engine.compare(profile, job)
        
        # 3. Build explainable evidence objects
        evidence_list = self.evidence_builder.build_evidence(comparison)
        
        # 4. Return new result incorporating evidence list
        # Since comparison is frozen, we reconstruct it cleanly
        result = ComparisonResult(
            candidate_id=comparison.candidate_id,
            job_id=comparison.job_id,
            generated_at=comparison.generated_at,
            profile_version=comparison.profile_version,
            job_version=comparison.job_version,
            context=comparison.context,
            skills=comparison.skills,
            technologies=comparison.technologies,
            education=comparison.education,
            experience=comparison.experience,
            projects=comparison.projects,
            certifications=comparison.certifications,
            location=comparison.location,
            employment=comparison.employment,
            responsibilities=comparison.responsibilities,
            languages=comparison.languages,
            strengths=comparison.strengths,
            weaknesses=comparison.weaknesses,
            warnings=comparison.warnings,
            metadata={"candidate_capabilities": [c.name for c in caps_cand]},
            evidence=evidence_list
        )
        
        # 5. Build snapshot record
        self.snapshot_builder.build_snapshot(result)
        
        return result
