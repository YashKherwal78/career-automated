# Graph Report - backend  (2026-07-14)

## Corpus Check
- 406 files · ~939,299 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2930 nodes · 6460 edges · 188 communities (151 shown, 37 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 706 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e0dcb70e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SourceInspector
- LLMRouter
- DiscoveryContext
- Config
- database.py
- setup_logger
- get_connection
- application_worker.py
- fallback_models.py
- Last updated: June 2026
- JobBoardProvider
- models.py
- AnalyticsRepository
- credential_provider.py
- DefaultFreshnessStrategy
- SourceOrchestrator
- db.py
- job_board_worker.py
- job_crawler_worker.py
- is_postgres
- SourceConnector
- get-jobs.ts
- LeverDiscoveryPlugin
- RawJob
- PlanningContext
- add_or_update_lead
- run_pipeline.py
- rie_pipeline.py
- package.json
- GreenhouseHandler
- Credential
- DiscoveryPlugin
- WorkdayDiscoveryPlugin
- ProfileManager
- StructuredJob
- ATSRegistry
- import_company_datasets.py
- Response
- CompatCursor
- .transition
- seed_discovery_worker.py
- ApifyManager
- ATSDetector
- Telemetry
- main.py
- HttpClient
- OpportunitySeed
- ATSDetector
- DiscoveryConnector
- career_discovery.py
- SourceAdapter
- ApplicationResult
- SearchResult
- CompanyIntelligenceEngine
- EndpointIntelligenceService
- base_provider.py
- WebsiteCrawlerStrategy
- ApplicationExecutor
- BaseBackend
- GreenhouseDiscoveryPlugin
- ProviderCapabilities
- BaseQueue
- IntentFilter
- CredentialFactory
- workday.py
- ATSProvider
- EndpointIdentity
- pipeline.py
- SourceRegistry
- SmartRecruitersDiscoveryPlugin
- LandingPageResolver
- RAGClient
- discovery_providers.py
- DiscoverySession
- IndeedProvider
- CrawlStateMachine
- compilerOptions
- database.py
- JobCanonicalizer
- LinkedinConnector
- SourceManager
- NegativeCache
- SQLiteReservationRepository
- RetryManager
- JobQualificationExtractor
- CuratedRepositoryProvider
- BaseWorker
- ScanBudgetManager
- SearchBackend
- WorkableProvider
- scheduler.py
- settings.py
- ProfileExtractorV2
- registry_generator.py
- WellfoundConnector
- EventBus
- JDExtractor
- BreezyDiscoveryPlugin
- JobviteDiscoveryPlugin
- RecruiteeDiscoveryPlugin
- TeamtailorDiscoveryPlugin
- WorkableDiscoveryPlugin
- SearchStrategy
- InMemoryEventBus
- AshbyProvider
- GreenhouseProvider
- LeverProvider
- DuckDuckGoSearchProvider
- SearchTask
- JobProvider
- CompanyIntake
- IndeedConnector
- AtsPatternStrategy
- ranking.py
- ApplicationExecutorInterface
- EnrichmentLayer
- run_batch.py
- DuckDuckGoProvider
- ProfileParser
- 2026 Artificial Intelligence Internship & New Grad Positions
- JDFetcher
- BoardRegistry
- CSVImportProvider
- 2026 International AI Internships :books::globe_with_meridians:
- 2026 International AI New Grad Positions :mortar_board::globe_with_meridians:
- 2026 USA AI New Graduate Positions :mortar_board::eagle:
- JobRegistry
- deduplicator.py
- provider_effectiveness.py
- ResumeSelector
- EligibilityEngine
- .pop
- DefaultStubProvider
- JobLifecycleManager
- IngestionEngine
- EmailListener
- github_jobs.py
- .validate
- PROJECT INTELLIGENCE DATABASE
- CompiledRegexCache
- DiscoveryDeduplicator
- DiscoveryQueue
- company_pipeline.py
- CareerLinkExpansionStrategy
- CareerPageFingerprintStrategy
- RobotsTxtStrategy
- SitemapStrategy
- DiscoveryEngine
- ApplicationPrioritizer
- .generate_strategy
- QuestionClassifier
- SubmissionVerifier
- CredentialTelemetry
- AmazonSignature
- RateLimiter
- GenericParserFallback
- .get_all_providers
- hash_job
- .generate_market_tasks
- BaseDiscoverySource
- JobScoringEngine
- CryptoManager
- profile_learner.py
- AshbySignature
- BambooHRSignature
- RecruiteeSignature
- TeamtailorSignature
- ExperienceNormalizer
- ranking_engine.py
- ResumeCompiler
- Daily Outreach Report
- .discover
- validate_sprint_a.py
- outreach_trace_report.md
- README.md

## God Nodes (most connected - your core abstractions)
1. `Config` - 119 edges
2. `setup_logger()` - 109 edges
3. `get_connection()` - 86 edges
4. `SourceInspector` - 78 edges
5. `is_postgres()` - 64 edges
6. `get_connection()` - 56 edges
7. `LLMRouter` - 50 edges
8. `HttpClient` - 48 edges
9. `DiscoveryContext` - 45 edges
10. `Credential` - 43 edges

## Surprising Connections (you probably didn't know these)
- `migrate_existing_companies()` --calls--> `get_connection()`  [EXTRACTED]
  scripts/migrate_existing_to_verified.py → src/api/db.py
- `migrate_existing_companies()` --calls--> `is_postgres()`  [EXTRACTED]
  scripts/migrate_existing_to_verified.py → src/api/db.py
- `_enqueue_batch()` --calls--> `is_postgres()`  [EXTRACTED]
  scripts/migrate_existing_to_verified.py → src/api/db.py
- `run_trace()` --calls--> `get_connection()`  [EXTRACTED]
  trace_100.py → src/api/db.py
- `DiscoveryResult` --uses--> `SourceInspector`  [INFERRED]
  src/discovery/pipeline/fallback_models.py → src/discovery/inspectors/base_inspector.py

## Import Cycles
- None detected.

## Communities (188 total, 37 thin omitted)

### Community 0 - "SourceInspector"
Cohesion: 0.06
Nodes (26): AshbyInspector, ABC, e.g., 'greenhouse', 'ashby' - must match the adapter's source_name, Validates the URL using the provider's native API., Abstract interface for verifying that a detected URL is a valid,     functioning, SourceInspector, BreezyInspector, JobviteInspector (+18 more)

### Community 1 - "LLMRouter"
Cohesion: 0.05
Nodes (34): get_cached_intelligence(), set_cached_intelligence(), calculate_priority_score(), run_intelligence_engine(), ProjectSelector, Returns (Project, [Rejected_Project], Reasoning, Confidence), ApplicationJudge, CriticRejection (+26 more)

### Community 2 - "DiscoveryContext"
Cohesion: 0.10
Nodes (38): DetectorRegistry, Central registry of ATS detectors., ContinuousDiscoveryEngine, DiscoveryDB, Any, EndpointRankingEngine, Ranks available candidates for a given company based on confidence score., BrowserSearchSource (+30 more)

### Community 3 - "Config"
Cohesion: 0.06
Nodes (21): datetime, Returns (verification_status, http_status), verify_url(), generate_daily_queue(), Generates the daily application queue by isolating the top 20 HIGH priority jobs, EmailConfirmationChecker, ATSDetector, Config (+13 more)

### Community 4 - "database.py"
Cohesion: 0.07
Nodes (31): clean_contacts(), add_discovery_source(), add_to_company_registry(), add_to_opportunity_cache(), get_active_greenhouse_slugs(), get_all_contacted_emails(), get_all_uncontacted_scored_leads(), get_connection() (+23 more)

### Community 5 - "setup_logger"
Cohesion: 0.06
Nodes (26): dotenv, analyze_failure(), generate_discovery_failure_report(), Returns (Failure Reason, Next Action), get_role_counts(), print_apify_analytics(), print_funnel_metrics(), print_source_attribution() (+18 more)

### Community 6 - "get_connection"
Cohesion: 0.08
Nodes (25): get_connection(), connector_metrics(), coverage_report(), health_check(), pipeline_metrics(), _q(), _ql(), Health & Observability API GET /api/v1/health          - system health check GET (+17 more)

### Community 7 - "application_worker.py"
Cohesion: 0.07
Nodes (16): FeedbackTracker, outcome should be 'INTERVIEW' or 'REJECTED', ApplicationHandler, Native Playwright handler for Wellfound 'Easy Apply' flows., WellfoundHandler, MatchEngine, Enforces the V1.4 target distribution by percentiles:         Top 5% -> 90+, Evaluates discovered jobs against the Candidate Intelligence DB     Returns a sc (+8 more)

### Community 8 - "fallback_models.py"
Cohesion: 0.07
Nodes (33): _categorize(), collect_evidence(), Candidate, rank_candidates(), RankedCandidate, CandidateEvaluator — Sprint C1B  Evidence Collection → Scoring → Ranking → Thres, Assign a coarse category purely from URL structure. No network calls., Collects all available structural evidence for a candidate URL.     This does NO (+25 more)

### Community 9 - "Last updated: June 2026"
Cohesion: 0.05
Nodes (42): AVAILABILITY, COMPENSATION, Experience 1: OrangeLabs (Feb 2026 – Apr 2026), Experience 2: ScoreMe Solutions (May 2025 – Jun 2025), Experience 3: Bharat Electronics Limited (Jun 2025 – Jul 2025), Final Year B.Tech, IIT Roorkee (Chemical Engineering, 2022–2026), Formatting Rules (Override Everything), LANGUAGES (+34 more)

### Community 10 - "JobBoardProvider"
Cohesion: 0.08
Nodes (21): GoogleJobsBoardProvider, Google Jobs Pipeline B provider.  Wraps GoogleJobsProvider using the JobBoardPro, Pipeline B adapter over the existing GoogleJobsProvider., GoogleJobsProvider, JobBoardProvider, JobBoardResult, ABC, Pipeline B — Job Board Provider base interface.  All Pipeline B providers implem (+13 more)

### Community 11 - "models.py"
Cohesion: 0.13
Nodes (12): SmartRecruitersConnector, BoardSyncTask, ConnectorCapability, SelectionResult, VerifiedCandidate, Connector, ABC, Base interface for ATS Connectors.     A Connector strictly handles provider com (+4 more)

### Community 12 - "AnalyticsRepository"
Cohesion: 0.08
Nodes (18): AnalyticsRepository, get_analytics_repo(), get_ats_drilldown(), get_data_quality(), get_dead_boards(), get_duplicate_companies(), get_funnel(), get_lineage() (+10 more)

### Community 13 - "credential_provider.py"
Cohesion: 0.12
Nodes (17): AuthException, CredentialProvider, Exception, RateLimitException, Abstract Base Class for Credential Management, ABC, SearchResult, SearchProvider (+9 more)

### Community 14 - "DefaultFreshnessStrategy"
Cohesion: 0.12
Nodes (15): ConnectorRegistry, Runtime registry for all Discovery Connectors.     Reads config, instantiates cl, AmazonJSONConnector, BambooHRConnector, GreenhouseConnector, GreenhouseJSONConnector, LeverConnector, LeverJSONConnector (+7 more)

### Community 15 - "SourceOrchestrator"
Cohesion: 0.09
Nodes (12): Company, CompanySource, Any, The immutable schema consumed by the rest of the Job Machine.     The downstream, SourceOrchestrator, GitHubConnector, OfficialAccelConnector, OfficialPeakXVConnector (+4 more)

### Community 16 - "db.py"
Cohesion: 0.09
Nodes (17): json_extract(), JobRepository, Any, Load jobs from DB → HardRejectFilter → JIE (IntentFilter) → Sort → Paginate → Re, EndpointCandidate, BaseModel, HardRejectFilter, HardRejectResult (+9 more)

### Community 17 - "job_board_worker.py"
Cohesion: 0.09
Nodes (22): CompanyResolver, _domain_slug(), _extract_domain(), Pipeline B — Company Resolver.  Resolves a free-text company name + apply URL fr, Push a discovery payload into discovery_queue so Pipeline A will         detect, Extract bare domain from any URL, stripping www., Stable, collision-resistant company_id from a domain., Resolves StandardJob.company + apply_url to an existing company_id.      Resolut (+14 more)

### Community 18 - "job_crawler_worker.py"
Cohesion: 0.11
Nodes (15): Queue, GreenhouseBoardIdentity, LeverBoardIdentity, ConnectorExecutor, ExecutionResult, Executes a single session under the concurrency semaphore., NormalizerFactory, BoardRepository (+7 more)

### Community 19 - "is_postgres"
Cohesion: 0.10
Nodes (11): is_postgres(), BaseRepository, Override in subclasses to create schema., CareerEndpointRepository, Connection, Updates status, health_status, confidence, failure_reason, and last_verified_at, DiscoveryCandidate, DiscoveryCandidateRepository (+3 more)

### Community 20 - "SourceConnector"
Cohesion: 0.12
Nodes (12): ABC, Any, SourceAggregator, SourceConnector, SourceConnectorRegistry, AccelConnector, BaseResumableConnector, PeakXVConnector (+4 more)

### Community 21 - "get-jobs.ts"
Cohesion: 0.12
Nodes (23): main(), parseIssueBody(), HEADERS, MARKERS, TABLES, __dirname, __filename, generateMarkdownTable() (+15 more)

### Community 22 - "LeverDiscoveryPlugin"
Cohesion: 0.09
Nodes (9): LeverInspector, Extracts the Lever board slug and hits their API.         e.g., https://jobs.lev, LeverParser, Any, LeverDiscoveryPlugin, Any, Normalize a Lever URL to the board-level URL.          Input examples:, CrawlResult (+1 more)

### Community 23 - "RawJob"
Cohesion: 0.14
Nodes (15): CanonicalJob, JobIdentity, RawJob, Convert a StandardJob to a CanonicalJob.          Args:             job:      St, JobValidator, Returns (valid_jobs, invalid_records)., Validates jobs before persistence to prevent corrupt data., Returns a list of error messages. Empty list means valid. (+7 more)

### Community 24 - "PlanningContext"
Cohesion: 0.17
Nodes (16): PlanningContextBuilder, Any, EndpointIntelligence, PlanningContext, PlanningContextBuilder, Any, RuntimeState, CrawlPlanner (+8 more)

### Community 25 - "add_or_update_lead"
Cohesion: 0.12
Nodes (20): add_or_update_lead(), get_lead(), get_lead_by_hr_email(), Upserts a lead based on company_name, update_lead_state(), PipelineStage, Enum, transition_state() (+12 more)

### Community 26 - "run_pipeline.py"
Cohesion: 0.11
Nodes (20): init_db(), build_pipeline(), # TODO: Load Candidate Context Logic, run(), PipelineContext, PipelineStage, ABC, Executes the pipeline stage and updates the context. (+12 more)

### Community 27 - "rie_pipeline.py"
Cohesion: 0.15
Nodes (14): CandidateFit, EditOperation, RewriteStrategy, StructuredJob, Any, ResumeEditor, Any, CandidateFit (+6 more)

### Community 28 - "package.json"
Cohesion: 0.07
Nodes (26): @actions/core, @actions/github, author, dependencies, @actions/core, @actions/github, dotenv, @supabase/supabase-js (+18 more)

### Community 29 - "GreenhouseHandler"
Cohesion: 0.13
Nodes (11): GreenhouseHandler, Page, Executes the Greenhouse application workflow.         Returns a dict with status, Iterates over custom fields. Returns True if all successfully answered and safe, Fix 4: Scan all required fields for empty or invalid values., Checks if the OTP verification screen is visible using robust signals., Dumps forensic state immediately after an OTP submission., Handles the OTP retrieval and submission flow with exponential backoff. (+3 more)

### Community 30 - "Credential"
Cohesion: 0.19
Nodes (10): Credential, CredentialExhaustedException, InMemoryCredentialProvider, load_generic_credentials(), load_google_credentials(), Any, Wraps the existing ApifyManager logic for persistent tracking.     Never stores, Pairs GOOGLE_SEARCH_API_KEY_N with GOOGLE_CX_N (+2 more)

### Community 31 - "DiscoveryPlugin"
Cohesion: 0.08
Nodes (12): DiscoveryPlugin, ABC, Any, Name of the ATS provider (e.g. 'greenhouse', 'workday'), Domains used to construct URL guesses., URL fragments or text used to identify this ATS., Parse a URL into an identity and confidence score., Returns the specific inspector for this ATS. (+4 more)

### Community 32 - "WorkdayDiscoveryPlugin"
Cohesion: 0.09
Nodes (5): WorkdayParser, Any, Normalize a Workday URL to the tenant board URL.          Input examples:, WorkdayDiscoveryPlugin, TestWorkdayParser

### Community 33 - "ProfileManager"
Cohesion: 0.11
Nodes (10): ProfileManager, Returns the fact value. Uses dynamic JSON if confidence >= 70 or human_verified, Manages the candidate profile used for form automation. Self-Learning V2., LocationResolver, QuestionClassifier, QuestionEngine, Deterministic salary calculation based on location and role.         Targeting 7, Generates and normalizes an answer using Candidate RAG + LLM with Deterministic (+2 more)

### Community 34 - "StructuredJob"
Cohesion: 0.19
Nodes (15): IntentFilter — wraps JIE (JDExtractor + FitAnalyzer) to score jobs.  This is the, CandidateProfile, FitAnalyzer, BaseModel, CandidateFit, StructuredJob, CandidateFit, FitDetail (+7 more)

### Community 35 - "ATSRegistry"
Cohesion: 0.10
Nodes (13): ATSRegistry, Connection, VerificationResult, Promotes a VerificationResult to ACTIVE status.         Compares endpoint_hash t, Promotes a batch of endpoints in a single transaction.         Each item in batc, For regression safety: creates a backup of the current ats_registry table., FastPathRegistry, Any (+5 more)

### Community 36 - "import_company_datasets.py"
Cohesion: 0.16
Nodes (24): NamedTuple, CompanyRecord, deduplicate(), domain_to_id(), extract_domain(), fetch_url(), infer_website(), insert_records() (+16 more)

### Community 37 - "Response"
Cohesion: 0.10
Nodes (8): Response, iCIMSSignature, LeverSignature, Analyzes the response body/headers/URL to determine if it is this ATS., If this is the ATS, extract or format the canonical URL., Returns the first matching ATSDetector., WorkableSignature, WorkdaySignature

### Community 38 - "CompatCursor"
Cohesion: 0.14
Nodes (6): CompatConnection, CompatCursor, Any, table_exists(), get_dashboard_summary(), get_discovery_queues()

### Community 39 - ".transition"
Cohesion: 0.14
Nodes (12): _enqueue_batch(), migrate_existing_companies(), PipelineStateManager, Any, Exception, Executes a lifecycle transition for a batch of companies atomically., Executes a lifecycle transition atomically within a single database transaction., TransitionError (+4 more)

### Community 40 - "seed_discovery_worker.py"
Cohesion: 0.15
Nodes (10): ABC, Any, Discovers new company seeds.         Returns a list of dicts:         {, SeedSource, Any, SearchSource, Any, YCombinatorSource (+2 more)

### Community 41 - "ApifyManager"
Cohesion: 0.13
Nodes (7): ProviderDefinition, LinkedInJobsProvider, ApifyManager, Registers credential IDs into SQLite., Returns (db_id, credential_id) of the least used active credential., Returns (ApifyClient, key_id) for the least-used active credential.         tier, ApifyProvider

### Community 42 - "ATSDetector"
Cohesion: 0.11
Nodes (9): ATSDetector, BreezySignature, GreenhouseSignature, JazzHRSignature, ABC, The canonical ID of the ATS provider in ats_providers., Return the confidence score of the match (0-100)., Return the reason for the match. (+1 more)

### Community 43 - "Telemetry"
Cohesion: 0.17
Nodes (13): DiscoveryRegistry, Retrieves all active or discovered candidates for a company, sorted by confidenc, Enum, str, ReasonCode, Stage, Status, Telemetry (+5 more)

### Community 44 - "main.py"
Cohesion: 0.19
Nodes (6): JobRepository, get_db(), get_board_jobs(), get_job(), get_job_repo(), get_jobs()

### Community 45 - "HttpClient"
Cohesion: 0.16
Nodes (6): Board, FetchResult, HttpClient, Any, Yields RawJobs incrementally. The connector owns its own pagination., Determines if the payload is fresh enough to skip synchronization.

### Community 46 - "OpportunitySeed"
Cohesion: 0.19
Nodes (9): BaseDiscoveryProvider, OpportunitySeed, ABC, Interface for all discovery providers.      Every provider must return a list of, CompanyIntelligenceProvider, InternetSearchProvider, QueryGenerator, Returns a list of strategy dictionaries to be executed. (+1 more)

### Community 47 - "ATSDetector"
Cohesion: 0.13
Nodes (7): AshbyDetector, ATSDetector, DetectorFactory, GreenhouseDetector, LeverDetector, ABC, Returns (is_match, valid_slug)

### Community 48 - "DiscoveryConnector"
Cohesion: 0.11
Nodes (11): Register an instantiated connector., DiscoveryConnector, ABC, Any, Stateless interface for all Discovery Connectors.     All state (sessions, retri, Defines what this connector is capable of doing., One-time setup (e.g. loading API keys). Raises Exception if config is missing., Verifies API endpoints are reachable or credentials are valid. (+3 more)

### Community 49 - "career_discovery.py"
Cohesion: 0.15
Nodes (10): ATSDetector, CareerDiscoveryEngine, ClientSession, Manages optional fallbacks to search engines like Google/LinkedIn if the main cr, Detects ATS endpoints using DOM signatures, URL structures, and Regex fallbacks., Returns (ATS_Name, board_token, confidence), The core async worker logic to discover a company's career page., SearchProviderManager (+2 more)

### Community 50 - "SourceAdapter"
Cohesion: 0.13
Nodes (11): ABC, Any, e.g., 'greenhouse', 'lever, e.g., 'v1.0' - Used to determine if jobs need re-parsing., Returns True if this adapter can handle the given URL., Performs the network I/O.          Takes a task (like a company endpoint) and re, Parses the raw payload into a structured format without network calls., Extracts individual job postings from the parsed data. (+3 more)

### Community 51 - "ApplicationResult"
Cohesion: 0.19
Nodes (9): ApplicationResult, BaseAdapter, ABC, Any, Executes the application logic for a specific ATS connector.         Returns an, GreenhouseAdapter, Any, ApplicationDispatcher (+1 more)

### Community 52 - "SearchResult"
Cohesion: 0.16
Nodes (10): DuckDuckGoSearchProvider, SearchProvider, SearchResult, SearchProvider, SearchResult, SerperSearchProvider, MockSearchProvider, Protocol (+2 more)

### Community 53 - "CompanyIntelligenceEngine"
Cohesion: 0.18
Nodes (3): CompanyIntelligenceEngine, Computes the company health score dynamically on demand.         Factors: recent, Computes priority scores, relevance, and assigns scan frequencies.     Listens t

### Community 54 - "EndpointIntelligenceService"
Cohesion: 0.12
Nodes (11): ConfidenceFormula, EndpointIntelligenceService, Any, Called when an endpoint candidate fails verification (e.g. 404, invalid signatur, Called by JobCrawlerWorker after a successful sync., Called by JobCrawlerWorker after a sync fails., confidence = provider_weight + historical_success + freshness + evidence - histo, Centralized service for managing confidence, health, and history of ATS endpoint (+3 more)

### Community 55 - "base_provider.py"
Cohesion: 0.32
Nodes (7): Candidate, DiscoveryStrategy, ABC, Unique name for this strategy, e.g. 'website_crawler'., Abstract interface for Discovery Strategies.      A strategy's sole job is to re, ProviderRegistry, Factory for instantiating Discovery Providers.     Follows the plugin architectu

### Community 56 - "WebsiteCrawlerStrategy"
Cohesion: 0.14
Nodes (8): _extract_all_urls(), _is_career_link(), Candidate, Find internal pages worth visiting (career pages + about/company)., From a depth-1 page, find links that specifically look like career pages., Pull every URL-shaped string from the full HTML source., Heuristic: does this anchor look like a career/jobs page?, WebsiteCrawlerStrategy

### Community 57 - "ApplicationExecutor"
Cohesion: 0.19
Nodes (4): EarlyEligibilityScanner, Checks Gmail for a recent confirmation email from an ATS for the given company a, ApplicationExecutor, Determines if a job should be skipped BEFORE launching the browser.         Retu

### Community 58 - "BaseBackend"
Cohesion: 0.19
Nodes (10): BackendFactory, Globally instantiates the active backend based on configuration/environment vari, BaseBackend, ABC, Any, Executes a search query and returns the raw response dictionary.         This mu, Abstract interface for all discovery backends.     Handles HTTP/Apify/SERP API e, DiscoveryCache (+2 more)

### Community 59 - "GreenhouseDiscoveryPlugin"
Cohesion: 0.13
Nodes (4): GreenhouseInspector, GreenhouseParser, GreenhouseDiscoveryPlugin, Normalize a Greenhouse URL to the board-level URL.          Input examples:

### Community 60 - "ProviderCapabilities"
Cohesion: 0.12
Nodes (5): ApifyProvider, BaseProvider, CompanyCareersProvider, BaseProvider, ProviderCapabilities

### Community 61 - "BaseQueue"
Cohesion: 0.17
Nodes (7): BaseQueue, ABC, Acknowledges successful processing, removing the item from the queue., Negative acknowledgment. Returns the item to the queue or pushes to a DLQ/Retry, Abstract interface for queues to allow swapping SQLite for Redis/SQS in producti, The orchestrator that continuously polls the Company Registry for due crawls, Scheduler

### Community 62 - "IntentFilter"
Cohesion: 0.19
Nodes (11): JIECandidateProfile, _build_jie_profile(), IntentFilter, Any, CandidateProfile, Return 0.0–1.0 based on how well the job title matches target roles., Score a batch of jobs that already passed HardRejectFilter.          Returns:, Legacy interface used by scratch scripts.         Returns (passed, rejected, met (+3 more)

### Community 63 - "CredentialFactory"
Cohesion: 0.27
Nodes (7): CredentialFactory, Any, Executes the platform-specific search logic and returns (raw_jobs, warnings)., Overrides DiscoveryConnector.discover to implement Search Escalation Policy., Base class for all Search Connectors (Pipeline B1).     Owns Adaptive Escalation, SearchConnectorBase, ConnectorResult

### Community 64 - "workday.py"
Cohesion: 0.23
Nodes (8): AshbyConnector, AshbyJSONConnector, WorkdayConnector, WorkdayJSONConnector, CrawlPolicy, CrawlPriority, Enum, Returns the crawl policy configuration for this connector.

### Community 65 - "ATSProvider"
Cohesion: 0.15
Nodes (4): ATSProvider, ProviderRegistry, Protocol, VerificationResult

### Community 66 - "EndpointIdentity"
Cohesion: 0.23
Nodes (3): BaseATSProvider, EndpointIdentity, ClientSession

### Community 67 - "pipeline.py"
Cohesion: 0.19
Nodes (10): discover_contacts(), Phase 1 - Contact Discovery (Safe Job Discovery Architecture)     Order:     1., discover_email(), Phase 4 - Email Discovery     Tries GetProspect first (mocked if no key), falls, Executes the V0.1 Referral Engine flow:     1. Safe Job Discovery (Max 5 contact, run_referral_engine(), Phase 2 - Profile Intelligence     Uses Apify LinkedIn Profile Scraper.     For, scrape_profile() (+2 more)

### Community 68 - "SourceRegistry"
Cohesion: 0.14
Nodes (8): DefaultInspector, Fallback validator for ATS providers that don't have a dedicated API validator y, Instantiates and registers a SourceAdapter., Instantiates and registers a SourceInspector., Returns the adapter by name, e.g., 'greenhouse, Returns the inspector by name, or a DefaultInspector if none is registered., Central registry for ATS plugins and inspectors., SourceRegistry

### Community 69 - "SmartRecruitersDiscoveryPlugin"
Cohesion: 0.14
Nodes (4): Extracts the SmartRecruiters board slug and hits their API.         e.g., https:, SmartRecruitersInspector, Any, SmartRecruitersDiscoveryPlugin

### Community 70 - "LandingPageResolver"
Cohesion: 0.16
Nodes (8): LandingPageResolver, LandingPageResolver — Sprint C1B  Responsibility: Given a generic /careers page, Return the ATS name if the URL itself is a recognized ATS endpoint., Scan full HTML for ATS URL patterns.         Returns (resolved_url, ats_name, co, Result of a LandingPageResolver.resolve() call., Resolves a generic careers page URL → ATS endpoint.      Pipeline:         URL →, :param http_client: An async-compatible HTTP client with a `.fetch(method, url)`, ResolvedEndpoint

### Community 71 - "RAGClient"
Cohesion: 0.21
Nodes (5): AutoapplyEngine, Maps the recommended resume string from the DB to an absolute resume path, RAGClient, Dynamically generates chunks from yash_master_profile.md., Retrieves Top 5 chunks using BM25, then reranks, returning the Final Top chunks.

### Community 72 - "discovery_providers.py"
Cohesion: 0.26
Nodes (8): DiscoveryProvider, EndpointCandidatePayload, KnownDatasetDiscoverer, ABC, Any, Generates candidates from known dataset mappings (e.g. from the benchmark CSV)., Generates candidates by guessing common ATS subdomains for the company., RegexDiscoverer

### Community 73 - "DiscoverySession"
Cohesion: 0.19
Nodes (6): ConnectorRegistry, ConnectorManager, Any, Runs all healthy connectors in parallel.         Returns a list of raw payloads., Orchestrates the healthy connectors supplied by the registry.     Connectors ret, DiscoverySession

### Community 74 - "IndeedProvider"
Cohesion: 0.18
Nodes (4): IndeedProvider, BaseProvider, QueryGenerator, Centralizes search query generation for job boards and search providers.

### Community 75 - "CrawlStateMachine"
Cohesion: 0.24
Nodes (3): CrawlState, CrawlStateMachine, Any

### Community 76 - "compilerOptions"
Cohesion: 0.17
Nodes (11): compilerOptions, esModuleInterop, forceConsistentCasingInFileNames, module, moduleResolution, noEmit, skipLibCheck, strict (+3 more)

### Community 77 - "database.py"
Cohesion: 0.33
Nodes (5): DataFrame, fetch_query(), fetch_table(), get_db_connection(), get_latest_heartbeats()

### Community 78 - "JobCanonicalizer"
Cohesion: 0.21
Nodes (6): JobCanonicalizer, Any, Lowercases, strips punctuation, and normalizes common title variations., Normalizes location string, prioritizing 'remote' if present., Normalizes messy job data and generates deterministic fingerprints for deduplica, Takes a raw scraped job and returns a normalized payload with fingerprint.

### Community 79 - "LinkedinConnector"
Cohesion: 0.21
Nodes (3): LinkedinConnector, Any, ConnectorCapabilityMatrix

### Community 80 - "SourceManager"
Cohesion: 0.23
Nodes (5): Handles cloning, pulling, and incremental sync of Git repositories., RepositoryManager, Runs sync across all sources and returns list of files that need parsing., Orchestrates generic sync over multiple specific source managers (Git, CSV, etc., SourceManager

### Community 82 - "SQLiteReservationRepository"
Cohesion: 0.21
Nodes (4): ABC, Any, SQLiteReservationRepository, WorkReservationRepository

### Community 83 - "RetryManager"
Cohesion: 0.21
Nodes (4): HealthScorer, Exponential backoff: 1hr -> 6hr -> 1day -> 7days, Computes a 0-100 score based on metrics., RetryManager

### Community 85 - "CuratedRepositoryProvider"
Cohesion: 0.24
Nodes (4): MarkdownJobParser, Parses Markdown tables to extract Job information., CuratedRepositoryProvider, BaseProvider

### Community 86 - "BaseWorker"
Cohesion: 0.22
Nodes (4): Iterates through registered adapters to find one that can handle the URL., BaseWorker, Any, Generic worker loop that continuously pulls tasks from a BaseQueue,     finds th

### Community 87 - "ScanBudgetManager"
Cohesion: 0.20
Nodes (6): PriorityScheduler, Yields target companies for the Job Discovery Engine based on their dynamic prio, Any, Prevents unnecessary scans by balancing daily API budgets against company priori, Creates a scan plan to maximize discovery quality without burning credits., ScanBudgetManager

### Community 88 - "SearchBackend"
Cohesion: 0.22
Nodes (7): BingBackend, DuckDuckGoBackend, Abstract search backend. Returns raw URLs from a search engine., Currently rate-limited (202 anti-bot). Kept as dormant fallback., Currently broken (primp impersonation failure). Kept as dormant fallback., SearchBackend, YahooBackend

### Community 93 - "registry_generator.py"
Cohesion: 0.33
Nodes (8): init_db(), upsert_contacted_email(), init_registry_db(), Pings ATS providers to find if slug exists., run(), slugify(), verify_ats(), sync_sent_emails()

### Community 95 - "EventBus"
Cohesion: 0.20
Nodes (6): EventBus, Any, A lightweight, SQLite-backed event bus for decoupling the Discovery pipeline., Publishes an event to the system_events table., Registers an in-process handler for an event type., Polls the system_events table for PENDING events and executes their registered h

### Community 96 - "JDExtractor"
Cohesion: 0.33
Nodes (4): JDExtractor, Any, StructuredJob, Requirement

### Community 103 - "InMemoryEventBus"
Cohesion: 0.24
Nodes (5): InMemoryEventBus, Any, Registers a listener for a specific event type., Emits an event to all registered listeners asynchronously., A lightweight, pragmatic in-memory event bus for local development and single-ma

### Community 107 - "DuckDuckGoSearchProvider"
Cohesion: 0.24
Nodes (4): DuckDuckGoSearchProvider, Protocol, SearchProvider, SearchProviderRegistry

### Community 108 - "SearchTask"
Cohesion: 0.36
Nodes (5): SearchTask, MatchEngine, MatchResult, Any, Evaluates opportunities and returns a transparent dual-score with a recommendati

### Community 109 - "JobProvider"
Cohesion: 0.27
Nodes (5): JobProvider, ABC, Abstract base class for all job providers., Discover jobs and return a list of job dictionaries.         Expected keys:, CSVProvider

### Community 110 - "CompanyIntake"
Cohesion: 0.25
Nodes (5): CompanyIntake, Any, Extracts companies from opportunities and processes them through the intake pipe, Checks if company exists. If NO, inserts as P3 NEW.         (Note: In a full pro, Company Discovery as a side-effect of Market Search (Pipeline B).     Extracts c

### Community 113 - "ranking.py"
Cohesion: 0.36
Nodes (8): apply_ranking_engine(), classify_role(), get_feedback_scores(), infer_experience(), parse_date(), Connection, rank_opportunity(), Pre-calculate feedback scores to avoid SQLite lock errors.

### Community 114 - "ApplicationExecutorInterface"
Cohesion: 0.28
Nodes (6): ApplicationExecutorInterface, ABC, Any, Submits the tailored application via Playwright., Processes the Strategy Queue., STRICT BOUNDARY: Do NOT implement or connect this interface for Sprint 1.6.

### Community 115 - "EnrichmentLayer"
Cohesion: 0.33
Nodes (3): EnrichmentLayer, Check if we have exceeded daily/monthly Apify constraints., Uses Apify to find Hiring Managers and Recruiters.

### Community 116 - "run_batch.py"
Cohesion: 0.39
Nodes (7): check_duplicate_run(), Checks if we have already sent the daily limit of emails today.     Returns True, run_daily_outreach(), get_scheduler_state(), job(), save_scheduler_state(), start_scheduler()

### Community 117 - "DuckDuckGoProvider"
Cohesion: 0.28
Nodes (4): DuckDuckGoProvider, Searches DDG for recruiters at a specific company via LinkedIn X-Ray., Searches DDG for potential hiring managers at a specific company., Searches DDG for the company's official career page.

### Community 118 - "ProfileParser"
Cohesion: 0.31
Nodes (4): ProfileParser, Extracts content starting from `section_prefix` until the next `## SECTION` or E, Extracts a specific project block from Section 4 based on a keyword.         Exa, Builds the minimal context for template generation.         Includes ONLY the Sp

### Community 119 - "2026 Artificial Intelligence Internship & New Grad Positions"
Cohesion: 0.25
Nodes (7): 2026 Artificial Intelligence Internship & New Grad Positions, 2026 USA AI Internships :books::eagle:, FAANG+, International Positions :globe_with_meridians:, Other, Quant, USA Positions :eagle:

### Community 122 - "CSVImportProvider"
Cohesion: 0.32
Nodes (4): CSVImportProvider, Any, BaseProvider, Reads candidate companies from a local CSV file.         Format expected: Compan

### Community 123 - "2026 International AI Internships :books::globe_with_meridians:"
Cohesion: 0.29
Nodes (6): 2026 International AI Internships :books::globe_with_meridians:, FAANG+, International Positions :globe_with_meridians:, Other, Quant, USA Positions :eagle:

### Community 124 - "2026 International AI New Grad Positions :mortar_board::globe_with_meridians:"
Cohesion: 0.29
Nodes (6): 2026 International AI New Grad Positions :mortar_board::globe_with_meridians:, FAANG+, International Positions :globe_with_meridians:, Other, Quant, USA Positions :eagle:

### Community 125 - "2026 USA AI New Graduate Positions :mortar_board::eagle:"
Cohesion: 0.29
Nodes (6): 2026 USA AI New Graduate Positions :mortar_board::eagle:, FAANG+, International Positions :globe_with_meridians:, Other, Quant, USA Positions :eagle:

### Community 126 - "JobRegistry"
Cohesion: 0.33
Nodes (3): Job, JobRegistry, Takes a snapshot of crawled jobs and compares them to existing jobs in the regis

### Community 127 - "deduplicator.py"
Cohesion: 0.38
Nodes (6): verify_top_opportunities(), generate_canonical_id(), is_ats_url(), process_job(), Adds a job to the database or updates it if it's a duplicate.     Prioritizes AT, Generates a canonical ID for a job.     Prefers ATS Job ID from the URL if extra

### Community 128 - "provider_effectiveness.py"
Cohesion: 0.33
Nodes (3): adjust_provider_priority(), Historical outcomes automatically adjust provider scan priority.     Providers p, record_application_outcome()

### Community 129 - "ResumeSelector"
Cohesion: 0.38
Nodes (3): Any, Returns (resume_path, resume_variant)         In the future, this will call Resu, ResumeSelector

### Community 130 - "EligibilityEngine"
Cohesion: 0.33
Nodes (3): EligibilityDecision, EligibilityEngine, Deterministic V2 rule-based bouncer.     Determines if an opportunity is ELIGIBL

### Community 131 - ".pop"
Cohesion: 0.29
Nodes (4): Any, Pushes an item onto the queue. Returns item ID., Pops an item from the queue, establishing a lock/lease., Pushes multiple items onto the queue. Returns list of item IDs.

### Community 133 - "JobLifecycleManager"
Cohesion: 0.33
Nodes (3): JobLifecycleManager, Any, Processes an array of raw jobs, computes hashes, and updates lifecycle states.

### Community 134 - "IngestionEngine"
Cohesion: 0.38
Nodes (3): IngestionEngine, Removes legal entities for deduplication., Scans the source folder and ingests all CSVs and Excels.

### Community 135 - "EmailListener"
Cohesion: 0.33
Nodes (3): EmailListener, Connects in read-only mode and searches for a recent OTP from a specific domain., Connects in read-only mode and searches for a magic verification link.

### Community 136 - "github_jobs.py"
Cohesion: 0.43
Nodes (6): extract_text_from_md_link(), extract_url_from_md_link(), fetch_github_jobs(), parse_markdown_table(), Fetches job listings from dynamically discovered GitHub repositories via Search, Parses both HTML tables and raw Markdown tables.

### Community 137 - ".validate"
Cohesion: 0.29
Nodes (5): Any, Ensures bullets aren't deleted, order is intact, page limit., Ensures the LLM did not hallucinate new facts., SemanticValidator, StructuralValidator

### Community 138 - "PROJECT INTELLIGENCE DATABASE"
Cohesion: 0.33
Nodes (5): AI Data Analyst Agent, Echo Pod — AI Stillness Companion, PROJECT INTELLIGENCE DATABASE, Semantic Document Search — GDSC IIT Roorkee, YAAR — AI Behavioral Companion

### Community 139 - "CompiledRegexCache"
Cohesion: 0.40
Nodes (3): CompiledRegexCache, ConfigLoader, Any

### Community 140 - "DiscoveryDeduplicator"
Cohesion: 0.33
Nodes (4): DiscoveryDeduplicator, Any, Groups opportunities by Company and Job Title (or some strong similarity)., Deduplicates Opportunities by merging alternative apply sources rather than dele

### Community 141 - "DiscoveryQueue"
Cohesion: 0.33
Nodes (4): DiscoveryQueue, Any, Fetches the next batch of companies to scan based on priority and lifecycle., Manages the priority queue for company discovery (P0 -> P1 -> P2 -> P3).     Ens

### Community 142 - "company_pipeline.py"
Cohesion: 0.47
Nodes (3): CompanyPipeline, PipelineResult, Orchestrates the discovery and verification of boards for a single company.

### Community 143 - "CareerLinkExpansionStrategy"
Cohesion: 0.33
Nodes (3): CareerLinkExpansionStrategy, Candidate, Replaces the generic BFS crawler. Extracts targeted internal links (About, Caree

### Community 144 - "CareerPageFingerprintStrategy"
Cohesion: 0.33
Nodes (3): CareerPageFingerprintStrategy, Candidate, Scans the raw HTML of the company homepage and career pages for embedded     ATS

### Community 145 - "RobotsTxtStrategy"
Cohesion: 0.33
Nodes (3): Candidate, Parses /robots.txt to find Sitemap directives and blocked /jobs paths., RobotsTxtStrategy

### Community 146 - "SitemapStrategy"
Cohesion: 0.33
Nodes (3): Candidate, Parses /sitemap.xml to find careers, jobs, and external ATS URLs., SitemapStrategy

### Community 147 - "DiscoveryEngine"
Cohesion: 0.40
Nodes (3): DiscoveryEngine, Removes legal entities for deduplication., Ingests companies from multiple sources, deduplicates, and incrementally updates

### Community 148 - "ApplicationPrioritizer"
Cohesion: 0.33
Nodes (3): ApplicationPrioritizer, Any, Evaluates opportunities relative to one another to produce the daily application

### Community 149 - ".generate_strategy"
Cohesion: 0.53
Nodes (4): Any, CandidateFit, StructuredJob, RewritePlanner

### Community 150 - "QuestionClassifier"
Cohesion: 0.40
Nodes (3): QuestionClassifier, Classifies application form questions and determines if they are safe to auto-an, Returns: 'DETERMINISTIC', 'ESCALATE', or 'UNKNOWN'

### Community 151 - "SubmissionVerifier"
Cohesion: 0.40
Nodes (3): Page, Verifies if an application was successfully submitted using a weighted confidenc, SubmissionVerifier

### Community 154 - "RateLimiter"
Cohesion: 0.40
Nodes (3): Any, RateLimiter, Handles per-provider request limits, exponential backoff, retries, jitter,

### Community 155 - "GenericParserFallback"
Cohesion: 0.40
Nodes (3): GenericParserFallback, Executes the fallback chain to extract jobs from a generic careers page., A shared parsing fallback chain to be used when stateless ATS connectors fail.

### Community 156 - ".get_all_providers"
Cohesion: 0.40
Nodes (3): BaseProvider, Registers a BaseProvider subclass., Returns instantiated versions of all registered providers.

### Community 158 - ".generate_market_tasks"
Cohesion: 0.40
Nodes (4): Any, Platform-Agnostic Search Planner.     Generates pure Market Discovery intents ba, Generates canonical Market Searches., SearchPlanner

### Community 159 - "BaseDiscoverySource"
Cohesion: 0.40
Nodes (3): BaseDiscoverySource, Any, Interface for all Opportunity Discovery Sources.     Sources are strictly respon

### Community 162 - "profile_learner.py"
Cohesion: 0.83
Nodes (3): load_profile(), run_learner(), save_profile()

### Community 168 - "ranking_engine.py"
Cohesion: 0.50
Nodes (3): Candidate, rank_candidate(), Returns a sortable tuple representing the strength of the evidence.     Python s

## Knowledge Gaps
- **95 isolated node(s):** `name`, `version`, `type`, `description`, `build` (+90 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Config` connect `Config` to `provider_effectiveness.py`, `LLMRouter`, `database.py`, `setup_logger`, `application_worker.py`, `JobBoardProvider`, `DiscoveryQueue`, `add_or_update_lead`, `ProfileManager`, `ATSRegistry`, `ApifyManager`, `OpportunitySeed`, `ApplicationExecutor`, `pipeline.py`, `RAGClient`, `DiscoverySession`, `database.py`, `registry_generator.py`, `EventBus`, `ranking.py`, `EnrichmentLayer`, `run_batch.py`, `ProfileParser`, `JobRegistry`, `deduplicator.py`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Why does `get_connection()` connect `get_connection` to `DiscoveryContext`, `Config`, `import_company_datasets.py`, `ATSRegistry`, `CompatCursor`, `.transition`, `seed_discovery_worker.py`, `Telemetry`, `main.py`, `db.py`, `job_board_worker.py`, `SQLiteReservationRepository`, `is_postgres`, `job_crawler_worker.py`, `EndpointIntelligenceService`, `scheduler.py`, `settings.py`, `BaseQueue`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `setup_logger()` connect `setup_logger` to `provider_effectiveness.py`, `LLMRouter`, `Config`, `database.py`, `application_worker.py`, `github_jobs.py`, `SourceConnector`, `add_or_update_lead`, `run_pipeline.py`, `rie_pipeline.py`, `ProfileManager`, `profile_learner.py`, `StructuredJob`, `OpportunitySeed`, `career_discovery.py`, `ApplicationResult`, `BaseBackend`, `pipeline.py`, `database.py`, `settings.py`, `registry_generator.py`, `JobProvider`, `ranking.py`, `run_batch.py`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `Config` (e.g. with `EmailConfirmationChecker` and `AutoapplyEngine`) actually correct?**
  _`Config` has 52 INFERRED edges - model-reasoned connections that need verification._
- **Are the 37 inferred relationships involving `SourceInspector` (e.g. with `AshbyInspector` and `BreezyInspector`) actually correct?**
  _`SourceInspector` has 37 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `type` to the rest of the system?**
  _95 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SourceInspector` be split into smaller, more focused modules?**
  _Cohesion score 0.06110154905335628 - nodes in this community are weakly interconnected._