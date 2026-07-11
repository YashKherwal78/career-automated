import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.discovery.jie.extractor import JDExtractor
from src.discovery.jie.normalizer import Normalizer
from src.discovery.jie.analyzer import FitAnalyzer, CandidateProfile

def test_jie_pipeline():
    with open('src/discovery/jie/fixtures/jd1.txt', 'r') as f:
        jd_text = f.read()
        
    title = "Backend Engineer (Python)"
    
    extractor = JDExtractor()
    normalizer = Normalizer()
    
    # Extract
    structured_job = extractor.extract(title, jd_text)
    
    # Assertions
    assert structured_job.experience_min == 3
    assert structured_job.experience_max == 5
    assert structured_job.work_mode == "Remote"
    assert structured_job.employment_type == "Full-time"
    
    # Normalize
    normalized_job = normalizer.normalize(structured_job)
    skill_names = [req.name for req in normalized_job.requirements if req.type == "skill"]
    assert "Python" in skill_names
    assert "SQL" in skill_names
    
    # Analyze
    candidate_profile = CandidateProfile(
        role_families=["Product", "AI"],
        experience_years=2,
        skills=["Python", "SQL", "Product Management", "A/B Testing", "FastAPI"],
        preferred_locations=["Bangalore", "Gurgaon", "Remote"],
        remote=True,
        employment=["Full-time"]
    )
    analyzer = FitAnalyzer(profile=candidate_profile)
    fit = analyzer.analyze(normalized_job)
    
    assert fit.experience.fit == False  # Candidate has 2, job needs 3
    assert "SQL" in fit.skills.matched
    assert fit.skills.coverage > 0
    
    print("All JIE pipeline tests passed successfully!")

if __name__ == '__main__':
    test_jie_pipeline()
