# Company Application Trace Report

## Target Opportunity: Cursor

Stage: Registry
Status: FAILED
Time: 24 ms
Evidence: 0 rows returned
Owner: Company Discovery Engine
Suggested Command: `python scratch/debug_discovery.py --company cursor`

## Target Opportunity: Mercor

Stage: Registry
Status: FAILED
Time: 0 ms
Evidence: 0 rows returned
Owner: Company Discovery Engine
Suggested Command: `python scratch/debug_discovery.py --company mercor`

## Target Opportunity: Lovable

Stage: Registry
Status: FAILED
Time: 0 ms
Evidence: 0 rows returned
Owner: Company Discovery Engine
Suggested Command: `python scratch/debug_discovery.py --company lovable`

## Target Opportunity: Perplexity

Stage: Registry
Status: ✓
Time: 0 ms
Evidence: Found in company_intelligence_static

Stage: Careers Page
Status: ✓
Time: 0 ms
Evidence: website=https://perplexity.com, careers_url=None

Stage: ATS Detected
Status: ✓
Time: 0 ms
Evidence: ATS=lever

Stage: Jobs Extracted
Status: FAILED
Time: 14 ms
Evidence: 0 rows returned from opportunity_cache
Owner: Job Discovery Engine
Suggested Command: `python scratch/debug_extraction.py --company perplexity --provider lever`

## Target Opportunity: Decagon

Stage: Registry
Status: FAILED
Time: 0 ms
Evidence: 0 rows returned
Owner: Company Discovery Engine
Suggested Command: `python scratch/debug_discovery.py --company decagon`

## Target Opportunity: Harvey

Stage: Registry
Status: FAILED
Time: 0 ms
Evidence: 0 rows returned
Owner: Company Discovery Engine
Suggested Command: `python scratch/debug_discovery.py --company harvey`

## Target Opportunity: Mistral

Stage: Registry
Status: FAILED
Time: 0 ms
Evidence: 0 rows returned
Owner: Company Discovery Engine
Suggested Command: `python scratch/debug_discovery.py --company mistral`

## Target Opportunity: Glean

Stage: Registry
Status: ✓
Time: 0 ms
Evidence: Found in company_intelligence_static

Stage: Careers Page
Status: ✓
Time: 0 ms
Evidence: website=https://glean.com, careers_url=None

Stage: ATS Detected
Status: ✓
Time: 0 ms
Evidence: ATS=greenhouse

Stage: Jobs Extracted
Status: FAILED
Time: 0 ms
Evidence: 0 rows returned from opportunity_cache
Owner: Job Discovery Engine
Suggested Command: `python scratch/debug_extraction.py --company glean --provider greenhouse`

