import pytest
from src.discovery.connectors.smartrecruiters import SmartRecruitersConnector
from src.discovery.pipeline.normalizers import NormalizerFactory
from src.discovery.models import RawJob, Board, StandardBoardIdentity

MOCK_API_RESPONSE = {
    "content": [
        {
            "id": "abc-123",
            "name": "Software Engineer",
            "releasedDate": "2026-07-19T10:00:00.000Z",
            "location": {
                "city": "Paris",
                "region": "Île-de-France",
                "country": "France",
                "remote": True
            },
            "department": {"label": "Engineering"},
            "typeOfEmployment": {"id": "permanent", "label": "Full-time"},
            "refNumber": "REQ-001"
        }
    ]
}

def test_smartrecruiters_normalizer():
    raw_payload = MOCK_API_RESPONSE["content"][0]
    
    identity = StandardBoardIdentity(ats="smartrecruiters", board_token="Sobi")
    raw_job = RawJob(
        company_id="sobi-com",
        provider="smartrecruiters",
        board_identity=identity,
        payload=raw_payload
    )
    
    normalizer = NormalizerFactory.get_normalizer("smartrecruiters")
    canonical_jobs = normalizer.normalize(raw_job)
    
    assert len(canonical_jobs) == 1
    job = canonical_jobs[0]
    assert job.title == "Software Engineer"
    assert job.location == "Paris, Île-de-France, France"
    assert job.remote_type == "Remote"
    assert job.employment_type == "Full-time"
    assert job.department == "Engineering"
    assert job.apply_url == "https://jobs.smartrecruiters.com/Sobi/abc-123"
