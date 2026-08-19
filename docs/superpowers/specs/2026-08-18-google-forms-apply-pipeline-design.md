# Google Forms Apply Pipeline — Design

**Status:** Approved for implementation
**Date:** 2026-08-18

## Problem

Some job postings (especially social/job-board posts) route applicants to a
Google Form instead of a real ATS. Today the auto-apply system
(`backend/src/applications/`) only knows how to fill known ATS platforms —
there's no way to go from "a screenshot of a job post" or "a job-alert email"
to a filled-out application at all, let alone a multi-page Google Form.

## Goals

1. Accept a screenshot of a social/job-board post as input; extract company,
   role, and apply link from it.
2. Accept Gmail job-alert emails as a second input source (no screenshot
   needed) — read directly via the existing IMAP integration.
3. When the extracted/apply-linked job has no JD attached, source one while
   minimizing paid API calls: check internal DB first, then the destination
   page itself, then web search as a last resort.
4. Route the apply link to the correct handler: existing verified ATS
   adapter, a newly-verified ATS adapter, or a new Google Forms handler.
5. Fill multi-page Google Forms end to end, reusing the existing
   question-answering and audit infrastructure.
6. No frontend in this phase — backend/pipeline only. User will supply
   screenshots via a folder (path TBD, told separately) for the first batch.

## Non-goals (this phase)

- No frontend UI for uploading images or reviewing runs.
- No handling of Google Forms that require signing in with a restricted
  Google Workspace account (treated as `REVIEW_REQUIRED`, same as any
  ATS handler hitting an unsupported gate today).
- No changes to the existing ATS adapters/handlers themselves.

## Architecture

```
[Screenshot folder]  ──┐
                        ├─▶ Extraction ─▶ JobLead{company, role, apply_link, jd_excerpt?, source}
[Gmail job-alert scan]─┘
                                              │
                                              ▼
                        JD enrichment: internal DB match → (if google_forms) form's own
                        description text → web search (last resort)
                                              │
                                              ▼
                        Routing: extend discovery's ATSDetector registry with
                        GoogleFormsSignature; look up job["connector"] in
                        ApplicationDispatcher._ADAPTER_REGISTRY
                                              │
                ┌─────────────────────────────┼─────────────────────────────┐
                ▼                             ▼                             ▼
     Verified known ATS              Recognized-but-unverified ATS    Google Forms
     → existing adapter               → verify endpoint once,          → new GoogleFormsHandler
       (unchanged)                      register, then existing adapter  + multi-page fill loop
```

### 1. Ingestion layer — `backend/src/ingestion/`

New package, two entry points feeding one shared `JobLead` shape:

```python
@dataclass
class JobLead:
    company: str
    role: str
    apply_link: str
    location: str | None
    jd_excerpt: str | None
    source: Literal["screenshot", "email"]
    source_ref: str  # file path or Gmail message id, for audit trail
```

- **`screenshot_extractor.py`** — `extract_from_image(path: str) -> JobLead`.
  One vision LLM call (via the existing `LLMRouter`, same router
  `apply_service.py` already constructs) with a strict JSON-schema prompt:
  `{company, role, apply_link, location, jd_excerpt, confidence}`. Low
  confidence or missing `apply_link`/`company`/`role` → skip with a logged
  reason rather than guessing.

- **`email_extractor.py`** — `scan_job_alerts(since_days: int = 3) -> list[JobLead]`.
  Extends `backend/src/integrations/email_listener.py`'s `EmailListener`
  (already does read-only IMAP against `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD` —
  this is the "google smtp" access referenced; it's actually IMAP, already
  wired for OTP retrieval). Add a method:
  `search_job_alerts(sender_allowlist: list[str], since_days: int) -> list[EmailMessage]`
  reusing `_connect()`, filtering `FROM` against a small known-sender list
  (LinkedIn Jobs, Indeed, Glassdoor, etc. — configurable list, not hardcoded
  in the method). Each matching message is parsed (regex/plain text, no
  vision call needed) into one or more `JobLead`s. A small persisted set of
  processed message IDs (new table `processed_job_alert_emails(message_id,
  processed_at)`, or a flat file if a table is overkill for phase 1) avoids
  reprocessing on repeated scans. Triggered on-demand (a script/CLI entry
  point in this phase — no scheduler, no frontend button yet).

### 2. JD enrichment — `backend/src/ingestion/jd_enrichment.py`

`enrich(lead: JobLead) -> JobLead`, in this order, stopping at the first hit:

1. Fuzzy match `company` + `role` against the existing `jobs` table
   (cheap, no external call). This doubles as a dedup check — if the job is
   already marked applied, the pipeline logs and skips it rather than
   re-applying.
