# Google Forms Apply Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a backend pipeline that takes a job-post screenshot or a scanned Gmail job-alert, extracts company/role/apply-link, enriches it with a JD, routes it to the right applier (existing ATS adapter, a newly-verified ATS adapter, or a new Google Forms handler), and fills the (possibly multi-page) form — dry-run first, live once approved.

**Architecture:** New `backend/src/ingestion/` package produces a source-agnostic `JobLead`. `jd_enrichment.py` fills in a missing JD (internal DB → form's own description → web search). Routing extends the existing `ATSDetector`/`DetectorRegistry` (discovery-time) with a `GoogleFormsSignature`, adds a one-time endpoint-verification step against the existing `ats_registry` table for recognized-but-unverified ATS tenants, then hands off to the existing `apply_to_job()` entry point (`backend/src/applications/apply_service.py`) — either an existing ATS adapter (nothing new there) or the new `GoogleFormsHandler`/`GoogleFormsAdapter` pair, registered in `ApplicationDispatcher._ADAPTER_REGISTRY` exactly like the other 15. A new `backend/src/ingestion/pipeline.py` orchestrator ties it together and is driven by a CLI script for this no-frontend phase, writing to the same `backend/executions/<run_id>/` audit convention every other connector already uses.

**Tech Stack:** Python, Playwright (sync API, via existing `LaunchedBrowser`), Google Gemini (`google-genai`, via existing `LLMRouter`, extended with a vision method), existing raw-SQL DB layer (`src.api.db.get_connection`/`is_postgres`), pytest.

**Spec:** `docs/superpowers/specs/2026-08-18-google-forms-apply-pipeline-design.md`

## Global Constraints

- Dry-run first: every run this plan produces must default to `test_mode=True` until the user explicitly reviews a batch and asks for live. (Spec §5)
- No frontend work in this phase — CLI/script-driven only. (Spec: Non-goals)
- Minimize paid API calls in JD enrichment: internal DB match → form's own description text → web search, in that exact order, stopping at first hit. (Spec §2)
- Reuse existing infrastructure everywhere possible — do not duplicate `QuestionEngine`, `RAGClient`, `LaunchedBrowser`, `captcha_bridge`, the `executions/` audit convention, or the `ATSDetector`/`ApplicationDispatcher` mechanisms. (Spec: Architecture)
- New DB objects follow the existing raw-SQL migration convention in `backend/src/database/migrations/NNN_description.sql`, applied via `MigrationRunner`, using the dual Postgres/SQLite placeholder pattern (`"%s" if is_postgres() else "?"`) already used in `base_handler.py`. (Research: item 9)

---

## File Structure

```
backend/src/ingestion/
    __init__.py
    job_lead.py                 # JobLead dataclass
    screenshot_extractor.py     # image -> JobLead (vision LLM call)
    email_extractor.py          # Gmail scan -> list[JobLead]
    jd_enrichment.py            # fill in missing JD, 3-step fallback
    endpoint_verification.py    # verify+register an unverified ATS endpoint
    routing.py                  # apply_link -> connector key
    pipeline.py                 # orchestrator: lead -> ApplicationResult + audit record

backend/scripts/
    run_google_forms_batch.py   # CLI: point at a folder of screenshots, run the pipeline

backend/src/applications/handlers/
    google_forms.py             # new BaseATSHandler subclass

backend/src/applications/adapters/
    google_forms_adapter.py     # new BaseAdapter subclass

backend/src/database/migrations/
    041_ingested_job_leads.sql  # dedup/audit table for ingested leads
    042_processed_job_alert_emails.sql  # dedup table for scanned emails

backend/src/integrations/email_listener.py   # modified: + search_job_alerts()
backend/src/discovery/ats_detector.py        # modified: + GoogleFormsSignature
backend/src/applications/dispatcher.py       # modified: +1 registry entry
backend/src/utils/llm_router.py              # modified: + chat_completion_vision()

backend/tests/
    test_job_lead.py
    test_screenshot_extractor.py
    test_email_extractor.py
    test_jd_enrichment.py
    test_endpoint_verification.py
    test_routing.py
    test_google_forms_handler.py
    test_pipeline.py
```

---

### Task 1: `JobLead` dataclass + ingestion package skeleton

**Files:**
- Create: `backend/src/ingestion/__init__.py`
- Create: `backend/src/ingestion/job_lead.py`
- Test: `backend/tests/test_job_lead.py`

**Interfaces:**
- Produces: `JobLead` dataclass with fields `company: str`, `role: str`, `apply_link: str`, `location: str | None`, `jd_excerpt: str | None`, `source: Literal["screenshot", "email"]`, `source_ref: str`. Method `is_valid(self) -> bool` returns `True` only when `company`, `role`, and `apply_link` are all non-empty strings.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_job_lead.py
from src.ingestion.job_lead import JobLead


def test_is_valid_true_when_required_fields_present():
    lead = JobLead(
        company="Acme", role="Backend Engineer", apply_link="https://forms.gle/abc123",
        location=None, jd_excerpt=None, source="screenshot", source_ref="/tmp/shot.png",
    )
    assert lead.is_valid() is True


def test_is_valid_false_when_apply_link_missing():
    lead = JobLead(
        company="Acme", role="Backend Engineer", apply_link="",
        location=None, jd_excerpt=None, source="email", source_ref="msg-123",
    )
    assert lead.is_valid() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_job_lead.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ingestion'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/ingestion/__init__.py
```//(empty file)

```python
# backend/src/ingestion/job_lead.py
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class JobLead:
    company: str
    role: str
    apply_link: str
    location: Optional[str]
    jd_excerpt: Optional[str]
    source: Literal["screenshot", "email"]
    source_ref: str

    def is_valid(self) -> bool:
        return bool(self.company and self.role and self.apply_link)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_job_lead.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/ingestion/__init__.py backend/src/ingestion/job_lead.py backend/tests/test_job_lead.py
git commit -m "feat(ingestion): add JobLead dataclass"
```

---

### Task 2: `LLMRouter.chat_completion_vision()`

No vision-capable call exists anywhere in this codebase today (confirmed by research — `LLMRouter.chat_completion` is text-only). This task adds one, routed through Gemini only (the only client here with a multimodal API), following the existing `FakeResponse`/`log_llm_usage` conventions `chat_completion` already uses.

**Files:**
- Modify: `backend/src/utils/llm_router.py`
- Test: `backend/tests/test_llm_router_vision.py`

**Interfaces:**
- Consumes: `self.gemini_client` (already set in `_initialize()`), `genai_types` (already imported), `FakeResponse`/`log_llm_usage` (already in this file).
- Produces: `LLMRouter.chat_completion_vision(image_bytes: bytes, mime_type: str, prompt: str, response_format: Optional[Dict] = None) -> FakeResponse`. Raises `Exception` if Gemini isn't configured or the call fails — callers must catch it (screenshot_extractor.py in Task 3 does).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_llm_router_vision.py
from unittest.mock import MagicMock
from src.utils.llm_router import LLMRouter


def test_chat_completion_vision_calls_gemini_with_image_and_text_parts(monkeypatch):
    router = LLMRouter()
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.text = '{"company": "Acme"}'
    fake_response.usage_metadata.total_token_count = 42
    fake_client.models.generate_content.return_value = fake_response
    router.gemini_client = fake_client

    result = router.chat_completion_vision(
        image_bytes=b"fake-png-bytes",
        mime_type="image/png",
        prompt="Extract the company name as JSON.",
        response_format={"type": "json_object"},
    )

    assert result.choices[0].message.content == '{"company": "Acme"}'
    assert result.usage.total_tokens == 42
    call_kwargs = fake_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.0-flash"
    assert call_kwargs["config"].response_mime_type == "application/json"


def test_chat_completion_vision_raises_when_gemini_not_configured():
    router = LLMRouter()
    router.gemini_client = None
    try:
        router.chat_completion_vision(b"x", "image/png", "prompt")
        assert False, "expected an exception"
    except Exception as e:
        assert "Gemini" in str(e)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_router_vision.py -v`
Expected: FAIL with `AttributeError: 'LLMRouter' object has no attribute 'chat_completion_vision'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/src/utils/llm_router.py`, as a new method on `LLMRouter` (after `chat_completion`):

```python
    def chat_completion_vision(self, image_bytes: bytes, mime_type: str, prompt: str, response_format: Optional[Dict] = None) -> FakeResponse:
        """Gemini-only — the only client wired into this router with a
        multimodal API. Raises if Gemini isn't configured; callers must
        handle that (there is no cross-provider vision fallback here)."""
        if not self.gemini_client:
            raise Exception("Gemini client not initialized — chat_completion_vision requires GEMINI_API_KEY.")

        mime_out = "text/plain"
        if response_format and response_format.get("type") == "json_object":
            mime_out = "application/json"

        config = genai_types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type=mime_out,
        )

        model_name = "gemini-2.0-flash"
        start_time = time.time()
        response = self.gemini_client.models.generate_content(
            model=model_name,
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=config,
        )
        latency = time.time() - start_time

        tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens = response.usage_metadata.total_token_count

        log_llm_usage("vision_extraction", "gemini", model_name, tokens, latency, 0)
        return FakeResponse(response.text, tokens)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_llm_router_vision.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/utils/llm_router.py backend/tests/test_llm_router_vision.py
git commit -m "feat(llm): add Gemini-backed vision completion method"
```

---

### Task 3: `screenshot_extractor.py`

**Files:**
- Create: `backend/src/ingestion/screenshot_extractor.py`
- Test: `backend/tests/test_screenshot_extractor.py`

**Interfaces:**
- Consumes: `LLMRouter.chat_completion_vision(image_bytes, mime_type, prompt, response_format)` (Task 2), `JobLead` (Task 1).
- Produces: `extract_from_image(image_path: str, llm_router: LLMRouter = None) -> Optional[JobLead]`. Returns `None` (logging the reason) when the model's JSON is unparseable, or when `confidence < 0.5`, or when the resulting `JobLead.is_valid()` is `False` — never raises out of a bad extraction.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_screenshot_extractor.py
import json
from unittest.mock import MagicMock, patch
from src.ingestion.screenshot_extractor import extract_from_image


def _fake_router(payload: dict):
    router = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
    router.chat_completion_vision.return_value = response
    return router


def test_extract_from_image_returns_lead_on_valid_response(tmp_path):
    img = tmp_path / "post.png"
    img.write_bytes(b"\x89PNG\r\n fake bytes")
    router = _fake_router({
        "company": "Acme", "role": "Backend Engineer",
        "apply_link": "https://forms.gle/abc123", "location": "Remote",
        "jd_excerpt": "Build things.", "confidence": 0.9,
    })

    lead = extract_from_image(str(img), llm_router=router)

    assert lead is not None
    assert lead.company == "Acme"
    assert lead.apply_link == "https://forms.gle/abc123"
    assert lead.source == "screenshot"
    assert lead.source_ref == str(img)


def test_extract_from_image_returns_none_on_low_confidence(tmp_path):
    img = tmp_path / "post.png"
    img.write_bytes(b"\x89PNG\r\n fake bytes")
    router = _fake_router({
        "company": "Acme", "role": "Backend Engineer",
        "apply_link": "https://forms.gle/abc123", "location": None,
        "jd_excerpt": None, "confidence": 0.2,
    })

    lead = extract_from_image(str(img), llm_router=router)

    assert lead is None


def test_extract_from_image_returns_none_on_unparseable_json(tmp_path):
    img = tmp_path / "post.png"
    img.write_bytes(b"\x89PNG\r\n fake bytes")
    router = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content="not json"))]
    router.chat_completion_vision.return_value = response

    lead = extract_from_image(str(img), llm_router=router)

    assert lead is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_screenshot_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ingestion.screenshot_extractor'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/ingestion/screenshot_extractor.py
