from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ResumeCompleteness(BaseModel):
    score: int
    missing_sections: List[str] = Field(default_factory=list)
    empty_fields: List[str] = Field(default_factory=list)

class ProfileQuality(BaseModel):
    score: int
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)

class ExtractionConfidence(BaseModel):
    score: int
    ocr_confidence: Optional[int] = None
    validation_errors: List[str] = Field(default_factory=list)

class ComparisonConfidence(BaseModel):
    score: int
    overlap_quality: str
    missing_evidence_count: int

class RecommendationConfidence(BaseModel):
    score: int

class TailoringConfidence(BaseModel):
    score: int

class LearningRecommendationConfidence(BaseModel):
    score: int
