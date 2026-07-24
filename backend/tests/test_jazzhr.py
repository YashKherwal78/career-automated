"""Unit tests for JazzHR connector."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.discovery.connectors.jazzhr import JazzHRConnector, _strip_tags
from src.discovery.models import Board, BoardIdentity, FetchResult, RawJob
from src.discovery.pipeline.normalizers import JazzHRNormalizer

# ---------- fixtures ----------

MOCK_HTML = """
<html>
<body>
<table>
<tr id="row_job_1" class="resumator_even_row">
  <td>
    <a class="job_title_link" href="/apply/jobs/details/ep3PtoGGEJ?&">Senior Engineer</a>
    <br /><span class="resumator_department">Engineering</span>
  </td>
  <td>New York, NY</td>
</tr>
<tr id="row_job_2" class="resumator_odd_row">
  <td>
    <a class="job_title_link" href="/apply/jobs/details/xK9mNqRRfJ?&">Product Designer</a>
    <br /><span class="resumator_department">Design</span>
  </td>
  <td>Remote</td>
</tr>
<tr id="row_job_3" class="resumator_even_row">
  <td>
    <a class="job_title_link" href="/apply/jobs/details/aB1cDeFgHi?&">Sales Rep</a>
    <br /><span class="resumator_department">Sales</span>
  </td>
  <td>Chicago, IL</td>
</tr>
</table>
</body>
</html>
"""

EMPTY_HTML = """
<html><body><table></table></body></html>
"""


def _make_board(slug="testco"):
    return Board(
        company_id=f"{slug}-com-abc123",
        identity=BoardIdentity(ats="jazzhr"),
        endpoint=f"https://{slug}.applytojob.com/apply/jobs",
        provider="jazzhr",
        discovered_by="test",
        discovered_at=0.0,
        last_verified_at=0.0,
        metadata={},
    )


def _make_fetch_result(html, status=200):
    import hashlib
    content = html.encode("utf-8") if isinstance(html, str) else html
    return FetchResult(
        status_code=status,
        payload=html,
        etag=None,
        last_modified=None,
        content_hash=hashlib.sha256(content).hexdigest(),
        bytes_downloaded=len(content),
        response_headers={},
        request_duration_ms=50,
    )


# ---------- connector tests ----------

def test_parse_three_jobs():
    connector = JazzHRConnector()
    board = _make_board("testco")
    fetch_result = _make_fetch_result(MOCK_HTML)

    mock_client = AsyncMock()
    mock_client.fetch = AsyncMock(return_value=fetch_result)

    async def run():
        items = []
        async for item in connector.sync(board, mock_client):
            items.append(item)
        return items

    items = asyncio.run(run())
    raw_jobs = [i for i in items if isinstance(i, RawJob)]
    assert len(raw_jobs) == 3
    assert raw_jobs[0].payload["title"] == "Senior Engineer"
    assert raw_jobs[0].payload["department"] == "Engineering"
    assert raw_jobs[0].payload["location"] == "New York, NY"
    assert raw_jobs[0].payload["id"] == "ep3PtoGGEJ"
    assert raw_jobs[1].payload["title"] == "Product Designer"
    assert raw_jobs[1].payload["location"] == "Remote"
    assert raw_jobs[2].payload["title"] == "Sales Rep"


def test_empty_board():
    connector = JazzHRConnector()
    board = _make_board("emptyco")
    fetch_result = _make_fetch_result(EMPTY_HTML)

    mock_client = AsyncMock()
    mock_client.fetch = AsyncMock(return_value=fetch_result)

    async def run():
        items = []
        async for item in connector.sync(board, mock_client):
            items.append(item)
        return items

    items = asyncio.run(run())
    raw_jobs = [i for i in items if isinstance(i, RawJob)]
    assert len(raw_jobs) == 0


def test_404_board():
    connector = JazzHRConnector()
    board = _make_board("deadco")
    fetch_result = _make_fetch_result("", status=404)

    mock_client = AsyncMock()
    mock_client.fetch = AsyncMock(return_value=fetch_result)

    async def run():
        items = []
        async for item in connector.sync(board, mock_client):
            items.append(item)
        return items

    items = asyncio.run(run())
    raw_jobs = [i for i in items if isinstance(i, RawJob)]
    assert len(raw_jobs) == 0


def test_no_duplicate_ids():
    """Duplicate row IDs should be deduplicated."""
    dup_html = MOCK_HTML + """
<tr id="row_job_dup" class="resumator_even_row">
  <td>
    <a class="job_title_link" href="/apply/jobs/details/ep3PtoGGEJ?&">Senior Engineer</a>
    <br /><span class="resumator_department">Engineering</span>
  </td>
  <td>New York, NY</td>
</tr>
"""
    connector = JazzHRConnector()
    board = _make_board("testco")
    fetch_result = _make_fetch_result(dup_html)

    mock_client = AsyncMock()
    mock_client.fetch = AsyncMock(return_value=fetch_result)

    async def run():
        items = []
        async for item in connector.sync(board, mock_client):
            items.append(item)
        return items

    items = asyncio.run(run())
    raw_jobs = [i for i in items if isinstance(i, RawJob)]
    ids = [j.payload["id"] for j in raw_jobs]
    assert len(ids) == len(set(ids)), "Duplicate IDs detected"


def test_slug_extraction():
    connector = JazzHRConnector()
    assert connector._extract_slug("https://acme.applytojob.com/apply/jobs") == "acme"
    assert connector._extract_slug("https://my-company.applytojob.com/apply/jobs") == "my-company"


# ---------- normalizer tests ----------

def test_normalizer():
    normalizer = JazzHRNormalizer()
    raw = RawJob(
        company_id="testco-com-abc123",
        provider="jazzhr",
        board_identity=BoardIdentity(ats="jazzhr"),
        payload={
            "id": "ep3PtoGGEJ",
            "title": "Senior Engineer",
            "department": "Engineering",
            "location": "New York, NY",
            "url": "https://testco.applytojob.com/apply/jobs/details/ep3PtoGGEJ",
        },
    )
    canonical = normalizer.normalize(raw)
    assert len(canonical) == 1
    assert canonical[0].title == "Senior Engineer"
    assert canonical[0].department == "Engineering"
    assert canonical[0].location == "New York, NY"
    assert canonical[0].apply_url == "https://testco.applytojob.com/apply/jobs/details/ep3PtoGGEJ"


def test_normalizer_remote_detection():
    normalizer = JazzHRNormalizer()
    raw = RawJob(
        company_id="testco-com-abc123",
        provider="jazzhr",
        board_identity=BoardIdentity(ats="jazzhr"),
        payload={
            "id": "xK9mNqRRfJ",
            "title": "Product Designer",
            "department": "Design",
            "location": "Remote",
            "url": "https://testco.applytojob.com/apply/jobs/details/xK9mNqRRfJ",
        },
    )
    canonical = normalizer.normalize(raw)
    assert canonical[0].remote_type == "Remote"


def test_strip_tags():
    assert _strip_tags("<b>Hello</b> &amp; World") == "Hello & World"
    assert _strip_tags("   plain text   ") == "plain text"