import json
import mimetypes
from typing import Optional

from src.system.logger import setup_logger
from src.utils.llm_router import LLMRouter
from src.ingestion.job_lead import JobLead

logger = setup_logger("screenshot_extractor")

_PROMPT = """You are looking at a screenshot of a social/job-board post \
advertising a job opening. Extract the following as strict JSON, no \
markdown fences, no commentary:

{
  "company": "<company name, or empty string if not visible>",
  "role": "<job title/role, or empty string if not visible>",
  "apply_link": "<the URL to apply, or empty string if none is visible>",
  "location": "<location if mentioned, else null>",
  "jd_excerpt": "<any job description text visible in the image (caption, bullet points), else null>",
  "confidence": <float 0.0-1.0, your confidence that company/role/apply_link are all correct>
}"""


def extract_from_image(image_path: str, llm_router: Optional[LLMRouter] = None) -> Optional[JobLead]:
    router = llm_router or LLMRouter()
    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/png"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    try:
        response = router.chat_completion_vision(
            image_bytes=image_bytes,
            mime_type=mime_type,
            prompt=_PROMPT,
            response_format={"type": "json_object"},
        )
        payload = json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.info(f"[screenshot_extractor] extraction failed for {image_path}: {e}")
        return None

    if payload.get("confidence", 0) < 0.5:
        logger.info(f"[screenshot_extractor] low confidence ({payload.get('confidence')}) for {image_path}, skipping")
        return None

    lead = JobLead(
        company=payload.get("company") or "",
        role=payload.get("role") or "",
        apply_link=payload.get("apply_link") or "",
        location=payload.get("location") or None,
        jd_excerpt=payload.get("jd_excerpt") or None,
        source="screenshot",
        source_ref=image_path,
    )

    if not lead.is_valid():
        logger.info(f"[screenshot_extractor] incomplete extraction for {image_path}: {payload}")
        return None

    return lead
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_screenshot_extractor.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/ingestion/screenshot_extractor.py backend/tests/test_screenshot_extractor.py
git commit -m "feat(ingestion): extract JobLead from a job-post screenshot"
```

---

### Task 4: `processed_job_alert_emails` migration + `EmailListener.search_job_alerts()` + `email_extractor.py`

**Files:**
- Create: `backend/src/database/migrations/042_processed_job_alert_emails.sql`
- Modify: `backend/src/integrations/email_listener.py`
- Create: `backend/src/ingestion/email_extractor.py`
- Test: `backend/tests/test_email_extractor.py`

**Interfaces:**
- Produces: `EmailListener.search_job_alerts(sender_allowlist: list[str], since_days: int = 3) -> list[dict]`, each dict shaped `{"message_id": str, "sender": str, "subject": str, "body": str}`. Produces: `email_extractor.scan_job_alerts(sender_allowlist: list[str] = None, since_days: int = 3) -> list[JobLead]`, deduped against `processed_job_alert_emails`.

- [ ] **Step 1: Write the migration**

```sql
-- backend/src/database/migrations/042_processed_job_alert_emails.sql
CREATE TABLE IF NOT EXISTS processed_job_alert_emails (
    message_id TEXT PRIMARY KEY,
    sender TEXT,
    subject TEXT,
    processed_at REAL NOT NULL
);
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_email_extractor.py
from unittest.mock import MagicMock, patch
from src.ingestion.email_extractor import scan_job_alerts


