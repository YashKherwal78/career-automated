from src.career_intelligence.models.common import (
    Identifier, Timestamp, Metadata, Score, Confidence, Version, ArtifactVersion, AuditInfo, SourceReference
)
from src.career_intelligence.models.candidate import (
    PersonalInfo, CandidateEducation, CandidateExperience, CandidateProject, CandidateSkills,
    CandidateCertification, CandidatePublication, CandidateLink, CandidateProfile
)
from src.career_intelligence.models.comparison import (
    SkillComparison, TechnologyComparison, ExperienceComparison, EducationComparison,
    ProjectComparison, CertificationComparison, LocationComparison, EmploymentComparison,
    ResponsibilityComparison, LanguageComparison, ComparisonResult, ScoreBreakdown, MatchScore,
    Gap, LearningRecommendation, GapAnalysis
)
from src.career_intelligence.models.evidence import Evidence
from src.career_intelligence.models.snapshot import ComparisonContext, ComparisonSnapshot
from src.career_intelligence.models.ontology import OntologyNode, OntologyRelationship
from src.career_intelligence.models.capability import Capability
from src.career_intelligence.models.quality import (
    ResumeCompleteness, ProfileQuality, ExtractionConfidence, ComparisonConfidence,
    RecommendationConfidence, TailoringConfidence, LearningRecommendationConfidence
)
