# Graph Report - src  (2026-07-10)

## Corpus Check
- 360 files · ~484,777 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2516 nodes · 4072 edges · 220 communities (178 shown, 42 thin omitted)
- Extraction: 78% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 895 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 193
- Community 199
- Community 200

## God Nodes (most connected - your core abstractions)
1. `SourceInspector` - 56 edges
2. `Config` - 55 edges
3. `DiscoveryContext` - 43 edges
4. `LLMRouter` - 37 edges
5. `AnalyticsRepository` - 35 edges
6. `Credential` - 34 edges
7. `DiscoveryPlugin` - 31 edges
8. `ApifyManager` - 31 edges
9. `GreenhouseHandler` - 30 edges
10. `DiscoveryOrchestrator` - 30 edges

## Surprising Connections (you probably didn't know these)
- `ProviderDefinition` --uses--> `ApifyManager`  [INFERRED]
  common/credential_provider.py → integrations/apify_manager.py
- `verify_top_opportunities()` --indirect_call--> `process_job()`  [INFERRED]
  analytics/opportunity_verification.py → jobs/deduplicator.py
- `get_health_status()` --calls--> `MetricsRepository`  [INFERRED]
  api/main.py → discovery/pipeline/repositories/metrics_repository.py
- `JobRepository` --uses--> `HardRejectFilter`  [INFERRED]
  api/repositories/jobs_repository.py → discovery/hard_reject_filter.py
- `EmailConfirmationChecker` --uses--> `Config`  [INFERRED]
  applications/email_confirmation.py → config/config.py

## Import Cycles
- None detected.

## Communities (220 total, 42 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (20): AnalyticsRepository, Connection, get_analytics_repo(), get_ats_drilldown(), get_data_quality(), get_dead_boards(), get_duplicate_companies(), get_funnel() (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (15): ATSRegistry, Connection, For regression safety: creates a backup of the current ats_registry table., Promotes a VerificationResult to ACTIVE status.         Compares endpoint_hash t, FastPathRegistry, Any, Attempts to register a company directly as ACTIVE in the ats_registry using trus, JobCrawlerOrchestrator (+7 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (12): Company, CompanySource, Any, The immutable schema consumed by the rest of the Job Machine.     The downstream, SourceOrchestrator, GitHubConnector, OfficialAccelConnector, OfficialPeakXVConnector (+4 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (11): ContinuousDiscoveryEngine, DiscoveryDB, Any, ReplayCache, AshbyDiscoveryPlugin, Any, Normalize an Ashby URL to the board-level URL.          Input examples:, LeverDiscoveryPlugin (+3 more)

