# Future Plan: Apify LinkedIn Jobs Scraper Integration

> Reference for future implementation of automated LinkedIn job scraping via the Apify API.

---

## Goal

Integrate the `curious_coder/linkedin-jobs-scraper` Apify actor into the Auto-Email pipeline to:
1. **Automatically scrape LinkedIn job listings** without manual URL copy-paste.
2. **Extract recruiter contact info** (name, email if available) from scraped job data.
3. **Send emails to multiple recipients** — one from Apify output, one extracted from JD text (if found).

---

## Apify Actor Details

- **Actor ID:** `curious_coder/linkedin-jobs-scraper`
- **Cost:** $1.00 / 1,000 results
- **Rating:** 4.9/5 (66 reviews)
- **Docs:** https://apify.com/curious_coder/linkedin-jobs-scraper

### Sample Output Fields (relevant subset)

```json
{
  "id": "3692563200",
  "link": "https://www.linkedin.com/jobs/view/...",
  "title": "English Data Labeling Analyst",
  "companyName": "Facebook",
  "companyLinkedinUrl": "...",
  "location": "Los Angeles Metropolitan Area",
  "postedAt": "2023-08-16",
  "descriptionText": "...",
  "descriptionHtml": "...",
  "jobPosterName": "Andrea Cowan",
  "jobPosterTitle": "Technical Recruiter at Meta",
  "jobPosterProfileUrl": "https://ca.linkedin.com/in/andrea-cowan-...",
  "seniorityLevel": "Associate",
  "employmentType": "Contract",
  "companyDescription": "...",
  "companyWebsite": "https://www.meta.com",
  "companyEmployeesCount": 36275
}
```

> **Note:** The Apify output does NOT contain an explicit `recruiterEmail` field. Email must be:
> 1. Extracted from `descriptionText` using regex (`extract_email()`)
> 2. Or sourced from additional context provided by the user

---

## Python Integration (apify-client)

### Installation
```bash
pip install apify-client
```

Add to `requirements.txt`:
```
apify-client
```

### Required Environment Variables
```env
APIFY_API_TOKEN=your_apify_token_here
```

Add to `.env` and `secrets.toml`.

### Example Usage

```python
from apify_client import ApifyClient

def scrape_linkedin_jobs_apify(search_url: str, num_jobs: int = 5) -> list[dict]:
    """Run the curious_coder/linkedin-jobs-scraper actor and return results."""
    client = ApifyClient(token=os.getenv("APIFY_API_TOKEN"))
    
    run_input = {
        "searchUrls": [{"url": search_url}],
        "count": num_jobs,
        "scrapeCompanyDetails": False,  # Set True for company info
    }

    run = client.actor("curious_coder/linkedin-jobs-scraper").call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    return items
```

---

## Planned Changes to Codebase

### 1. `utils/scraper.py`
- Add `scrape_linkedin_jobs_apify(search_url, num_jobs)` function.
- Attempt to extract email from `descriptionText` field using `extract_email()`.
- Return structured dict with: `company_name`, `job_title`, `job_description`, `recruiter_name`, `recruiter_email` (if found), `job_poster_profile_url`.

### 2. `utils/email_sender.py`
- Modify `send_email(to=...)` to accept comma-separated emails or a `list[str]`.
- Use `smtplib.SMTP.sendmail(from, to_list, msg)` to send to all at once.

### 3. `app.py`
- Add a new **"LinkedIn Job Search URL"** input mode (in addition to job view URL).
- Populate `auto_recipient` with a comma-separated list of both:
  - Email from Apify `descriptionText` extraction
  - Email from additional context (if provided by user)
- Deduplicate before displaying.

---

## Email Deduplication Logic

```python
emails = set()

# From Apify descriptionText
apify_email = extract_email(apify_job.get("descriptionText", ""))
if apify_email:
    emails.add(apify_email.lower())

# From user's additional context
context_email = extract_email(additional_context)
if context_email:
    emails.add(context_email.lower())

# From recruiter_email field (if scraping returns it in future)
if apify_job.get("recruiterEmail"):
    emails.add(apify_job["recruiterEmail"].lower())

recipient = ", ".join(sorted(emails))  # or just list them
```

---

## Open Questions (to resolve before implementing)

1. **Input schema:** Is the correct input field `searchUrls` or `startUrls`? Need to verify from the actor's actual input schema page.
2. **Email field:** Confirm if `curious_coder/linkedin-jobs-scraper` ever returns an explicit email field in any plan tier.
3. **Rate limits:** How many jobs can be scraped per run on the free/starter plan?
4. **Sync vs Async:** The Apify `.call()` method blocks until the run finishes. Consider using `.start()` + polling for large scrapes.

---

## Related Actors (for future reference)

| Actor | Use Case |
|---|---|
| `curious_coder/linkedin-jobs-scraper` | Public LinkedIn jobs (no login) |
| Advanced LinkedIn Jobs Scraper | Requires login/cookies, more fields |
| `apify/contact-info-scraper` | Find contact info for companies from jobs |
| Indeed Job Scraper | Scrape jobs from Indeed |

---

*Last updated: 2026-04-05*
*Status: PLANNED — Not yet implemented*
