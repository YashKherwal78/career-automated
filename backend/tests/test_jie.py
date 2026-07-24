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

def test_jie_structural_extractors():
    from src.discovery.jie.extractors.education import EducationExtractor
    from src.discovery.jie.extractors.experience import ExperienceExtractor
    from src.discovery.jie.extractors.technologies import TechnologyExtractor
    from src.discovery.jie.models import EducationInfo, ExperienceInfo
    
    # 1. Test EducationExtractor
    edu_extractor = EducationExtractor()
    edu_info = edu_extractor.extract("Requires a Bachelor of Technology in CSE and a Master's degree.")
    assert "Bachelor's" in edu_info.degrees
    assert "Master's" in edu_info.degrees
    assert "Computer Science" in edu_info.fields
    assert isinstance(edu_info, EducationInfo)
    
    # 2. Test ExperienceExtractor with word numbers
    exp_extractor = ExperienceExtractor()
    exp_info = exp_extractor.extract("Must have three to five years of experience. Fresher friendly.")
    assert exp_info.experience_min == 3
    assert exp_info.experience_max == 5
    assert exp_info.fresher_friendly is False  # Min is 3, overrides entry-level
    
    exp_info_fresher = exp_extractor.extract("Graduate Program or recent graduates welcome. No experience required.")
    assert exp_info_fresher.experience_min == 0
    assert exp_info_fresher.fresher_friendly is True
    assert isinstance(exp_info_fresher, ExperienceInfo)
    
    # 3. Test TechnologyExtractor with categories
    tech_extractor = TechnologyExtractor()
    techs = tech_extractor.extract("Experience with Python3, ReactJS, and postgres.")
    assert "Python" in techs
    assert "React" in techs
    assert "PostgreSQL" in techs
    
    techs_with_cat = tech_extractor.extract_with_categories("Docker and AWS.")
    names = [t["name"] for t in techs_with_cat]
    categories = [t["category"] for t in techs_with_cat]
    assert "Docker" in names
    assert "DevOps & Infrastructure" in categories
    assert "AWS" in names
    assert "Cloud Providers" in categories

if __name__ == '__main__':
    test_jie_pipeline()
    test_jie_structural_extractors()
