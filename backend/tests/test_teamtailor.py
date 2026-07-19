import pytest
from src.discovery.connectors.teamtailor import TeamtailorConnector
from src.discovery.pipeline.normalizers import NormalizerFactory
from src.discovery.models import RawJob, Board, StandardBoardIdentity

def test_teamtailor_normalizer():
    raw_payload = {
        "id": "98765",
        "title": "Data Scientist",
        "description": "We are looking for a data scientist...",
        "location": "London, United Kingdom",
        "url": "https://careers.tecknuovo.com/jobs/98765"
    }
    
    identity = StandardBoardIdentity(ats="teamtailor", board_token="tecknuovo")
    raw_job = RawJob(
        company_id="tecknuovo-com",
        provider="teamtailor",
        board_identity=identity,
        payload=raw_payload
    )
    
    normalizer = NormalizerFactory.get_normalizer("teamtailor")
    canonical_jobs = normalizer.normalize(raw_job)
    
    assert len(canonical_jobs) == 1
    job = canonical_jobs[0]
    assert job.title == "Data Scientist"
    assert job.location == "London, United Kingdom"
    assert job.apply_url == "https://careers.tecknuovo.com/jobs/98765"
