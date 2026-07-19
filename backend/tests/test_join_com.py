import pytest
from src.discovery.connectors.shared import NextJsParser, ProviderProfile
from src.discovery.connectors.join_com import JoinComConnector
from src.discovery.pipeline.normalizers import NormalizerFactory
from src.discovery.models import RawJob, Board, StandardBoardIdentity

# Mock Next.js HTML response
MOCK_HTML = b"""
<!DOCTYPE html>
<html>
<body>
  <script id="__NEXT_DATA__" type="application/json">
  {
    "buildId": "mock-build-123",
    "props": {
      "pageProps": {
        "initialState": {
          "jobs": {
            "items": [
              {
                "id": 12345,
                "idParam": "12345-software-engineer",
                "title": "Software Engineer",
                "createdAt": "2026-07-19T00:00:00.000Z",
                "workplaceType": "REMOTE",
                "city": {"cityName": "Berlin", "countryName": "Germany"},
                "employmentType": {"name": "Full-time"},
                "category": {"name": "Engineering"},
                "salaryAmountFrom": {"amount": 8000000, "currency": "EUR"},
                "settings": {"showSalary": true}
              }
            ],
            "pagination": {
              "page": 1,
              "pageCount": 1,
              "pageSize": 5,
              "perPage": 5,
              "total": 1
            }
          }
        }
      }
    }
  }
  </script>
</body>
</html>
"""

def test_next_js_parser():
    data, build_id = NextJsParser.extract_next_data(MOCK_HTML)
    assert data is not None
    assert build_id == "mock-build-123"
    
    initial_state = data.get("props", {}).get("pageProps", {}).get("initialState", {})
    items = initial_state.get("jobs", {}).get("items", [])
    assert len(items) == 1
    assert items[0]["title"] == "Software Engineer"

def test_join_com_normalizer():
    # Setup raw job from the mock items
    raw_payload = {
        "id": 12345,
        "idParam": "12345-software-engineer",
        "title": "Software Engineer",
        "createdAt": "2026-07-19T00:00:00.000Z",
        "workplaceType": "REMOTE",
        "city": {"cityName": "Berlin", "countryName": "Germany"},
        "employmentType": {"name": "Full-time"},
        "category": {"name": "Engineering"},
        "salaryAmountFrom": {"amount": 8000000, "currency": "EUR"},
        "settings": {"showSalary": True}
    }
    
    identity = StandardBoardIdentity(ats="join_com", board_token="test-company")
    raw_job = RawJob(
        company_id="test-company",
        provider="join_com",
        board_identity=identity,
        payload=raw_payload
    )
    
    normalizer = NormalizerFactory.get_normalizer("join_com")
    canonical_jobs = normalizer.normalize(raw_job)
    
    assert len(canonical_jobs) == 1
    job = canonical_jobs[0]
    assert job.title == "Software Engineer"
    assert job.location == "Berlin, Germany"
    assert job.remote_type == "Remote"
    assert job.employment_type == "Full-time"
    assert job.department == "Engineering"
    assert job.salary_min == 80000.0
    assert job.salary_currency == "EUR"
    assert job.apply_url == "https://join.com/companies/test-company/12345-software-engineer"