@patch("src.ingestion.email_extractor.get_connection")
@patch("src.ingestion.email_extractor.EmailListener")
def test_scan_job_alerts_skips_already_processed(mock_listener_cls, mock_get_connection):
    mock_listener = MagicMock()
    mock_listener.search_job_alerts.return_value = [
        {"message_id": "seen-1", "sender": "jobs@linkedin.com", "subject": "New jobs for you",
         "body": "Backend Engineer at Acme https://forms.gle/abc123"},
        {"message_id": "new-1", "sender": "jobs@linkedin.com", "subject": "New jobs for you",
         "body": "Frontend Engineer at Beta Inc https://forms.gle/def456"},
    ]
    mock_listener_cls.return_value = mock_listener

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {"message_id": "seen-1"},  # already processed
        None,                       # not processed
    ]
    mock_conn.execute.return_value = mock_cursor
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    leads = scan_job_alerts(sender_allowlist=["jobs@linkedin.com"], since_days=3)

    assert len(leads) == 1
    assert leads[0].company == "Beta Inc"
    assert leads[0].apply_link == "https://forms.gle/def456"
    assert leads[0].source == "email"
    assert leads[0].source_ref == "new-1"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_email_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ingestion.email_extractor'`

- [ ] **Step 4: Extend `EmailListener` with `search_job_alerts`**

Add to `backend/src/integrations/email_listener.py`, as a new method on `EmailListener` (after `get_latest_otp`):

```python
    def search_job_alerts(self, sender_allowlist: list, since_days: int = 3) -> list:
        """Read-only scan for job-alert emails from a known sender allowlist,
        within the last `since_days` days. Returns [{message_id, sender,
        subject, body}, ...] — no filtering/dedup here, that's the caller's
        job (see src.ingestion.email_extractor.scan_job_alerts)."""
        import datetime

        results = []
        try:
            mail = self._connect()
            since_date = (datetime.date.today() - datetime.timedelta(days=since_days)).strftime("%d-%b-%Y")

            for sender in sender_allowlist:
                status, messages = mail.search(None, f'(FROM "{sender}" SINCE "{since_date}")')
                if status != 'OK':
                    continue
                for email_id in messages[0].split():
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    for response_part in msg_data:
                        if not isinstance(response_part, tuple):
                            continue
                        msg = email.message_from_bytes(response_part[1])
                        message_id = msg.get("Message-ID", email_id.decode())
                        subject_raw, encoding = decode_header(msg.get("Subject", ""))[0]
                        subject = subject_raw.decode(encoding or "utf-8") if isinstance(subject_raw, bytes) else subject_raw

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    try:
                                        body += part.get_payload(decode=True).decode(errors="ignore")
                                    except Exception:
                                        pass
                        else:
                            try:
                                body = msg.get_payload(decode=True).decode(errors="ignore")
                            except Exception:
                                pass

                        results.append({
                            "message_id": message_id,
                            "sender": sender,
                            "subject": subject,
                            "body": body,
                        })

            mail.close()
            mail.logout()
        except Exception as e:
            logger.info(f"EmailListener.search_job_alerts Error: {e}")

        return results
```

- [ ] **Step 5: Write `email_extractor.py`**

