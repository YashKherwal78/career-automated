import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.career_intelligence.models import CandidateProfile, CandidateExperience, CandidateProject, CandidateSkills
from src.discovery.jie.models import StructuredJob
from src.career_intelligence.matching.engine import MatchScoreEngine
from src.career_intelligence.tailoring.engine import ResumeTailoringEngine
from src.career_intelligence.recommendations.engine import JobRecommendationEngine
from src.career_intelligence.filters.evaluator import JobFilterEvaluator

def test_career_intelligence_layer():
    # 1. Create a dummy CandidateProfile matching our onboarding parsed format
    profile = CandidateProfile(
        summary="Experienced Software Engineer specializing in Python and React.",
        experience=[
            CandidateExperience(
                company="TechCorp",
                role="Software Engineer",
                start_date="Jan 2024",
                end_date="Present",
                bullet_points=["Build REST APIs in Python."],
                technologies=["Python", "FastAPI"],
                employment_type="Full-time"
            )
        ],
        projects=[
            CandidateProject(
                name="Portal",
                technologies=["React", "TypeScript"]
            )
        ],
        skills=CandidateSkills(
            programming_languages=["Python", "TypeScript"],
            frameworks=["React", "FastAPI"]
        ),
        location={"country": "India", "state": "Karnataka", "city": "Bangalore"}
    )
    # Set candidate profile location text property
    profile.personal_info.location = "Bangalore, Karnataka, India"

    # 2. Create a StructuredJob description representing the requirements
    job = StructuredJob(
        jd_hash="hash123",
        jie_version="3.0.0",
        parsed_at="2026-07-24T00:00:00Z",
        title="Fullstack Developer",
        company="Stripe",
        location={"country": "India", "state": "Karnataka", "city": "Bangalore"},
        work_mode="Remote",
        employment_type="Full-time",
        experience_min=2,
        experience_max=5,
        education=["Bachelor's"],
        technologies=["Python", "React", "Docker"],
        skills=["System Design"]
    )

    # 3. Test MatchScoreEngine
    engine = MatchScoreEngine()
    match_res = engine.calculate_match(profile, job)
    assert match_res["overall_score"] > 0
    assert "technologies" in match_res["breakdown"]
    
    # 4. Test ResumeTailoringEngine
    tailor_engine = ResumeTailoringEngine()
    tailor_plan = tailor_engine.generate_tailoring_plan(profile, job)
    assert len(tailor_plan["keyword_optimizations"]) > 0
    # Suggests adding Docker (which candidate is missing)
    missing_techs = [x["canonical_value"] for x in tailor_plan["keyword_optimizations"]]
    assert "Docker" in missing_techs

    # 5. Test JobRecommendationEngine
    rec_engine = JobRecommendationEngine()
    recs = rec_engine.get_recommendations(profile, [job])
    assert "best_matching_jobs" in recs
    assert "hidden_opportunities" in recs

    # 6. Test JobFilterEvaluator
    assert JobFilterEvaluator.match_filters(job, {"work_mode": "Remote"}) is True
    assert JobFilterEvaluator.match_filters(job, {"location": {"city": "Bangalore"}}) is True
    assert JobFilterEvaluator.match_filters(job, {"location": {"city": "Delhi"}}) is False

    print("All Career Intelligence Layer integration tests passed successfully!")

if __name__ == '__main__':
    test_career_intelligence_layer()