### Community 4 - "Community 4"
Cohesion: 0.24
Nodes (18): BrowserSearchSource, Fallback discovery mechanism using a secondary Exa search strategy.     (Replace, DiscoveryContext, Candidate, DiscoverySource, Evidence, ProbeResult, SourceResult (+10 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (20): CompanyResolver, _domain_slug(), _extract_domain(), Pipeline B — Company Resolver.  Resolves a free-text company name + apply URL fr, Push a discovery payload into discovery_queue so Pipeline A will         detect, Extract bare domain from any URL, stripping www., Stable, collision-resistant company_id from a domain., Resolves StandardJob.company + apply_url to an existing company_id.      Resolut (+12 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (12): ABC, Any, SourceAggregator, SourceConnector, SourceConnectorRegistry, AccelConnector, BaseResumableConnector, PeakXVConnector (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (21): build_pipeline(), # TODO: Load Candidate Context Logic, run(), PipelineContext, PipelineStage, ABC, Executes the pipeline stage and updates the context., ProductionCron (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (18): JobRepository, Any, Connection, Load jobs from DB → HardRejectFilter → JIE (IntentFilter) → Sort → Paginate → Re, _build_jie_profile(), IntentFilter, Any, CandidateProfile (+10 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (22): get_dashboard_summary(), get_discovery_queues(), get_health_status(), Connection, get_activities(), Connection, get_applications(), Connection (+14 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (23): clean_contacts(), add_discovery_source(), add_to_company_registry(), add_to_opportunity_cache(), get_active_greenhouse_slugs(), get_all_contacted_emails(), get_all_uncontacted_scored_leads(), get_cached_intelligence() (+15 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (8): GreenhouseParser, GreenhouseDiscoveryPlugin, Any, Normalize a Greenhouse URL to the board-level URL.          Input examples:, Any, Any, CrawlResult, Job

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (12): ABC, Any, SQLiteReservationRepository, WorkReservationRepository, Enum, str, ReasonCode, Stage (+4 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (12): DiscoveryPlugin, ABC, Any, Name of the ATS provider (e.g. 'greenhouse', 'workday'), Domains used to construct URL guesses., URL fragments or text used to identify this ATS., Parse a URL into an identity and confidence score., Returns the specific inspector for this ATS. (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (13): Any, DiscoveryOrchestrator, Any, Candidate, Logger, DiscoveryBudget, VerificationPolicy, VerificationResult (+5 more)

### Community 15 - "Community 15"
Cohesion: 0.17
Nodes (17): CandidateProfile, FitAnalyzer, BaseModel, CandidateFit, StructuredJob, CandidateFit, FitDetail, BaseModel (+9 more)

### Community 16 - "Community 16"
Cohesion: 0.08
Nodes (14): discover_contacts(), Phase 1 - Contact Discovery (Safe Job Discovery Architecture)     Order:     1., discover_email(), Phase 4 - Email Discovery     Tries GetProspect first (mocked if no key), falls, Executes the V0.1 Referral Engine flow:     1. Safe Job Discovery (Max 5 contact, run_referral_engine(), Phase 2 - Profile Intelligence     Uses Apify LinkedIn Profile Scraper.     For, scrape_profile() (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.16
Nodes (24): CompanyRecord, deduplicate(), domain_to_id(), extract_domain(), fetch_url(), infer_website(), insert_records(), load_dpiit() (+16 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (22): _categorize(), collect_evidence(), Candidate, rank_candidates(), RankedCandidate, CandidateEvaluator — Sprint C1B  Evidence Collection → Scoring → Ranking → Thres, Assign a coarse category purely from URL structure. No network calls., Collects all available structural evidence for a candidate URL.     This does NO (+14 more)

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (8): FeedbackTracker, outcome should be 'INTERVIEW' or 'REJECTED', MatchEngine, Enforces the V1.4 target distribution by percentiles:         Top 5% -> 90+, Evaluates discovered jobs against the Candidate Intelligence DB     Returns a sc, Config, WellfoundDailyCron, ApplicationWorker

### Community 20 - "Community 20"
Cohesion: 0.16
Nodes (8): GreenhouseHandler, Executes the Greenhouse application workflow.         Returns a dict with status, Iterates over custom fields. Returns True if all successfully answered and safe, Fix 4: Scan all required fields for empty or invalid values., Checks if the OTP verification screen is visible using robust signals., Dumps forensic state immediately after an OTP submission., Handles the OTP retrieval and submission flow with exponential backoff., Attempts to deterministically repair missing fields or OTPs.

### Community 21 - "Community 21"
Cohesion: 0.10
Nodes (10): CredentialProvider, Abstract Base Class for Credential Management, ExaProvider, SearchProvider, SearchResult, FirecrawlProvider, SearchResult, GoogleProvider (+2 more)

### Community 22 - "Community 22"
Cohesion: 0.15
Nodes (7): EarlyEligibilityScanner, EmailConfirmationChecker, Checks Gmail for a recent confirmation email from an ATS for the given company a, ApplicationExecutor, ATSDetector, EligibilityFilter, Determines if a job should be skipped BEFORE launching the browser.         Retu

### Community 23 - "Community 23"
Cohesion: 0.16
Nodes (8): GreenhouseConnector, LeverConnector, WorkdayConnector, HttpClient, DefaultFreshnessStrategy, FreshnessStrategy, Fallback strategy that relies purely on SHA256 content hashing., Returns the freshness strategy for this connector. Defaults to content hash fall

### Community 24 - "Community 24"
Cohesion: 0.20
Nodes (12): CanonicalJob, JobIdentity, RawJob, Convert a StandardJob to a CanonicalJob.          Args:             job:      St, AshbyNormalizer, GreenhouseNormalizer, JobNormalizer, LeverNormalizer (+4 more)

### Community 25 - "Community 25"
Cohesion: 0.12
Nodes (7): BaseRepository, Override in subclasses to create schema., JobRepository, Takes the new canonical jobs, diffs against existing active jobs for the board/c, SnapshotRepository, SyncRepository, BoardSyncSession

### Community 26 - "Community 26"
Cohesion: 0.16
Nodes (11): BoardIdentity, BoardSyncTask, Candidate, GreenhouseBoardIdentity, LeverBoardIdentity, SelectionResult, StandardBoardIdentity, VerifiedCandidate (+3 more)

### Community 27 - "Community 27"
Cohesion: 0.13
Nodes (7): AshbyDetector, ATSDetector, DetectorFactory, GreenhouseDetector, LeverDetector, ABC, Returns (is_match, valid_slug)

### Community 28 - "Community 28"
Cohesion: 0.13
Nodes (8): Page, LocationResolver, QuestionClassifier, QuestionEngine, Deterministic salary calculation based on location and role.         Targeting 7, Generates and normalizes an answer using Candidate RAG + LLM with Deterministic, ResponseNormalizer, SalaryEngineV1

### Community 29 - "Community 29"
Cohesion: 0.12
Nodes (11): Register an instantiated connector., ConnectorResult, DiscoveryConnector, ABC, Any, Stateless interface for all Discovery Connectors.     All state (sessions, retri, One-time setup (e.g. loading API keys). Raises Exception if config is missing., Verifies API endpoints are reachable or credentials are valid. (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (9): AshbyConnector, Connector, CrawlPolicy, CrawlPriority, ABC, Enum, Base interface for ATS Connectors.     A Connector strictly handles provider com, Returns the crawl policy configuration for this connector. (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.12
Nodes (7): AshbyInspector, ABC, e.g., 'greenhouse', 'ashby' - must match the adapter's source_name, Abstract interface for verifying that a detected URL is a valid,     functioning, SourceInspector, GreenhouseInspector, LeverInspector

### Community 32 - "Community 32"
Cohesion: 0.12
Nodes (10): BaseQueue, ABC, Any, Pushes an item onto the queue. Returns item ID., Pops an item from the queue, establishing a lock/lease., Acknowledges successful processing, removing the item from the queue., Negative acknowledgment. Returns the item to the queue or pushes to a DLQ/Retry, Abstract interface for queues to allow swapping SQLite for Redis/SQS in producti (+2 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (10): ATSDetector, CareerDiscoveryEngine, ClientSession, Manages optional fallbacks to search engines like Google/LinkedIn if the main cr, Detects ATS endpoints using DOM signatures, URL structures, and Regex fallbacks., Returns (ATS_Name, board_token, confidence), The core async worker logic to discover a company's career page., SearchProviderManager (+2 more)

### Community 34 - "Community 34"
Cohesion: 0.16
Nodes (9): ApplicationResult, BaseAdapter, ABC, Any, Executes the application logic for a specific ATS connector.         Returns an, GreenhouseAdapter, Any, ApplicationDispatcher (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.15
Nodes (11): AuthException, CredentialFactory, load_generic_credentials(), load_google_credentials(), ProviderDefinition, Exception, RateLimitException, Pairs GOOGLE_SEARCH_API_KEY_N with GOOGLE_CX_N (+3 more)

### Community 36 - "Community 36"
Cohesion: 0.13
Nodes (10): DuckDuckGoSearchProvider, SearchProvider, SearchResult, SearchProvider, SearchResult, SerperSearchProvider, MockSearchProvider, Protocol (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.15
Nodes (8): _extract_all_urls(), _is_career_link(), Candidate, Find internal pages worth visiting (career pages + about/company)., From a depth-1 page, find links that specifically look like career pages., Pull every URL-shaped string from the full HTML source., Heuristic: does this anchor look like a career/jobs page?, WebsiteCrawlerStrategy

### Community 38 - "Community 38"
Cohesion: 0.13
Nodes (11): ABC, Any, e.g., 'greenhouse', 'lever, e.g., 'v1.0' - Used to determine if jobs need re-parsing., Returns True if this adapter can handle the given URL., Performs the network I/O.          Takes a task (like a company endpoint) and re, Parses the raw payload into a structured format without network calls., Extracts individual job postings from the parsed data. (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.16
Nodes (5): EmailCritic, EmailClient, Exception, ResumeAttachmentError, OutreachEngine

### Community 40 - "Community 40"
Cohesion: 0.12
Nodes (6): generate_daily_queue(), Generates the daily application queue by isolating the top 20 HIGH priority jobs, Retrieves an OTP code and detailed forensics.     Returns:         {, retrieve_greenhouse_otp(), sync_sent_emails(), datetime

### Community 41 - "Community 41"
Cohesion: 0.32
Nodes (5): Credential, CredentialExhaustedException, Any, Wraps the existing ApifyManager logic for persistent tracking.     Never stores, SQLiteCredentialProvider

### Community 42 - "Community 42"
Cohesion: 0.14
Nodes (14): add_or_update_lead(), get_lead_by_hr_email(), Upserts a lead based on company_name, update_lead_state(), PipelineStage, Enum, transition_state(), classify_reply() (+6 more)

### Community 43 - "Community 43"
Cohesion: 0.12
Nodes (4): BreezyInspector, BreezyParser, BreezyDiscoveryPlugin, Any

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (4): JobviteInspector, JobviteParser, JobviteDiscoveryPlugin, Any

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (4): TeamtailorInspector, TeamtailorParser, Any, TeamtailorDiscoveryPlugin

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (3): ATSProvider, ProviderRegistry, Protocol

### Community 47 - "Community 47"
Cohesion: 0.17
Nodes (9): HardRejectFilter, HardRejectResult, Any, CandidateProfile, HardRejectFilter — ONE reusable binary filter.  Returns KEEP or REJECT. No scori, Filter a batch of jobs. Returns (passed, rejected, rejection_counts).          r, Extract minimum experience required from:           1. jie column already stored, Binary filter that evaluates a single job against a CandidateProfile.     Respon (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.15
Nodes (10): BackendFactory, Globally instantiates the active backend based on configuration/environment vari, BaseBackend, ABC, Any, Executes a search query and returns the raw response dictionary.         This mu, Abstract interface for all discovery backends.     Handles HTTP/Apify/SERP API e, DiscoveryCache (+2 more)

### Community 50 - "Community 50"
Cohesion: 0.13
Nodes (7): Computes the company health score dynamically on demand.         Factors: recent, generate_synthetic_startups(), seed_database(), import_ai_companies(), import_indian_startups(), import_manual_company(), import_yc_companies()

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (4): RecruiteeInspector, RecruiteeParser, Any, RecruiteeDiscoveryPlugin

### Community 52 - "Community 52"
Cohesion: 0.13
Nodes (4): SmartRecruitersInspector, SmartRecruitersParser, Any, SmartRecruitersDiscoveryPlugin

### Community 53 - "Community 53"
Cohesion: 0.13
Nodes (4): WorkableInspector, WorkableParser, Any, WorkableDiscoveryPlugin

### Community 54 - "Community 54"
Cohesion: 0.13
Nodes (8): DefaultInspector, Fallback validator for ATS providers that don't have a dedicated API validator y, Instantiates and registers a SourceAdapter., Instantiates and registers a SourceInspector., Returns the adapter by name, e.g., 'greenhouse, Returns the inspector by name, or a DefaultInspector if none is registered., Central registry for ATS plugins and inspectors., SourceRegistry

### Community 55 - "Community 55"
Cohesion: 0.12
Nodes (9): Validates the URL using the provider's native API., Extracts the Lever board slug and hits their API.         e.g., https://jobs.lev, Extracts the SmartRecruiters board slug and hits their API.         e.g., https:, Validates the Workable board by trying to hit their API.         e.g., https://a, Validates the Workday board by trying to hit the CXS jobs API.         e.g., htt, InspectionResult, Candidate, rank_candidate() (+1 more)

### Community 56 - "Community 56"
Cohesion: 0.26
Nodes (3): BaseATSProvider, EndpointIdentity, ClientSession

### Community 57 - "Community 57"
Cohesion: 0.17
Nodes (8): CandidateFit, EditOperation, RewriteStrategy, StructuredJob, Any, ResumeEditor, Any, ResumeEditor

### Community 58 - "Community 58"
Cohesion: 0.17
Nodes (5): AutoapplyEngine, Maps the recommended resume string from the DB to an absolute resume path, ProfileManager, Returns the fact value. Uses dynamic JSON if confidence >= 70 or human_verified, Manages the candidate profile used for form automation. Self-Learning V2.

### Community 59 - "Community 59"
Cohesion: 0.19
Nodes (5): ApplicationHandler, Native Playwright handler for Wellfound 'Easy Apply' flows., WellfoundHandler, Enum, WorkflowState

### Community 60 - "Community 60"
Cohesion: 0.16
Nodes (6): ConnectorRegistry, ConnectorManager, Any, Runs all healthy connectors in parallel.         Returns a list of raw payloads., Orchestrates the healthy connectors supplied by the registry.     Connectors ret, DiscoverySession

### Community 61 - "Community 61"
Cohesion: 0.14
Nodes (4): ConnectorRegistry, Runtime registry for all Discovery Connectors.     Reads config, instantiates cl, SmartRecruitersConnector, ConnectorCapability

### Community 62 - "Community 62"
Cohesion: 0.16
Nodes (4): LinkedinConnector, Any, ConnectorCapabilityMatrix, Defines what this connector is capable of doing.

### Community 63 - "Community 63"
Cohesion: 0.14
Nodes (3): WorkdayInspector, Normalize a Workday URL to the tenant board URL.          Input examples:, WorkdayDiscoveryPlugin

### Community 64 - "Community 64"
Cohesion: 0.16
Nodes (8): LandingPageResolver, LandingPageResolver — Sprint C1B  Responsibility: Given a generic /careers page, Return the ATS name if the URL itself is a recognized ATS endpoint., Scan full HTML for ATS URL patterns.         Returns (resolved_url, ats_name, co, Result of a LandingPageResolver.resolve() call., Resolves a generic careers page URL → ATS endpoint.      Pipeline:         URL →, :param http_client: An async-compatible HTTP client with a `.fetch(method, url)`, ResolvedEndpoint

### Community 65 - "Community 65"
Cohesion: 0.21
Nodes (6): BaseDiscoveryProvider, OpportunitySeed, ABC, Interface for all discovery providers.      Every provider must return a list of, CompanyIntelligenceProvider, InternetSearchProvider

### Community 66 - "Community 66"
Cohesion: 0.16
Nodes (5): QueryGenerator, Returns a list of strategy dictionaries to be executed., Passive Data Collection Query Generator.     Generates permutations of roles, lo, IndeedProvider, BaseProvider

### Community 67 - "Community 67"
Cohesion: 0.15
Nodes (6): ApifyProvider, JobProvider, ABC, Abstract base class for all job providers., Discover jobs and return a list of job dictionaries.         Expected keys:, CSVProvider

### Community 69 - "Community 69"
Cohesion: 0.19
Nodes (5): Runs sync across all sources and returns list of files that need parsing., Orchestrates generic sync over multiple specific source managers (Git, CSV, etc., SourceManager, CuratedRepositoryProvider, BaseProvider

### Community 71 - "Community 71"
Cohesion: 0.17
Nodes (6): PriorityScheduler, Yields target companies for the Job Discovery Engine based on their dynamic prio, Any, Prevents unnecessary scans by balancing daily API budgets against company priori, Creates a scan plan to maximize discovery quality without burning credits., ScanBudgetManager

### Community 72 - "Community 72"
Cohesion: 0.18
Nodes (6): Any, Pops an item and locks it for 300 seconds., Deletes the item from the queue., Unlocks the item so it can be retried, applying a 1-hour backoff., SQLite-backed implementation of BaseQueue for local development.     Uses a sing, SQLiteQueue

### Community 74 - "Community 74"
Cohesion: 0.24
Nodes (3): CrawlState, CrawlStateMachine, Any

### Community 75 - "Community 75"
Cohesion: 0.24
Nodes (7): _determine_company_size(), enrich_company(), EnrichmentProvider, GetProspectProvider, HunterProvider, ABC, Returns standard dict of role to email

### Community 76 - "Community 76"
Cohesion: 0.21
Nodes (6): JobCanonicalizer, Any, Lowercases, strips punctuation, and normalizes common title variations., Normalizes location string, prioritizing 'remote' if present., Normalizes messy job data and generates deterministic fingerprints for deduplica, Takes a raw scraped job and returns a normalized payload with fingerprint.

### Community 77 - "Community 77"
Cohesion: 0.20
Nodes (4): GoogleJobsBoardProvider, Google Jobs Pipeline B provider.  Wraps GoogleJobsProvider using the JobBoardPro, Pipeline B adapter over the existing GoogleJobsProvider., GoogleJobsProvider

### Community 78 - "Community 78"
Cohesion: 0.24
Nodes (7): BingBackend, DuckDuckGoBackend, Abstract search backend. Returns raw URLs from a search engine., Currently rate-limited (202 anti-bot). Kept as dormant fallback., Currently broken (primp impersonation failure). Kept as dormant fallback., SearchBackend, YahooBackend

### Community 79 - "Community 79"
Cohesion: 0.21
Nodes (4): HealthScorer, Exponential backoff: 1hr -> 6hr -> 1day -> 7days, Computes a 0-100 score based on metrics., RetryManager

### Community 80 - "Community 80"
Cohesion: 0.21
Nodes (4): Calls Apify Wellfound Scraper to extract real jobs., Emergency fallback using Playwright if all Apify actors fail.         Currently, WellfoundScraper, DiscoveryWorker

### Community 81 - "Community 81"
Cohesion: 0.21
Nodes (4): ApifyManager, Registers credential IDs into SQLite., Returns (db_id, credential_id) of the least used active credential., Returns (ApifyClient, key_id) for the least-used active credential.         tier

### Community 82 - "Community 82"
Cohesion: 0.20
Nodes (3): CleanupWorker, BaseWorker, BaseWorker

### Community 84 - "Community 84"
Cohesion: 0.18
Nodes (6): EventBus, Any, A lightweight, SQLite-backed event bus for decoupling the Discovery pipeline., Publishes an event to the system_events table., Registers an in-process handler for an event type., Polls the system_events table for PENDING events and executes their registered h

### Community 85 - "Community 85"
Cohesion: 0.29
Nodes (4): JDExtractor, Any, StructuredJob, Requirement

### Community 87 - "Community 87"
Cohesion: 0.22
Nodes (5): MarkdownJobParser, Parses Markdown tables to extract Job information., StandardJob, GenericCareersProvider, BaseProvider

### Community 88 - "Community 88"
Cohesion: 0.24
Nodes (3): BoardRepository, Scheduler, Queue

### Community 89 - "Community 89"
Cohesion: 0.20
Nodes (7): JobBoardProvider, ABC, Pipeline B — Job Board Provider base interface.  All Pipeline B providers implem, Abstract base for all Pipeline B providers.      Implementations must:       - R, Unique provider name, e.g. 'linkedin', 'google_jobs'., Returns True only when all required credentials/config are present.         Work, Fetch a batch of jobs from this job board.          Args:             cursor: Op

### Community 90 - "Community 90"
Cohesion: 0.20
Nodes (5): JobBoardResult, Returned by every JobBoardProvider.discover() call., LinkedInBoardProvider, LinkedIn Pipeline B provider.  Wraps LinkedInJobsProvider using the JobBoardProv, Pipeline B adapter over the existing LinkedInJobsProvider.

### Community 91 - "Community 91"
Cohesion: 0.24
Nodes (5): calculate_priority_score(), run_intelligence_engine(), ProjectSelector, Returns (Project, [Rejected_Project], Reasoning, Confidence), run_validation()

### Community 93 - "Community 93"
Cohesion: 0.24
Nodes (8): Returns (verification_status, http_status), verify_top_opportunities(), verify_url(), generate_canonical_id(), is_ats_url(), process_job(), Adds a job to the database or updates it if it's a duplicate.     Prioritizes AT, Generates a canonical ID for a job.     Prefers ATS Job ID from the URL if extra

### Community 94 - "Community 94"
Cohesion: 0.27
Nodes (3): RAGClient, Dynamically generates chunks from yash_master_profile.md., Retrieves Top 5 chunks using BM25, then reranks, returning the Final Top chunks.

### Community 98 - "Community 98"
Cohesion: 0.29
Nodes (6): Any, Executes the platform-specific search logic and returns (raw_jobs, warnings)., Overrides DiscoveryConnector.discover to implement Search Escalation Policy., Base class for all Search Connectors (Pipeline B1).     Owns Adaptive Escalation, SearchConnectorBase, SearchTask

### Community 101 - "Community 101"
Cohesion: 0.24
Nodes (5): InMemoryEventBus, Any, Registers a listener for a specific event type., Emits an event to all registered listeners asynchronously., A lightweight, pragmatic in-memory event bus for local development and single-ma

### Community 106 - "Community 106"
Cohesion: 0.24
Nodes (4): DuckDuckGoSearchProvider, Protocol, SearchProvider, SearchProviderRegistry

### Community 107 - "Community 107"
Cohesion: 0.20
Nodes (4): Any, SearchSource, Any, YCombinatorSource

### Community 108 - "Community 108"
Cohesion: 0.29
Nodes (3): EnrichmentLayer, Check if we have exceeded daily/monthly Apify constraints., Uses Apify to find Hiring Managers and Recruiters.

### Community 109 - "Community 109"
Cohesion: 0.27
Nodes (4): ProfileParser, Extracts content starting from `section_prefix` until the next `## SECTION` or E, Extracts a specific project block from Section 4 based on a keyword.         Exa, Builds the minimal context for template generation.         Includes ONLY the Sp

### Community 111 - "Community 111"
Cohesion: 0.25
Nodes (5): CompanyIntake, Any, Extracts companies from opportunities and processes them through the intake pipe, Checks if company exists. If NO, inserts as P3 NEW.         (Note: In a full pro, Company Discovery as a side-effect of Market Search (Pipeline B).     Extracts c

### Community 113 - "Community 113"
Cohesion: 0.28
Nodes (5): Board, FetchResult, Any, Yields RawJobs incrementally. The connector owns its own pagination., Determines if the payload is fresh enough to skip synchronization.

### Community 114 - "Community 114"
Cohesion: 0.28
Nodes (4): CompanyPipeline, PipelineResult, Orchestrates the discovery and verification of boards for a single company., Iterates through registered adapters to find one that can handle the URL.

### Community 115 - "Community 115"
Cohesion: 0.31
Nodes (4): IdentityResult, CompanyIdentityValidator, Fast heuristic check. Returns False if obviously mismatched., Deep multi-signal verification using HTML and Inspector metadata.

### Community 116 - "Community 116"
Cohesion: 0.22
Nodes (3): BaseProvider, WorkableProvider, ProviderCapabilities

### Community 117 - "Community 117"
Cohesion: 0.25
Nodes (6): DiscoveryStrategy, ABC, Candidate, Unique name for this strategy, e.g. 'website_crawler'., Returns a list of Candidate objects that might contain career/ATS endpoints., Abstract interface for Discovery Strategies.      A strategy's sole job is to re

### Community 118 - "Community 118"
Cohesion: 0.28
Nodes (4): CSVImportProvider, Any, BaseProvider, Reads candidate companies from a local CSV file.         Format expected: Compan

### Community 119 - "Community 119"
Cohesion: 0.25
Nodes (7): JobBoardRegistry, Pipeline B — Job Board Provider Registry.  The worker calls JobBoardRegistry.loa, # TODO: from src.discovery.providers.wellfound_board_provider import WellfoundBo, # TODO: from src.discovery.providers.indeed_board_provider import IndeedBoardPro, Plugin registry for Pipeline B providers.      Usage:         registry = JobBoar, Instantiate all registered providers, skip those that are unavailable         (e, _registered_classes()

### Community 120 - "Community 120"
Cohesion: 0.28
Nodes (3): BaseWorker, Any, Generic worker loop that continuously pulls tasks from a BaseQueue,     finds th

### Community 121 - "Community 121"
Cohesion: 0.33
Nodes (4): MatchEngine, MatchResult, Any, Evaluates opportunities and returns a transparent dual-score with a recommendati

### Community 122 - "Community 122"
Cohesion: 0.36
Nodes (8): apply_ranking_engine(), classify_role(), get_feedback_scores(), infer_experience(), parse_date(), Connection, rank_opportunity(), Pre-calculate feedback scores to avoid SQLite lock errors.

### Community 123 - "Community 123"
Cohesion: 0.28
Nodes (6): ApplicationExecutorInterface, ABC, Any, Submits the tailored application via Playwright., Processes the Strategy Queue., STRICT BOUNDARY: Do NOT implement or connect this interface for Sprint 1.6.

### Community 124 - "Community 124"
Cohesion: 0.33
Nodes (7): check_duplicate_run(), Checks if we have already sent the daily limit of emails today.     Returns True, run_daily_outreach(), get_scheduler_state(), job(), save_scheduler_state(), start_scheduler()

### Community 125 - "Community 125"
Cohesion: 0.33
Nodes (8): compile_and_count_pages(), extract_numbers(), extract_projects_from_tex(), parse_jd(), Extracts all integers and decimals from text., Extracts project blocks from LaTeX. Returns dict of {project_name: full_latex_bl, Agentic extraction of JD elements., tailor_resume()

### Community 126 - "Community 126"
Cohesion: 0.31
Nodes (4): FakeChoice, FakeMessage, FakeResponse, FakeUsage

### Community 128 - "Community 128"
Cohesion: 0.29
Nodes (4): JobValidator, Returns (valid_jobs, invalid_records)., Validates jobs before persistence to prevent corrupt data., Returns a list of error messages. Empty list means valid.

### Community 129 - "Community 129"
Cohesion: 0.25
Nodes (3): AshbyParser, LeverParser, WorkdayParser

### Community 131 - "Community 131"
Cohesion: 0.36
Nodes (4): EligibilityRule, EligibilityRuleProvider, Parses and serves Eligibility Rules from YAML.     Separates rule logic from the, Returns the version string and the ordered list of pre-compiled rules.

### Community 132 - "Community 132"
Cohesion: 0.29
Nodes (5): ProviderRegistry, BaseProvider, Registers a BaseProvider subclass., Returns instantiated versions of all registered providers., Factory for instantiating Discovery Providers.     Follows the plugin architectu

### Community 133 - "Community 133"
Cohesion: 0.32
Nodes (3): IngestionEngine, Removes legal entities for deduplication., Scans the source folder and ingests all CSVs and Excels.

### Community 134 - "Community 134"
Cohesion: 0.29
Nodes (3): EmailListener, Connects in read-only mode and searches for a recent OTP from a specific domain., Connects in read-only mode and searches for a magic verification link.

### Community 135 - "Community 135"
Cohesion: 0.29
Nodes (5): Any, Ensures bullets aren't deleted, order is intact, page limit., Ensures the LLM did not hallucinate new facts., SemanticValidator, StructuralValidator

### Community 136 - "Community 136"
Cohesion: 0.33
Nodes (3): adjust_provider_priority(), Historical outcomes automatically adjust provider scan priority.     Providers p, record_application_outcome()

### Community 137 - "Community 137"
Cohesion: 0.38
Nodes (3): Any, Returns (resume_path, resume_variant)         In the future, this will call Resu, ResumeSelector

### Community 139 - "Community 139"
Cohesion: 0.29
Nodes (4): ATSLearningEngine, Consults the learning cache to see if we already know the ATS for this domain, Records the outcome of an ATS job extraction to update historical confidence., Maintains a learning cache for ATS detection to prevent deterministic, expensive

### Community 140 - "Community 140"
Cohesion: 0.29
Nodes (4): DiscoveryQueue, Any, Fetches the next batch of companies to scan based on priority and lifecycle., Manages the priority queue for company discovery (P0 -> P1 -> P2 -> P3).     Ens

### Community 141 - "Community 141"
Cohesion: 0.33
Nodes (3): EligibilityDecision, EligibilityEngine, Deterministic V2 rule-based bouncer.     Determines if an opportunity is ELIGIBL

### Community 144 - "Community 144"
Cohesion: 0.29
Nodes (3): CareerLinkExpansionStrategy, Candidate, Replaces the generic BFS crawler. Extracts targeted internal links (About, Caree

### Community 145 - "Community 145"
Cohesion: 0.29
Nodes (3): CareerPageFingerprintStrategy, Candidate, Scans the raw HTML of the company homepage and career pages for embedded     ATS

### Community 146 - "Community 146"
Cohesion: 0.29
Nodes (3): Candidate, Parses /robots.txt to find Sitemap directives and blocked /jobs paths., RobotsTxtStrategy

### Community 147 - "Community 147"
Cohesion: 0.29
Nodes (3): Candidate, Parses /sitemap.xml to find careers, jobs, and external ATS URLs., SitemapStrategy

### Community 148 - "Community 148"
Cohesion: 0.33
Nodes (3): DiscoveryEngine, Removes legal entities for deduplication., Ingests companies from multiple sources, deduplicates, and incrementally updates

### Community 149 - "Community 149"
Cohesion: 0.33
Nodes (3): JobLifecycleManager, Any, Processes an array of raw jobs, computes hashes, and updates lifecycle states.

### Community 150 - "Community 150"
Cohesion: 0.43
Nodes (6): extract_text_from_md_link(), extract_url_from_md_link(), fetch_github_jobs(), parse_markdown_table(), Fetches job listings from dynamically discovered GitHub repositories via Search, Parses both HTML tables and raw Markdown tables.

### Community 152 - "Community 152"
Cohesion: 0.43
Nodes (4): Any, CandidateFit, StructuredJob, RewritePlanner

### Community 154 - "Community 154"
Cohesion: 0.53
Nodes (5): init_registry_db(), Pings ATS providers to find if slug exists., run(), slugify(), verify_ats()

### Community 155 - "Community 155"
Cohesion: 0.67
Nodes (5): fetch_query(), fetch_table(), get_db_connection(), get_latest_heartbeats(), DataFrame

### Community 156 - "Community 156"
Cohesion: 0.33
Nodes (3): Any, RateLimiter, Handles per-provider request limits, exponential backoff, retries, jitter,

### Community 157 - "Community 157"
Cohesion: 0.40
Nodes (3): CompiledRegexCache, ConfigLoader, Any

### Community 158 - "Community 158"
Cohesion: 0.33
Nodes (4): DiscoveryDeduplicator, Any, Groups opportunities by Company and Job Title (or some strong similarity)., Deduplicates Opportunities by merging alternative apply sources rather than dele

### Community 159 - "Community 159"
Cohesion: 0.33
Nodes (3): GenericParserFallback, Executes the fallback chain to extract jobs from a generic careers page., A shared parsing fallback chain to be used when stateless ATS connectors fail.

### Community 163 - "Community 163"
Cohesion: 0.33
Nodes (4): Any, Platform-Agnostic Search Planner.     Generates pure Market Discovery intents ba, Generates canonical Market Searches., SearchPlanner

### Community 164 - "Community 164"
Cohesion: 0.40
Nodes (4): ABC, Any, Discovers new company seeds.         Returns a list of dicts:         {, SeedSource

### Community 166 - "Community 166"
Cohesion: 0.33
Nodes (3): ApplicationPrioritizer, Any, Evaluates opportunities relative to one another to produce the daily application

### Community 167 - "Community 167"
Cohesion: 0.70
Nodes (4): get_role_counts(), print_apify_analytics(), print_funnel_metrics(), print_source_attribution()

### Community 169 - "Community 169"
Cohesion: 0.40
Nodes (3): QuestionClassifier, Classifies application form questions and determines if they are safe to auto-an, Returns: 'DETERMINISTIC', 'ESCALATE', or 'UNKNOWN'

### Community 170 - "Community 170"
Cohesion: 0.40
Nodes (3): Page, Verifies if an application was successfully submitted using a weighted confidenc, SubmissionVerifier

### Community 171 - "Community 171"
Cohesion: 0.40
Nodes (3): CareerEndpointRepository, Connection, Updates status, health_status, confidence, failure_reason, and last_verified_at

### Community 174 - "Community 174"
Cohesion: 0.50
Nodes (3): ABC, SearchResult, SearchProvider

### Community 175 - "Community 175"
Cohesion: 0.40
Nodes (3): BaseDiscoverySource, Any, Interface for all Opportunity Discovery Sources.     Sources are strictly respon

### Community 176 - "Community 176"
Cohesion: 0.50
Nodes (4): apply_quality_filters(), evaluate_job_quality(), Runs over all jobs in the database and updates their quality score., Evaluates job title for seniority penalties and role boosts.     Returns (qualit

### Community 178 - "Community 178"
Cohesion: 0.70
Nodes (4): run_validation(), test_agent5(), test_greenhouse(), test_outreach()

### Community 179 - "Community 179"
Cohesion: 0.67
Nodes (3): analyze_failure(), generate_discovery_failure_report(), Returns (Failure Reason, Next Action)

### Community 180 - "Community 180"
Cohesion: 0.83
Nodes (3): load_profile(), run_learner(), save_profile()

### Community 182 - "Community 182"
Cohesion: 0.83
Nodes (3): check_ats_duplicate(), run_shadow_mode(), setup_shadow_table()

### Community 183 - "Community 183"
Cohesion: 0.67
Nodes (3): collect_company_metadata(), Groq, Uses DDG search to attempt to find company domain, employee count, and CTO/Found

### Community 185 - "Community 185"
Cohesion: 0.50
Nodes (3): Logger, Creates a structured logger that writes to file and console., setup_logger()

## Knowledge Gaps
- **9 isolated node(s):** `Settings`, `Candidate`, `VerifiedCandidate`, `SelectionResult`, `BoardSyncTask` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **42 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Config` connect `Community 19` to `Community 1`, `Community 131`, `Community 138`, `Community 140`, `Community 22`, `Community 151`, `Community 28`, `Community 161`, `Community 35`, `Community 39`, `Community 177`, `Community 58`, `Community 60`, `Community 65`, `Community 67`, `Community 68`, `Community 75`, `Community 77`, `Community 80`, `Community 81`, `Community 84`, `Community 87`, `Community 91`, `Community 94`, `Community 108`, `Community 109`, `Community 116`, `Community 126`?**
  _High betweenness centrality (0.217) - this node is a cross-community bridge._
- **Why does `ATSRegistry` connect `Community 1` to `Community 19`, `Community 4`, `Community 102`, `Community 14`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `BaseWorker` connect `Community 82` to `Community 1`, `Community 130`, `Community 3`, `Community 5`, `Community 72`, `Community 12`, `Community 153`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `SourceInspector` (e.g. with `AshbyInspector` and `BreezyInspector`) actually correct?**
  _`SourceInspector` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `Config` (e.g. with `EmailConfirmationChecker` and `AutoapplyEngine`) actually correct?**
  _`Config` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `DiscoveryContext` (e.g. with `BrowserSearchSource` and `ATSRegistry`) actually correct?**
  _`DiscoveryContext` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `LLMRouter` (e.g. with `AutoapplyEngine` and `.__init__()`) actually correct?**
  _`LLMRouter` has 27 INFERRED edges - model-reasoned connections that need verification._