```python
# backend/src/ingestion/email_extractor.py
import re
import time
from typing import List, Optional

from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres
from src.integrations.email_listener import EmailListener
from src.ingestion.job_lead import JobLead

logger = setup_logger("email_extractor")

DEFAULT_SENDER_ALLOWLIST = [
    "jobs-noreply@linkedin.com",
    "jobalerts-noreply@linkedin.com",
    "noreply@indeed.com",
    "noreply@glassdoor.com",
]

_URL_RE = re.compile(r"https?://\S+")


def _parse_email_body(body: str) -> Optional[dict]:
    """Best-effort parse: first URL in the body is the apply link; company/
    role are read from `Role at Company` or `Role - Company` patterns in the
    body text. Returns None if no URL is found at all."""
    urls = _URL_RE.findall(body)
    if not urls:
        return None
    apply_link = urls[0].rstrip(").,")

    role, company = "", ""
    match = re.search(r"([A-Za-z0-9 /&+\-]+?)\s+(?:at|@|-)\s+([A-Za-z0-9 &.,'\-]+)", body)
    if match:
        role, company = match.group(1).strip(), match.group(2).strip()

    return {"role": role, "company": company, "apply_link": apply_link}


def _is_processed(conn, message_id: str) -> bool:
    ph = "%s" if is_postgres() else "?"
    cur = conn.execute(f"SELECT message_id FROM processed_job_alert_emails WHERE message_id = {ph}", (message_id,))
    return cur.fetchone() is not None


def _mark_processed(conn, message_id: str, sender: str, subject: str):
    ph = "%s" if is_postgres() else "?"
    conn.execute(
        f"INSERT INTO processed_job_alert_emails (message_id, sender, subject, processed_at) VALUES ({ph}, {ph}, {ph}, {ph})",
        (message_id, sender, subject, time.time()),
    )
    conn.commit()


def scan_job_alerts(sender_allowlist: List[str] = None, since_days: int = 3) -> List[JobLead]:
    allowlist = sender_allowlist or DEFAULT_SENDER_ALLOWLIST
    listener = EmailListener()
    raw_emails = listener.search_job_alerts(allowlist, since_days=since_days)

    leads = []
    with get_connection() as conn:
        for raw in raw_emails:
            if _is_processed(conn, raw["message_id"]):
                continue

            parsed = _parse_email_body(raw["body"])
            if parsed:
                lead = JobLead(
                    company=parsed["company"], role=parsed["role"], apply_link=parsed["apply_link"],
                    location=None, jd_excerpt=None, source="email", source_ref=raw["message_id"],
                )
                if lead.is_valid():
                    leads.append(lead)
                else:
                    logger.info(f"[email_extractor] incomplete parse for {raw['message_id']}: {parsed}")
            else:
                logger.info(f"[email_extractor] no URL found in {raw['message_id']}")

            _mark_processed(conn, raw["message_id"], raw["sender"], raw["subject"])

    return leads
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_email_extractor.py -v`
Expected: PASS (1 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/src/database/migrations/042_processed_job_alert_emails.sql \
        backend/src/integrations/email_listener.py \
        backend/src/ingestion/email_extractor.py backend/tests/test_email_extractor.py
git commit -m "feat(ingestion): scan Gmail job-alert emails into JobLeads"
```

---

### Task 5: `ingested_job_leads` migration + dedup/DB-match step of `jd_enrichment.py`

**Files:**
- Create: `backend/src/database/migrations/041_ingested_job_leads.sql`
- Create: `backend/src/ingestion/jd_enrichment.py`
- Test: `backend/tests/test_jd_enrichment.py`

**Interfaces:**
- Consumes: `JobRepository.get_jobs(company=None, title=None, ..., tx=None)` (existing, `backend/src/core/repositories/job/repository.py:237`) via `RepositoryManager` (existing, `backend/src/core/repositories/manager.py`). **Confirmed by reading the source (not assumed):** called without `user_id`/`sort_by="score"`, `get_jobs` returns a **plain `list[dict]`** (each dict has a `description` key, among others) — not `{"jobs": [...]}`. Passing `user_id` would route through `get_jobs_from_precomputed` instead, a different return shape — this task deliberately never passes `user_id`, so that branch never triggers.
- Produces: `enrich(lead: JobLead, repos=None) -> JobLead` (mutates and returns a copy with `jd_excerpt` filled in if found; unchanged otherwise). `already_applied(lead: JobLead, user_id: str) -> bool` — dedup check against `ingested_job_leads`.

This task covers only fallback step 1 (internal DB match) plus the dedup table; steps 2 (form description) and 3 (web search) are wired in Task 8 (`GoogleFormsHandler`, which is the thing that actually opens the form) and Task 6 respectively, since they need capabilities this task doesn't have yet.

- [ ] **Step 1: Write the migration**

```sql
-- backend/src/database/migrations/041_ingested_job_leads.sql
CREATE TABLE IF NOT EXISTS ingested_job_leads (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    apply_link TEXT NOT NULL,
    source TEXT NOT NULL,
    source_ref TEXT,
    connector TEXT,
    jd_source TEXT,
    result_status TEXT,
    really_submitted INTEGER DEFAULT 0,
    execution_run_id TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ingested_job_leads_user_company_role
    ON ingested_job_leads (user_id, company, role);
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_jd_enrichment.py
from unittest.mock import MagicMock, patch
from src.ingestion.job_lead import JobLead
from src.ingestion.jd_enrichment import enrich, already_applied


def _lead(**overrides):
    base = dict(company="Acme", role="Backend Engineer", apply_link="https://forms.gle/abc123",
                location=None, jd_excerpt=None, source="screenshot", source_ref="/tmp/x.png")
    base.update(overrides)
    return JobLead(**base)


def test_enrich_fills_jd_from_internal_db_match():
    lead = _lead(jd_excerpt=None)
    mock_repos = MagicMock()
    mock_repos.job.get_jobs.return_value = [
        {"title": "Backend Engineer", "canonical_name": "Acme", "description": "We build widgets."}
    ]

    enriched = enrich(lead, repos=mock_repos)

    assert enriched.jd_excerpt == "We build widgets."
    mock_repos.job.get_jobs.assert_called_once()


def test_enrich_leaves_existing_jd_untouched():
    lead = _lead(jd_excerpt="Already have one.")
    mock_repos = MagicMock()

    enriched = enrich(lead, repos=mock_repos)

    assert enriched.jd_excerpt == "Already have one."
    mock_repos.job.get_jobs.assert_not_called()


def test_enrich_returns_lead_unchanged_when_no_db_match():
    lead = _lead(jd_excerpt=None)
    mock_repos = MagicMock()
    mock_repos.job.get_jobs.return_value = []

    enriched = enrich(lead, repos=mock_repos)

    assert enriched.jd_excerpt is None


@patch("src.ingestion.jd_enrichment.get_connection")
def test_already_applied_true_when_row_exists(mock_get_connection):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = {"id": "abc"}
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    assert already_applied(_lead(), user_id="user-1") is True


@patch("src.ingestion.jd_enrichment.get_connection")
def test_already_applied_false_when_no_row(mock_get_connection):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    assert already_applied(_lead(), user_id="user-1") is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_jd_enrichment.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ingestion.jd_enrichment'`

- [ ] **Step 4: Write minimal implementation**

```python
# backend/src/ingestion/jd_enrichment.py
import dataclasses
from typing import Optional

from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres
from src.ingestion.job_lead import JobLead

logger = setup_logger("jd_enrichment")


def enrich(lead: JobLead, repos=None) -> JobLead:
    """Step 1 only: internal DB match. Steps 2 (form description) and 3
    (web search) are applied later in the pipeline by callers that have
    the capabilities this function doesn't (see pipeline.py)."""
    if lead.jd_excerpt:
        return lead

    if repos is None:
        from src.core.repositories.manager import RepositoryManager
        repos = RepositoryManager()

    jobs = repos.job.get_jobs(company=lead.company, title=lead.role, page_size=1)
    if not jobs:
        return lead

    description = jobs[0].get("description")
    if not description:
        return lead

    return dataclasses.replace(lead, jd_excerpt=description)


def already_applied(lead: JobLead, user_id: str) -> bool:
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            SELECT id FROM ingested_job_leads
            WHERE user_id = {ph} AND company = {ph} AND role = {ph} AND really_submitted = 1
            """,
            (user_id, lead.company, lead.role),
        )
        return cur.fetchone() is not None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_jd_enrichment.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/src/database/migrations/041_ingested_job_leads.sql \
        backend/src/ingestion/jd_enrichment.py backend/tests/test_jd_enrichment.py
git commit -m "feat(ingestion): internal-DB JD enrichment + applied-lead dedup table"
```

---

### Task 6: `GoogleFormsSignature` + `endpoint_verification.py`

**Files:**
- Modify: `backend/src/discovery/ats_detector.py`
- Create: `backend/src/ingestion/endpoint_verification.py`
- Test: `backend/tests/test_routing.py` (covers `GoogleFormsSignature`)
- Test: `backend/tests/test_endpoint_verification.py`

**Interfaces:**
- Consumes: `ats_registry` table (existing, `backend/src/database/migrations/002_endpoint_verification.sql` — columns include `company_domain`, `ats_type`, `endpoint`, `status`, `last_verified`).
- Produces: `GoogleFormsSignature(ATSDetector)` with `provider_id = "google_forms"`. Produces: `is_endpoint_verified(company_domain: str, ats_type: str) -> bool` and `mark_endpoint_verified(company_domain: str, ats_type: str, endpoint: str) -> None`.

- [ ] **Step 1: Write the failing test — GoogleFormsSignature**

```python
# backend/tests/test_routing.py
from unittest.mock import MagicMock
from src.discovery.ats_detector import GoogleFormsSignature


def test_google_forms_signature_detects_forms_gle():
    detector = GoogleFormsSignature()
    response = MagicMock(status_code=200, text="")
    assert detector.detect("https://forms.gle/AbCdEf123", response) is True


def test_google_forms_signature_detects_docs_google_forms():
    detector = GoogleFormsSignature()
    response = MagicMock(status_code=200, text="")
    assert detector.detect("https://docs.google.com/forms/d/e/1FAIpQ/viewform", response) is True


def test_google_forms_signature_rejects_unrelated_url():
    detector = GoogleFormsSignature()
    response = MagicMock(status_code=200, text="")
    assert detector.detect("https://boards.greenhouse.io/acme/jobs/123", response) is False


def test_google_forms_signature_provider_id():
    assert GoogleFormsSignature().provider_id == "google_forms"
```

- [ ] **Step 2: Write the failing test — endpoint_verification**

```python
# backend/tests/test_endpoint_verification.py
from unittest.mock import MagicMock, patch
from src.ingestion.endpoint_verification import is_endpoint_verified, mark_endpoint_verified


@patch("src.ingestion.endpoint_verification.get_connection")
def test_is_endpoint_verified_true_when_status_verified(mock_get_connection):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = {"status": "VERIFIED"}
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    assert is_endpoint_verified("acme.com", "workday") is True


@patch("src.ingestion.endpoint_verification.get_connection")
def test_is_endpoint_verified_false_when_no_row(mock_get_connection):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    assert is_endpoint_verified("acme.com", "workday") is False


@patch("src.ingestion.endpoint_verification.get_connection")
def test_mark_endpoint_verified_upserts_row(mock_get_connection):
    mock_conn = MagicMock()
    mock_get_connection.return_value.__enter__.return_value = mock_conn

    mark_endpoint_verified("acme.com", "workday", "https://acme.wd1.myworkdayjobs.com/careers")

    assert mock_conn.execute.called
    assert mock_conn.commit.called
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_routing.py tests/test_endpoint_verification.py -v`
Expected: FAIL — `ImportError: cannot import name 'GoogleFormsSignature'` and `ModuleNotFoundError: No module named 'src.ingestion.endpoint_verification'`

- [ ] **Step 4: Add `GoogleFormsSignature` to `ats_detector.py`**

Add to `backend/src/discovery/ats_detector.py`, as a new class alongside the other `ATSDetector` subclasses, and register it in `DetectorRegistry._detectors`:

```python
class GoogleFormsSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'google_forms'

    def detect(self, url: str, response: Response) -> bool:
        return "forms.gle/" in url or "docs.google.com/forms/" in url

    def extract_canonical_url(self, url: str, response: Response) -> str:
        return url
```

And add `GoogleFormsSignature(),` to the `_detectors` list in `DetectorRegistry`.

- [ ] **Step 5: Write `endpoint_verification.py`**

```python
# backend/src/ingestion/endpoint_verification.py
import time
from typing import Optional

from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres

logger = setup_logger("endpoint_verification")


def is_endpoint_verified(company_domain: str, ats_type: str) -> bool:
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT status FROM ats_registry WHERE company_domain = {ph} AND ats_type = {ph}",
            (company_domain, ats_type),
        )
        row = cur.fetchone()
        if not row:
            return False
        status = row["status"] if hasattr(row, "keys") else row[0]
        return status == "VERIFIED"


def mark_endpoint_verified(company_domain: str, ats_type: str, endpoint: str) -> None:
    ph = "%s" if is_postgres() else "?"
    now = time.time()
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT id FROM ats_registry WHERE company_domain = {ph} AND ats_type = {ph}",
            (company_domain, ats_type),
        )
        existing = cur.fetchone()
        if existing:
            row_id = existing["id"] if hasattr(existing, "keys") else existing[0]
            conn.execute(
                f"UPDATE ats_registry SET status = {ph}, last_verified = {ph}, endpoint = {ph} WHERE id = {ph}",
                ("VERIFIED", now, endpoint, row_id),
            )
        else:
            conn.execute(
                f"""
                INSERT INTO ats_registry (company_domain, ats_type, endpoint, status, last_verified, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (company_domain, ats_type, endpoint, "VERIFIED", now, now),
            )
        conn.commit()
    logger.info(f"[endpoint_verification] marked {ats_type} endpoint verified for {company_domain}")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_routing.py tests/test_endpoint_verification.py -v`
Expected: PASS (7 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/src/discovery/ats_detector.py backend/src/ingestion/endpoint_verification.py \
        backend/tests/test_routing.py backend/tests/test_endpoint_verification.py
git commit -m "feat(discovery): Google Forms detection + ATS endpoint verification helpers"
```

---

### Task 7: `routing.py` — apply_link → connector key

**Files:**
- Create: `backend/src/ingestion/routing.py`
- Test: `backend/tests/test_routing.py` (extend the file created in Task 6)

**Interfaces:**
- Consumes: `DetectorRegistry.detect_all(url, response)` (existing), `is_endpoint_verified`/`mark_endpoint_verified` (Task 6).
- Produces: `resolve_connector(apply_link: str) -> tuple[str | None, str]` — returns `(connector_key, reason)`. `connector_key` is `None` when nothing matches (caller treats as `REVIEW_REQUIRED`); `reason` is a human-readable string always present, e.g. `"google_forms"`, `"workday (verified)"`, `"workday (newly verified)"`, `"unrecognized URL"`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_routing.py`:

```python
from unittest.mock import MagicMock, patch
from src.ingestion.routing import resolve_connector


@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_returns_google_forms_directly(mock_get):
    connector, reason = resolve_connector("https://forms.gle/AbCdEf123")
    assert connector == "google_forms"
    assert reason == "google_forms"
    mock_get.assert_not_called()  # no fetch needed for Google Forms — URL pattern is enough


@patch("src.ingestion.routing.is_endpoint_verified", return_value=True)
@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_returns_verified_known_ats(mock_get, mock_is_verified):
    mock_get.return_value = MagicMock(status_code=200, text="grnhse.com", url="https://boards.greenhouse.io/acme")
    connector, reason = resolve_connector("https://boards.greenhouse.io/acme/jobs/1")
    assert connector == "greenhouse"
    assert "verified" in reason


@patch("src.ingestion.routing.mark_endpoint_verified")
@patch("src.ingestion.routing.is_endpoint_verified", return_value=False)
@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_verifies_unverified_known_ats(mock_get, mock_is_verified, mock_mark):
    mock_get.return_value = MagicMock(status_code=200, text="grnhse.com", url="https://boards.greenhouse.io/acme")
    connector, reason = resolve_connector("https://boards.greenhouse.io/acme/jobs/1")
    assert connector == "greenhouse"
    assert "newly verified" in reason
    mock_mark.assert_called_once()


@patch("src.ingestion.routing.httpx.get")
def test_resolve_connector_returns_none_for_unrecognized_url(mock_get):
    mock_get.return_value = MagicMock(status_code=200, text="nothing recognizable here", url="https://example.com/apply")
    connector, reason = resolve_connector("https://example.com/apply")
    assert connector is None
    assert reason == "unrecognized URL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_routing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ingestion.routing'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/ingestion/routing.py
import httpx
from urllib.parse import urlparse
from typing import Optional, Tuple

from src.system.logger import setup_logger
from src.discovery.ats_detector import DetectorRegistry, GoogleFormsSignature
from src.ingestion.endpoint_verification import is_endpoint_verified, mark_endpoint_verified

logger = setup_logger("routing")

_google_forms = GoogleFormsSignature()


def resolve_connector(apply_link: str) -> Tuple[Optional[str], str]:
    if "forms.gle/" in apply_link or "docs.google.com/forms/" in apply_link:
        return "google_forms", "google_forms"

    try:
        response = httpx.get(apply_link, timeout=10.0, follow_redirects=True)
    except Exception as e:
        logger.info(f"[routing] failed to fetch {apply_link}: {e}")
        return None, "fetch failed"

    detector = DetectorRegistry.detect_all(apply_link, response)
    if not detector:
        return None, "unrecognized URL"

    company_domain = urlparse(apply_link).netloc
    connector = detector.provider_id

    if is_endpoint_verified(company_domain, connector):
        return connector, f"{connector} (verified)"

    mark_endpoint_verified(company_domain, connector, apply_link)
    return connector, f"{connector} (newly verified)"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_routing.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/ingestion/routing.py backend/tests/test_routing.py
git commit -m "feat(ingestion): route an apply link to a connector, verifying unverified ATS endpoints"
```

---

### Task 8: `GoogleFormsHandler` + `GoogleFormsAdapter`

This is the largest task. `GoogleFormsHandler` implements every `BaseATSHandler` abstract method, using `LeverHandler` (`backend/src/applications/handlers/lever.py`) as the structural template per the research, but replacing the single-page fill with a multi-page loop, and reading the form's own description text as JD-enrichment fallback step 2 (per spec §2/§C).

**Files:**
- Create: `backend/src/applications/handlers/google_forms.py`
- Create: `backend/src/applications/adapters/google_forms_adapter.py`
- Test: `backend/tests/test_google_forms_handler.py`

**Interfaces:**
- Consumes: `BaseATSHandler.__init__` (existing, exact signature in Research item 1), `QuestionEngine.answer(...)` (existing, constructed for you by `BaseATSHandler.__init__` as `self.engine`), `BaseAdapter.apply(...)` (existing ABC), `ApplicationResult` (existing), `LaunchedBrowser` (existing).
- Produces: `GoogleFormsHandler(BaseATSHandler)` with `ATS_NAME = "GOOGLE_FORMS"`, and `read_form_description(self) -> str | None` (new method beyond the base class, used by the pipeline for JD-enrichment fallback step 2). `GoogleFormsAdapter(BaseAdapter)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_google_forms_handler.py
from unittest.mock import MagicMock, PropertyMock
from src.applications.handlers.google_forms import GoogleFormsHandler


def _make_page_with_questions(question_htmls_per_page):
    """Builds a MagicMock Playwright Page that returns a different set of
    question-item locators on each successive call to
    page.locator('div[role="listitem"]') — simulating one Google Forms
    section per call, advanced by clicking Next."""
    page = MagicMock()
    call_state = {"page_index": 0}

    def locator_side_effect(selector):
        loc = MagicMock()
        if selector == 'div[role="listitem"]':
            items = question_htmls_per_page[call_state["page_index"]]
            loc.all.return_value = items
        return loc

    page.locator.side_effect = locator_side_effect
    return page, call_state


def test_read_form_description_returns_text_when_present():
    page = MagicMock()
    page.locator.return_value.first.text_content.return_value = "We are hiring a Backend Engineer to build widgets."
    handler = GoogleFormsHandler(
        page=page, job_title="Backend Engineer", company_name="Acme", location="Remote",
        resume_path="/tmp/resume.pdf", test_mode=True, execution_dir="/tmp/exec",
        profile_manager=MagicMock(), rag_client=MagicMock(), llm_client=MagicMock(),
    )

    description = handler.read_form_description()

    assert description == "We are hiring a Backend Engineer to build widgets."


def test_get_submit_button_locator_finds_submit_span():
    page = MagicMock()
    handler = GoogleFormsHandler(
        page=page, job_title="Backend Engineer", company_name="Acme", location="Remote",
        resume_path="/tmp/resume.pdf", test_mode=True, execution_dir="/tmp/exec",
        profile_manager=MagicMock(), rag_client=MagicMock(), llm_client=MagicMock(),
    )

    handler._get_submit_button_locator()

    page.get_by_role.assert_called_with("button", name="Submit")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_google_forms_handler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.applications.handlers.google_forms'`

- [ ] **Step 3: Write `google_forms.py`**

```python
# backend/src/applications/handlers/google_forms.py
from src.applications.handlers.base_handler import BaseATSHandler
from src.system.logger import setup_logger

logger = setup_logger("google_forms_handler")

# Google Forms' own DOM roles for each question widget type, mapped onto
# the widget_type vocabulary _interact_widget() (base_handler.py) already
# understands.
_WIDGET_TYPE_BY_ROLE = {
    "radio": "radio_group",
    "checkbox": "checkbox_group",
    "listbox": "native_select",
}


class GoogleFormsHandler(BaseATSHandler):
    ATS_NAME = "GOOGLE_FORMS"

    def _enter_application_flow(self):
        # Google Forms links go directly to the form -- there's no separate
        # "Apply" button/landing page to click through, unlike ATS postings.
        pass

    def _detect_and_set_iframe(self):
        # Google Forms are never embedded in an iframe from the applicant's
        # perspective -- self.page already is the form.
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        # Google Forms have no ATS-standard name/email/phone fields --
        # anything like that is just an ordinary form item, handled by the
        # generic _extract_questions()/_interact_widget() cycle instead.
        return True

    def _upload_resume(self) -> bool:
        # Only present if the form owner explicitly added a native file-
        # upload item; that item will show up in _extract_questions() as an
        # ordinary (if currently unhandled) widget_type, so there's nothing
        # to do at this fixed pipeline stage.
        return True

    def read_form_description(self):
        """JD-enrichment fallback step 2 (spec §2/§C) -- read once while the
        handler already has the form open, at zero extra API cost."""
        try:
            text = self.active_context.locator('div[role="heading"]').first.text_content()
            return text.strip() if text else None
        except Exception as e:
            logger.info(f"[GoogleFormsHandler] could not read form description: {e}")
            return None

    def _extract_questions(self) -> list:
        """Extracts questions for the CURRENT page/section only -- Google
        Forms sections are separate DOM subtrees that only exist once
        you've navigated to them via _advance_to_next_page()."""
        questions = []
        items = self.active_context.locator('div[role="listitem"]').all()
        for item in items:
            label_el = item.locator('div[role="heading"]').first
            raw_label = label_el.text_content() or ""
            is_required = "*" in raw_label
            clean_label = raw_label.replace("*", "").strip()

            widget_type = "input"
            options = []
            for role, mapped in _WIDGET_TYPE_BY_ROLE.items():
                role_items = item.get_by_role(role).all()
                if role_items:
                    widget_type = mapped
                    options = [el.get_attribute("aria-label") or el.text_content() or "" for el in role_items]
                    break
            else:
                if item.locator("textarea").count() > 0:
                    widget_type = "textarea"

            questions.append({
                "container": item,
                "question": clean_label,
                "raw_label": raw_label,
                "is_required": is_required,
                "widget_type": widget_type,
                "options": options,
                "placeholder": "",
            })
        return questions

    def _advance_to_next_page(self) -> bool:
        """Clicks Google Forms' "Next" button if this section has one.
        Returns False when there's no Next button left (i.e. this was the
        final section, with only Submit remaining)."""
        next_button = self.active_context.get_by_role("button", name="Next")
        if next_button.count() == 0:
            return False
        next_button.first.click()
        self.active_context.wait_for_timeout(500)
        return True

    def _get_submit_button_locator(self):
        return self.active_context.get_by_role("button", name="Submit")
```

- [ ] **Step 4: Write `google_forms_adapter.py`**

```python
# backend/src/applications/adapters/google_forms_adapter.py
from typing import Any, Dict

from src.applications.adapters.base_adapter import BaseAdapter, ApplicationResult, derive_diagnosis
from src.applications.browser_launcher import LaunchedBrowser
from src.applications.handlers.google_forms import GoogleFormsHandler
from src.system.logger import setup_logger

logger = setup_logger("google_forms_adapter")


class GoogleFormsAdapter(BaseAdapter):
    def __init__(self, profile_manager=None, rag_client=None, llm_router=None):
        self.profile_manager = profile_manager
        self.rag_client = rag_client
        self.llm_router = llm_router

    def apply(self, job: Dict[str, Any], resume_path: str, profile_manager: Any, test_mode: bool = False, user_id: str = None) -> ApplicationResult:
        with LaunchedBrowser() as lb:
            page = lb.page
            page.goto(job["apply_url"], timeout=30000)

            handler = GoogleFormsHandler(
                page=page,
                job_title=job.get("job_title", ""),
                company_name=job.get("company_name", ""),
                location=job.get("location", ""),
                resume_path=resume_path,
                test_mode=test_mode,
                execution_dir=job.get("execution_dir", ""),
                profile_manager=profile_manager or self.profile_manager,
                rag_client=self.rag_client,
                llm_client=self.llm_router,
                company_context=job.get("company_context", ""),
                user_id=user_id,
                job_id=job.get("id"),
            )

            outcome = handler.execute()
            telemetry = outcome.get("telemetry", {})

            return ApplicationResult(
                status=outcome.get("status", "FAILED"),
                confirmation_url=telemetry.get("submission_proof", {}).get("confirmation_url", ""),
                screenshot_path=telemetry.get("submission_proof", {}).get("screenshot_path", ""),
                submitted_answers=telemetry.get("filled_fields", {}),
                failure_reason=derive_diagnosis(telemetry),
                really_submitted=telemetry.get("submission_proof", {}).get("really_submitted", False),
            )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_google_forms_handler.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Register in the dispatcher**

Modify `backend/src/applications/dispatcher.py` — add one entry to `_ADAPTER_REGISTRY`:

```python
    "google_forms": ("src.applications.adapters.google_forms_adapter", "GoogleFormsAdapter"),
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/applications/handlers/google_forms.py \
        backend/src/applications/adapters/google_forms_adapter.py \
        backend/src/applications/dispatcher.py \
        backend/tests/test_google_forms_handler.py
git commit -m "feat(applications): add GoogleFormsHandler/Adapter with multi-page fill support"
```

**Note for the implementer:** `execute()`'s cycle in `base_handler.py` calls `_process_custom_fields()` once per iteration, which calls `_extract_questions()` once — it does not natively loop across "pages" the way this handler needs. Before this task is considered done, re-read `execute()` (`base_handler.py:701-917`) against this handler's `_advance_to_next_page()` and confirm where the page-advance call needs to be inserted (most likely: override the loop by having `_extract_questions()` itself call `_advance_to_next_page()` when the current page returns zero unanswered questions and a page has already been processed — track this with an instance flag, e.g. `self._page_index`, initialized in `__init__` — rather than modifying the shared `execute()` state machine, to avoid touching code every other handler also depends on). Write an additional test asserting `_extract_questions()` is called once per section across a 2-page form fixture before marking this task complete.

---

### Task 9: Web search fallback (JD enrichment step 3) in `jd_enrichment.py`

**Files:**
- Modify: `backend/src/ingestion/jd_enrichment.py`
- Modify: `backend/tests/test_jd_enrichment.py`

**Interfaces:**
- Consumes: `src.discovery.providers.search_engine_provider.YahooBackend.search(query: str) -> list[str]` (existing, async).
- Produces: `enrich_with_web_search(lead: JobLead) -> JobLead` — called by the pipeline (Task 10) only when both DB match (this task's `enrich`) and the form's own description (`GoogleFormsHandler.read_form_description`, Task 8) came up empty, per spec §2's ordering.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_jd_enrichment.py`:

```python
from unittest.mock import AsyncMock, patch
from src.ingestion.jd_enrichment import enrich_with_web_search


@patch("src.ingestion.jd_enrichment.YahooBackend")
def test_enrich_with_web_search_fills_jd_from_first_result(mock_backend_cls):
    mock_backend = mock_backend_cls.return_value
    mock_backend.search = AsyncMock(return_value=["https://acme.com/careers/backend-engineer"])

    lead = _lead(jd_excerpt=None)
    enriched = enrich_with_web_search(lead)

    assert enriched.apply_link == lead.apply_link  # unchanged
    mock_backend.search.assert_called_once_with("Acme Backend Engineer job description")


@patch("src.ingestion.jd_enrichment.YahooBackend")
def test_enrich_with_web_search_leaves_lead_unchanged_on_no_results(mock_backend_cls):
    mock_backend = mock_backend_cls.return_value
    mock_backend.search = AsyncMock(return_value=[])

    lead = _lead(jd_excerpt=None)
    enriched = enrich_with_web_search(lead)

    assert enriched.jd_excerpt is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_jd_enrichment.py -v`
Expected: FAIL with `ImportError: cannot import name 'enrich_with_web_search'`

- [ ] **Step 3: Write minimal implementation**

Add to `backend/src/ingestion/jd_enrichment.py`:

```python
import asyncio
from src.discovery.providers.search_engine_provider import YahooBackend


def enrich_with_web_search(lead: JobLead) -> JobLead:
    """Last-resort JD enrichment (spec §2 step 3) -- only called by the
    pipeline after both the internal DB match and the Google Form's own
    description text have come up empty, to minimize paid/rate-limited
    search calls."""
    if lead.jd_excerpt:
        return lead

    backend = YahooBackend()
    query = f"{lead.company} {lead.role} job description"
    try:
        urls = asyncio.run(backend.search(query))
    except Exception as e:
        logger.info(f"[jd_enrichment] web search failed for {query}: {e}")
        return lead

    if not urls:
        return lead

    # Storing the found URL as the excerpt seed is deliberately conservative
    # here -- fetching and extracting full page text is Task 8/10's
    # GoogleFormsHandler's territory (it already has an HTTP-capable
    # Playwright context); this function's job is only to decide whether a
    # plausible JD source exists at all, not to scrape it.
    return dataclasses.replace(lead, jd_excerpt=f"(found via web search: {urls[0]})")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_jd_enrichment.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/ingestion/jd_enrichment.py backend/tests/test_jd_enrichment.py
git commit -m "feat(ingestion): web-search JD enrichment fallback (last resort)"
```

---

### Task 10: `pipeline.py` orchestrator + `run_google_forms_batch.py` CLI

**Files:**
- Create: `backend/src/ingestion/pipeline.py`
- Create: `backend/scripts/run_google_forms_batch.py`
- Test: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `jd_enrichment.enrich`/`enrich_with_web_search`/`already_applied` (Tasks 5, 9), `routing.resolve_connector` (Task 7), `apply_to_job` (existing, `backend/src/applications/apply_service.py`), `screenshot_extractor.extract_from_image` (Task 3), `email_extractor.scan_job_alerts` (Task 4).
- Produces: `run_lead(lead: JobLead, user_id: str, test_mode: bool = True) -> dict` — returns the same `result.json`-shaped dict the rest of the system already writes to `backend/executions/<run_id>/`, extended with `job_lead` and `jd_source` fields per spec §6. Writes that dict to `backend/executions/<run_id>/result.json` as a side effect.

**Pre-flight correction (found during plan review, before this task was dispatched):** `apply_to_job()`'s `_map_job_row()` (`backend/src/applications/apply_service.py:23-32`, existing code) translates an incoming `job_row` into a **new dict containing only 6 fixed keys** — `id` (read from `job_row["job_id"]`, not `job_row["id"]`), `job_title`, `company_name`, `connector`, `location`, `apply_url` — before handing it to the dispatcher. Any other key on `job_row` (e.g. `execution_dir`, `description`) is silently dropped, and building `job_row` with a key literally named `"id"` (as an earlier draft of this task did) means `_map_job_row` reads a nonexistent `job_row["job_id"]` and the adapter receives `id=None`. Step 3 below builds `job_row` with the exact keys `_map_job_row` reads, and Step 3a extends `_map_job_row` itself (additively — the 6 existing keys are untouched, so no other adapter's behavior changes) so `GoogleFormsAdapter` (Task 8) actually receives `execution_dir` and `description`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_pipeline.py
from unittest.mock import MagicMock, patch
from src.ingestion.job_lead import JobLead
from src.ingestion.pipeline import run_lead


def _lead():
    return JobLead(company="Acme", role="Backend Engineer", apply_link="https://forms.gle/abc123",
                    location="Remote", jd_excerpt=None, source="screenshot", source_ref="/tmp/x.png")


@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich_with_web_search", side_effect=lambda lead: lead)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=("google_forms", "google_forms"))
@patch("src.ingestion.pipeline.apply_to_job")
def test_run_lead_calls_apply_to_job_with_mapped_job_row(mock_apply, mock_resolve, mock_enrich, mock_web, mock_dup):
    mock_result = MagicMock(status="COMPLETED", really_submitted=False, confirmation_url="",
                             screenshot_path="", submitted_answers={}, failure_reason="")
    mock_apply.return_value = mock_result

    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)

    called_job_row = mock_apply.call_args.args[0]
    assert called_job_row["title"] == "Backend Engineer"
    assert called_job_row["canonical_name"] == "Acme"
    assert called_job_row["provider"] == "google_forms"
    assert called_job_row["apply_url"] == "https://forms.gle/abc123"
    assert called_job_row["job_id"]  # non-empty — _map_job_row reads "job_id", not "id"
    assert outcome["status"] == "COMPLETED"
    assert outcome["job_lead"]["company"] == "Acme"


@patch("src.ingestion.pipeline.already_applied", return_value=True)
def test_run_lead_skips_when_already_applied(mock_dup):
    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)
    assert outcome["status"] == "SKIPPED_DUPLICATE"


