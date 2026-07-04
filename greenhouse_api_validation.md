# Greenhouse API Validation Report
**Endpoint Tested**: `https://boards-api.greenhouse.io/v1/boards/anthropic/jobs/5183044008`
**HTTP Status**: `200`
**Latency**: `402.04 ms`

## Response Schema Analysis
- **Top-level fields returned**: absolute_url, data_compliance, internal_job_id, location, metadata, id, updated_at, requisition_id, title, company_name, first_published, language, application_deadline, content, departments, offices

### Critical Metadata Check
- **Title**: ✅ Present
- **Location**: ✅ Present
- **Department**: ✅ Present
- **Updated Date**: ✅ Present
- **Job Description (content)**: ✅ Present

### Missing Fields
*(None of the critical routing fields are missing)*

### Auth & Rate Limiting
- **Authentication**: ❌ None required. The API is entirely public.
- **Rate Limiting (Observed)**: ❌ No rate limiting headers returned (no `X-RateLimit` headers present).