from src.career_intelligence.models.candidate import CandidateProfile, CandidateSkills
from src.discovery.jie.models import StructuredJob
from src.career_intelligence.ontology.backend import MemoryGraphBackend
from src.career_intelligence.ontology.service import CareerGraphService
from src.career_intelligence.ontology.cache import CachedGraphService
from src.career_intelligence.ontology.loader import OntologyLoader
from src.career_intelligence.capability.registry import CapabilityRegistry
from src.career_intelligence.capability.normalizer import DefaultCapabilityNormalizer
from src.career_intelligence.capability.mapper import DefaultCapabilityMapper
from src.career_intelligence.capability.extractor import DefaultCapabilityExtractor
from src.career_intelligence.pipeline.evidence_builder import DefaultEvidenceBuilder
from src.career_intelligence.pipeline.snapshot_builder import DefaultSnapshotBuilder
from src.career_intelligence.pipeline.comparison_pipeline import DefaultComparisonPipeline
from src.career_intelligence.comparison.engine import CareerComparisonEngine

def test_career_platform_pipeline():
    # 1. Setup Graph Backend and Service
    backend = MemoryGraphBackend()
    loader = OntologyLoader(backend)
    loader.load_default_fixtures()
    raw_service = CareerGraphService(backend)
    service = CachedGraphService(raw_service)

    # Validate traversal similarity logic
    assert service.check_similarity("next.js", "react") >= 0.8
    assert service.check_similarity("fastapi", "python") >= 0.8
    assert service.check_similarity("kubernetes", "docker") >= 0.8

    # 2. Setup Capability Layer normalizers, registries, and mappers
    registry = CapabilityRegistry()
    normalizer = DefaultCapabilityNormalizer()
    mapper = DefaultCapabilityMapper(registry, normalizer)
    extractor = DefaultCapabilityExtractor(registry, mapper)

    # Validate normalization
    assert normalizer.normalize("node.js") == "Node.js"
    assert normalizer.normalize("nextjs") == "Next.js"

    # Validate capability extraction
    caps = extractor.extract_from_text("We need a backend developer built using FastAPI and Python.")
    caps_names = [c.name for c in caps]
    assert "Backend Development" in caps_names
    assert "API Design" in caps_names

    # 3. Instantiate the orchestrated ComparisonPipeline
    comp_engine = CareerComparisonEngine()
    evidence_builder = DefaultEvidenceBuilder()
    snapshot_builder = DefaultSnapshotBuilder()
    pipeline = DefaultComparisonPipeline(comp_engine, evidence_builder, snapshot_builder)

    profile = CandidateProfile(
        summary="Experienced engineer with Node.js and React background.",
        skills=CandidateSkills(
            programming_languages=["JavaScript", "TypeScript"],
            frameworks=["React", "Node.js"]
        )
    )
    job = StructuredJob(
        jd_hash="hash456",
        jie_version="3.0.0",
        parsed_at="2026-07-24T00:00:00Z",
        title="Full Stack Software Engineer",
        company="GitHub",
        location={"country": "US", "state": "CA", "city": "San Francisco"},
        work_mode="Remote",
        employment_type="Full-time",
        experience_min=3,
        education=["Bachelor's"],
        technologies=["Node.js", "React", "Docker"],
        skills=["System Design"]
    )

    # Execute pipeline
    result = pipeline.execute(profile, job)
    
    # Assert result conforms to model specifications
    assert result.metadata["candidate_capabilities"] is not None
    assert len(result.evidence) > 0
    
    # Assert evidence builders identified exact matches and missing requirements
    evidence_types = [e.evidence_type for e in result.evidence]
    assert "exact_match" in evidence_types
    assert "missing_requirement" in evidence_types

    print("All Pipeline infrastructure unit tests passed successfully!")