@patch("src.ingestion.pipeline.already_applied", return_value=False)
@patch("src.ingestion.pipeline.enrich", side_effect=lambda lead, repos=None: lead)
@patch("src.ingestion.pipeline.resolve_connector", return_value=(None, "unrecognized URL"))
def test_run_lead_returns_review_required_when_connector_unresolved(mock_resolve, mock_enrich, mock_dup):
    outcome = run_lead(_lead(), user_id="user-1", test_mode=True)
    assert outcome["status"] == "REVIEW_REQUIRED"
    assert "unrecognized URL" in outcome["failure_reason"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ingestion.pipeline'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/ingestion/pipeline.py
import json
import os
import time
import uuid
import dataclasses

from src.system.logger import setup_logger
from src.ingestion.job_lead import JobLead
from src.ingestion.jd_enrichment import enrich, enrich_with_web_search, already_applied
from src.ingestion.routing import resolve_connector
from src.applications.apply_service import apply_to_job

logger = setup_logger("ingestion_pipeline")

EXECUTIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "executions")


def run_lead(lead: JobLead, user_id: str, test_mode: bool = True) -> dict:
    run_id = f"leads_{lead.source}_{uuid.uuid4().hex[:8]}"

    if already_applied(lead, user_id=user_id):
        logger.info(f"[pipeline] skipping duplicate lead: {lead.company} / {lead.role}")
        return {"run_id": run_id, "status": "SKIPPED_DUPLICATE", "job_lead": dataclasses.asdict(lead)}

    lead = enrich(lead)
    jd_source = "db_match" if lead.jd_excerpt else "none"

    connector, reason = resolve_connector(lead.apply_link)
    if not connector:
        logger.info(f"[pipeline] could not route {lead.apply_link}: {reason}")
        return {
            "run_id": run_id, "status": "REVIEW_REQUIRED",
            "failure_reason": f"Could not route apply link: {reason}",
            "job_lead": dataclasses.asdict(lead), "jd_source": jd_source,
        }

    if not lead.jd_excerpt and connector != "google_forms":
        # Only google_forms gets the form-description fallback (Task 8's
        # GoogleFormsHandler.read_form_description, called from inside
        # GoogleFormsAdapter.apply() -- not reachable from here without
        # opening a browser session redundantly), so any other connector
        # goes straight to the web-search fallback.
        lead = enrich_with_web_search(lead)
        if lead.jd_excerpt:
            jd_source = "web_search"

    job_row = {
        "job_id": str(uuid.uuid4()),
        "title": lead.role,
        "canonical_name": lead.company,
        "provider": connector,
        "location": lead.location or "",
        "apply_url": lead.apply_link,
        "execution_dir": os.path.join(EXECUTIONS_DIR, run_id),
        "description": lead.jd_excerpt or "",
    }

    result = apply_to_job(job_row, test_mode=test_mode, user_id=user_id)

    outcome = {
        "run_id": run_id,
        "started_at": time.time(),
        "company": lead.company,
        "title": lead.role,
        "connector": connector,
        "test_mode": test_mode,
        "status": result.status,
        "really_submitted": result.really_submitted,
        "confirmation_url": result.confirmation_url,
        "screenshot_path": result.screenshot_path,
        "submitted_answers": result.submitted_answers,
        "failure_reason": result.failure_reason,
        "job_lead": dataclasses.asdict(lead),
        "jd_source": jd_source,
    }

    os.makedirs(job_row["execution_dir"], exist_ok=True)
    with open(os.path.join(job_row["execution_dir"], "result.json"), "w") as f:
        json.dump(outcome, f, indent=2, default=str)

    return outcome
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: PASS (3 passed)