2. If still missing and the apply link resolves to `google_forms`: the
   `GoogleFormsHandler` reads the form's own description text when it opens
   the page anyway (zero extra calls) and reports it back.
3. Only if still missing: one web search call, last resort.

### 3. Routing — extends existing discovery + dispatch, no new mechanism

- `backend/src/discovery/ats_detector.py`: new `GoogleFormsSignature(ATSDetector)`
  — `provider_id = "google_forms"`, URL-pattern match on
  `docs.google.com/forms/` / `forms.gle/`, registered in
  `DetectorRegistry._detectors`.
- **New: endpoint verification for recognized-but-unverified ATS.** When
  `ATSDetector` matches a known ATS pattern (e.g. a Workday tenant) that
  isn't yet marked verified in the discovery registry (the same "verified
  real hit rate" concept from commit `40f913d`), the pipeline runs a
  one-time verification call — confirms the endpoint returns a real
  job/JD, not a soft-404 — before handing off. Success marks that tenant
  verified (so future jobs from it skip the check); failure falls back to
  `REVIEW_REQUIRED`, same as an ATS with no adapter at all today. This
  makes routing three-way: verified ATS → existing adapter; recognized but
  unverified ATS → verify then adapter; Google Forms → new handler.
- `ApplicationDispatcher._ADAPTER_REGISTRY` gets one new entry:
  `"google_forms": ("src.applications.adapters.google_forms_adapter", "GoogleFormsAdapter")`.
  No change to `dispatch()` itself.

### 4. Google Forms handler

- `backend/src/applications/handlers/google_forms.py` — new
  `BaseATSHandler` subclass. Differs structurally from ATS handlers:
  no iframe, no distinct standard-fields step (name/email/phone are
  ordinary form items, if present at all), no resume-upload widget unless
  the form owner explicitly added a native file-upload item. Reuses the
  base class's generic widget interaction (`input`/`textarea`/
  `radio_group`/`checkbox_group`, plus a dropdown variant for Google's
  native dropdown widget) and `QuestionEngine`/`RAGClient` for answers,
  fed by the enriched `JobLead` (company/role/JD).
- **New behavior: multi-page loop.** Google Forms sections advance via a
  "Next" button with client-side validation. The handler extracts one
  page's questions at a time (extending `_extract_questions()` to be
  page-scoped rather than whole-document), answers/fills them, clicks
  Next, checks for validation errors (Google surfaces these inline — if
  present, re-answer the flagged field with an escalation-aware retry
  rather than looping forever), and repeats until it reaches the final
  page with the real Submit button.
- `backend/src/applications/adapters/google_forms_adapter.py` — thin
  `BaseAdapter.apply()` implementation, same shape as the other 16.

### 5. Submission safety

Per your explicit instruction: the first batch of forms you hand me runs in
**dry-run** (`test_mode=True`, the existing convention — fills every page,
screenshots each one, stops before the real Submit click,
`really_submitted=False`) so you can review the results. Once you're
satisfied, the default for this connector flips to **live**
(`test_mode=False`) for everything after — still honoring the existing
low-confidence-on-required-field escalation (`REVIEW_REQUIRED`, no guessing)
regardless of dry-run/live.

### 6. Audit trail

Same `backend/executions/<run_id>/` convention as every other connector:
numbered screenshots per page, `final_dom.html`, `result.json`. `result.json`
gains two new fields beyond the existing shape: the source `JobLead`
(including `source`/`source_ref` for traceability back to the screenshot or
email) and which JD-enrichment step produced the JD (`db_match` /
`form_description` / `web_search` / `none`).

## Data flow summary

```
JobLead (screenshot or email)
  → enrich() [DB → form description → web search]
  → route() [ATSDetector + verification]
  → dispatch() [existing ApplicationDispatcher, +1 registry entry]
  → BaseATSHandler.execute() [existing state machine; GoogleFormsHandler
    overrides the DOM-specific primitives + adds the page loop]
  → ApplicationResult + executions/<run_id>/ audit trail
```

## Testing

- Unit tests for `screenshot_extractor` (mocked vision call → JobLead
  parsing) and `email_extractor` (mocked IMAP fetch → JobLead parsing,
  dedup-by-message-id).
- Unit tests for `jd_enrichment`'s three-step fallback ordering.
- Integration test for `GoogleFormsSignature` detection against a real
  `forms.gle`/`docs.google.com/forms` URL shape.
- `GoogleFormsHandler` tested against the real screenshots/forms you
  provide, in dry-run, per your instruction — not synthetic fixtures only,
  since Google Forms layout varies enough that a hand-built fixture risks
  testing the wrong thing.
