import pytest
from src.discovery.connectors.bamboohr import BambooHRConnector
from src.discovery.pipeline.normalizers import NormalizerFactory
from src.discovery.models import RawJob, Board, StandardBoardIdentity

def test_bamboohr_normalizer():
    raw_payload = {
        "id": "123",
        "title": "Software Engineer",
        "location": "Berlin, Germany",
        "department": "Engineering",
        "url": "https://adps.bamboohr.com/jobs/view.php?id=123"
    }
    
    identity = StandardBoardIdentity(ats="bamboohr", board_token="adps")
    raw_job = RawJob(
        company_id="adps-com",
        provider="bamboohr",
        board_identity=identity,
        payload=raw_payload
    )
    
    normalizer = NormalizerFactory.get_normalizer("bamboohr")
    canonical_jobs = normalizer.normalize(raw_job)
    
    assert len(canonical_jobs) == 1
    job = canonical_jobs[0]
    assert job.title == "Software Engineer"
    assert job.location == "Berlin, Germany"
    assert job.department == "Engineering"
    assert job.apply_url == "https://adps.bamboohr.com/jobs/view.php?id=123"