- [ ] **Step 4a: Extend `_map_job_row` so `execution_dir`/`description` survive into the adapter**

Modify `backend/src/applications/apply_service.py` — add two keys to the dict `_map_job_row` returns (the 6 existing keys are unchanged, so this is additive and safe for the other 15 adapters, which simply won't set these two on their own `job_row`s):

```python
def _map_job_row(job_row: Dict[str, Any]) -> Dict[str, Any]:
    """`repos.job.get_job()` returns `job_id`/`title`/`provider`/
    `canonical_name`; the dispatcher/adapters expect `id`/`job_title`/
    `connector`/`company_name`. Translate field names only — no new data.
    `execution_dir`/`description` pass through unchanged when present (used
    by GoogleFormsAdapter; no other adapter sets them today)."""
    return {
        "id": job_row.get("job_id"),
        "job_title": job_row.get("title", ""),
        "company_name": job_row.get("canonical_name", ""),
        "connector": (job_row.get("provider") or "").lower().strip(),
        "location": job_row.get("location", ""),
        "apply_url": job_row.get("apply_url", ""),
        "execution_dir": job_row.get("execution_dir", ""),
        "description": job_row.get("description", ""),
    }
```

Add a test to `backend/tests/test_pipeline.py` covering this directly (it's `apply_service.py`'s function, not `pipeline.py`'s, but belongs with the rest of this task's verification since nothing else in the plan exercises it):

```python
def test_map_job_row_passes_through_execution_dir_and_description():
    from src.applications.apply_service import _map_job_row

    mapped = _map_job_row({
        "job_id": "abc-123", "title": "Backend Engineer", "canonical_name": "Acme",
        "provider": "google_forms", "location": "Remote", "apply_url": "https://forms.gle/abc123",
        "execution_dir": "/tmp/exec/run-1", "description": "We build widgets.",
    })

    assert mapped["id"] == "abc-123"
    assert mapped["execution_dir"] == "/tmp/exec/run-1"
    assert mapped["description"] == "We build widgets."
```

Run: `cd backend && python -m pytest tests/test_pipeline.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Write the CLI script**

```python
# backend/scripts/run_google_forms_batch.py
"""
Point at a folder of job-post screenshots; runs each through the ingestion
pipeline in dry-run mode by default. This is the no-frontend entry point for
phase 1 (see docs/superpowers/specs/2026-08-18-google-forms-apply-pipeline-design.md) --
the user hands over a folder path and reviews backend/executions/<run_id>/
afterward.

Usage:
    python scripts/run_google_forms_batch.py --folder /path/to/screenshots --user-id <uuid> [--live]
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ingestion.screenshot_extractor import extract_from_image
from src.ingestion.pipeline import run_lead

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True, help="Folder of screenshots to process")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--live", action="store_true", help="Submit for real (default: dry-run)")
    args = parser.parse_args()

    paths = [p for ext in IMAGE_EXTENSIONS for p in glob.glob(os.path.join(args.folder, f"*{ext}"))]
    print(f"Found {len(paths)} images in {args.folder}")

    for path in paths:
        lead = extract_from_image(path)
        if lead is None:
            print(f"SKIP  {path}: extraction failed or low-confidence")
            continue

        outcome = run_lead(lead, user_id=args.user_id, test_mode=not args.live)
        print(f"{outcome['status']:<20} {lead.company} / {lead.role}  -> {outcome.get('run_id')}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/ingestion/pipeline.py backend/src/applications/apply_service.py \
        backend/scripts/run_google_forms_batch.py backend/tests/test_pipeline.py
git commit -m "feat(ingestion): pipeline orchestrator + CLI to batch-run screenshots"
```

---

## Self-Review Notes

- **Spec coverage:** §A (pipeline overview) → Task 10. §B (ingestion layer, both sources) → Tasks 3, 4. §C (JD enrichment 3-step) → Tasks 5, 8 (`read_form_description`), 9. §D (Google Forms handler + multi-page) → Task 8. §E (dry-run default, live after review) → Task 10 (`test_mode` param defaults `True` throughout the call chain; CLI requires explicit `--live`). §F (audit trail) → Task 10 (`result.json` written to `executions/<run_id>/`). §G (endpoint verification) → Tasks 6, 7.
- **Known follow-up, flagged inline rather than hidden:** Task 8 calls out explicitly that `_advance_to_next_page()`'s integration point into `execute()`'s existing loop needs to be nailed down by the implementer against the real `execute()` control flow before the task is done — this is real uncertainty (the multi-page mechanism is genuinely new relative to every existing handler) rather than a placeholder, and the task includes a concrete instruction for resolving it plus an explicit test to add.
- **Not covered by this plan (explicitly out of scope per spec):** frontend/UI, scheduled/automatic Gmail polling (CLI/on-demand only), Google Workspace sign-in-gated forms.
