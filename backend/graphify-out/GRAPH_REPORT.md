# Graph Report - backend  (2026-07-18)

## Corpus Check
- 481 files · ~958,792 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3483 nodes · 7739 edges · 210 communities (175 shown, 35 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 906 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3c7a5ff2`
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
- backfill_metrics.py
- verify_scale.py
- LeverSignature
- WorkableSignature
- WorkdaySignature
- SessionRepository
- RedisKeys
- ProfileParser
- MigrationRepository
- EligibilityRuleProvider
- .promote_endpoints_batch
- MetricsRepository
- SourceAggregator
- jobs.py
- ProviderRepository
- init_mass_execution_schema.py
- CareerEndpointRepository
- HealthScorer
- SmartRecruitersConnector
- get_repository_health
- get_version

## God Nodes (most connected - your core abstractions)
1. `Config` - 119 edges
2. `setup_logger()` - 112 edges
3. `SourceInspector` - 78 edges
4. `get_connection()` - 56 edges
5. `is_postgres()` - 53 edges
6. `LLMRouter` - 50 edges
7. `HttpClient` - 48 edges
8. `DiscoveryContext` - 46 edges
9. `RepositoryManager` - 44 edges
10. `Credential` - 43 edges

## Surprising Connections (you probably didn't know these)
- `test_embedding_providers()` --calls--> `get_embedding_provider()`  [EXTRACTED]
  tests/test_vector.py → src/ai/embeddings/provider.py
- `ProviderDefinition` --uses--> `ApifyManager`  [INFERRED]
  src/common/credential_provider.py → src/integrations/apify_manager.py
- `TestRepositories` --uses--> `RepositoryManager`  [INFERRED]
  tests/test_repositories.py → src/core/repositories/manager.py
- `DiscoveryResult` --uses--> `SourceInspector`  [INFERRED]
  src/discovery/pipeline/fallback_models.py → src/discovery/inspectors/base_inspector.py
- `test_jie_pipeline()` --calls--> `JDExtractor`  [EXTRACTED]
  tests/test_jie.py → src/discovery/jie/extractor.py

## Import Cycles
- 1-file cycle: `src/discovery/pipeline/sources.py -> src/discovery/pipeline/sources.py`

## Communities (210 total, 35 thin omitted)

### Community 0 - "SourceInspector"
Cohesion: 0.12
Nodes (13): AshbyInspector, ABC, e.g., 'greenhouse', 'ashby' - must match the adapter's source_name, Abstract interface for verifying that a detected URL is a valid,     functioning, SourceInspector, GreenhouseInspector, LeverInspector, WorkdayInspector (+5 more)

### Community 1 - "LLMRouter"
Cohesion: 0.06
Nodes (21): ProfileManager, Returns the fact value. Uses dynamic JSON if confidence >= 70 or human_verified, Manages the candidate profile used for form automation. Self-Learning V2., LocationResolver, QuestionClassifier, QuestionEngine, Deterministic salary calculation based on location and role.         Targeting 7, Generates and normalizes an answer using Candidate RAG + LLM with Deterministic (+13 more)

### Community 2 - "DiscoveryContext"
Cohesion: 0.08
Nodes (23): ContinuousDiscoveryEngine, DiscoveryDB, Any, ReplayCache, Logger, DiscoveryBudget, AshbyDiscoveryPlugin, Any (+15 more)

### Community 3 - "Config"
Cohesion: 0.05
Nodes (25): datetime, Returns (verification_status, http_status), verify_top_opportunities(), verify_url(), EmailConfirmationChecker, ATSDetector, Retrieves an OTP code and detailed forensics.     Returns:         {, retrieve_greenhouse_otp() (+17 more)

### Community 4 - "database.py"
Cohesion: 0.07
Nodes (30): clean_contacts(), add_discovery_source(), add_to_company_registry(), add_to_opportunity_cache(), get_active_greenhouse_slugs(), get_all_contacted_emails(), get_all_uncontacted_scored_leads(), get_connection() (+22 more)

### Community 5 - "setup_logger"
Cohesion: 0.06
Nodes (23): dotenv, analyze_failure(), generate_discovery_failure_report(), Returns (Failure Reason, Next Action), get_role_counts(), print_apify_analytics(), print_funnel_metrics(), print_source_attribution() (+15 more)

### Community 6 - "get_connection"
Cohesion: 0.10
Nodes (12): Settings, DetectorRegistry, Central registry of ATS detectors., CleanupWorker, BaseWorker, _extract_domain(), _normalize_company_id(), Ensure a minimal company identity exists for verification payloads. (+4 more)

### Community 7 - "application_worker.py"
Cohesion: 0.08
Nodes (16): FeedbackTracker, outcome should be 'INTERVIEW' or 'REJECTED', ApplicationHandler, Native Playwright handler for Wellfound 'Easy Apply' flows., WellfoundHandler, MatchEngine, Enforces the V1.4 target distribution by percentiles:         Top 5% -> 90+, Evaluates discovered jobs against the Candidate Intelligence DB     Returns a sc (+8 more)

### Community 8 - "fallback_models.py"
Cohesion: 0.06
Nodes (44): _categorize(), collect_evidence(), Candidate, rank_candidates(), RankedCandidate, CandidateEvaluator — Sprint C1B  Evidence Collection → Scoring → Ranking → Thres, Assign a coarse category purely from URL structure. No network calls., Collects all available structural evidence for a candidate URL.     This does NO (+36 more)

### Community 9 - "Last updated: June 2026"
Cohesion: 0.05
Nodes (42): AVAILABILITY, COMPENSATION, Experience 1: OrangeLabs (Feb 2026 – Apr 2026), Experience 2: ScoreMe Solutions (May 2025 – Jun 2025), Experience 3: Bharat Electronics Limited (Jun 2025 – Jul 2025), Final Year B.Tech, IIT Roorkee (Chemical Engineering, 2022–2026), Formatting Rules (Override Everything), LANGUAGES (+34 more)

### Community 10 - "JobBoardProvider"
Cohesion: 0.14
Nodes (11): Google Jobs Pipeline B provider.  Wraps GoogleJobsProvider using the JobBoardPro, JobBoardProvider, JobBoardResult, ABC, Pipeline B — Job Board Provider base interface.  All Pipeline B providers implem, Returned by every JobBoardProvider.discover() call., Abstract base for all Pipeline B providers.      Implementations must:       - R, Unique provider name, e.g. 'linkedin', 'google_jobs'. (+3 more)

### Community 11 - "models.py"
Cohesion: 0.15
Nodes (16): AshbyJSONConnector, Board, ConnectorCapability, FetchResult, Connector, CrawlPriority, ABC, Any (+8 more)

### Community 12 - "AnalyticsRepository"
Cohesion: 0.18
Nodes (18): AnalyticsRepository, get_analytics_repo(), get_ats_drilldown(), get_data_quality(), get_dead_boards(), get_duplicate_companies(), get_funnel(), get_lineage() (+10 more)

### Community 13 - "credential_provider.py"
Cohesion: 0.11
Nodes (18): AuthException, CredentialProvider, ProviderDefinition, Exception, RateLimitException, Abstract Base Class for Credential Management, ABC, SearchResult (+10 more)

### Community 14 - "DefaultFreshnessStrategy"
Cohesion: 0.09
Nodes (16): ConnectorRegistry, Runtime registry for all Discovery Connectors.     Reads config, instantiates cl, AmazonJSONConnector, BambooHRConnector, GreenhouseConnector, GreenhouseJSONConnector, LeverConnector, LeverJSONConnector (+8 more)

### Community 15 - "SourceOrchestrator"
Cohesion: 0.13
Nodes (7): CompanySource, GitHubConnector, OfficialAccelConnector, OfficialPeakXVConnector, OfficialYCConnector, Any, YCAPIConnector

### Community 16 - "db.py"
Cohesion: 0.09
Nodes (12): json_extract(), JobRepository, Any, Load jobs from DB → HardRejectFilter → JIE (IntentFilter) → Sort → Paginate → Re, JobRepository, BaseRepository, Takes the new canonical jobs, diffs against existing active jobs for the board/c, HardRejectFilter (+4 more)

### Community 17 - "job_board_worker.py"
Cohesion: 0.12
Nodes (15): CompanyResolver, Resolves StandardJob.company + apply_url to an existing company_id.      Resolut, Args:             db_path: Path to the SQLite database.             queue:   A S, JobBoardNormalizer, Pipeline B — Job Board Normalizer.  Converts a StandardJob (from any job board p, Stable 16-char id derived from the canonical apply URL., Converts StandardJob → CanonicalJob.      Uses CompanyResolver to map the compan, _url_hash() (+7 more)

### Community 18 - "job_crawler_worker.py"
Cohesion: 0.10
Nodes (16): run_production(), ConnectorExecutor, ExecutionResult, Executes a single session under the concurrency semaphore., JobValidator, Returns (valid_jobs, invalid_records)., Validates jobs before persistence to prevent corrupt data., Returns a list of error messages. Empty list means valid. (+8 more)

### Community 19 - "is_postgres"
Cohesion: 0.20
Nodes (5): BaseRepository, Override in subclasses to create schema., DiscoveryCandidate, DiscoveryCandidateRepository, BaseRepository

### Community 20 - "SourceConnector"
Cohesion: 0.17
Nodes (10): ABC, SourceConnector, SourceConnectorRegistry, AccelConnector, BaseResumableConnector, PeakXVConnector, Any, Helper to scrape real startups from TechCrunch VC tags to bypass VC Cloudflare p (+2 more)

### Community 21 - "get-jobs.ts"
Cohesion: 0.12
Nodes (23): main(), parseIssueBody(), HEADERS, MARKERS, TABLES, __dirname, __filename, generateMarkdownTable() (+15 more)

### Community 22 - "LeverDiscoveryPlugin"
Cohesion: 0.12
Nodes (9): BoardIdentity, GreenhouseBoardIdentity, LeverBoardIdentity, StandardBoardIdentity, WorkdayBoardIdentity, AshbyParser, GreenhouseParser, LeverParser (+1 more)

### Community 23 - "RawJob"
Cohesion: 0.21
Nodes (12): CanonicalJob, JobIdentity, RawJob, Convert a StandardJob to a CanonicalJob.          Args:             job:      St, AshbyNormalizer, GreenhouseNormalizer, JobNormalizer, LeverNormalizer (+4 more)

### Community 24 - "PlanningContext"
Cohesion: 0.17
Nodes (16): PlanningContextBuilder, Any, EndpointIntelligence, PlanningContext, PlanningContextBuilder, Any, RuntimeState, CrawlPlanner (+8 more)

### Community 25 - "add_or_update_lead"
Cohesion: 0.12
Nodes (20): add_or_update_lead(), get_lead(), get_lead_by_hr_email(), Upserts a lead based on company_name, update_lead_state(), PipelineStage, Enum, transition_state() (+12 more)

### Community 26 - "run_pipeline.py"
Cohesion: 0.11
Nodes (22): init_db(), build_pipeline(), # TODO: Load Candidate Context Logic, run(), PipelineContext, PipelineStage, ABC, Executes the pipeline stage and updates the context. (+14 more)

### Community 27 - "rie_pipeline.py"
Cohesion: 0.15
Nodes (15): CandidateFit, EditOperation, RewriteStrategy, StructuredJob, Any, ResumeEditor, Any, CandidateFit (+7 more)

### Community 28 - "package.json"
Cohesion: 0.07
Nodes (26): @actions/core, @actions/github, author, dependencies, @actions/core, @actions/github, dotenv, @supabase/supabase-js (+18 more)

### Community 29 - "GreenhouseHandler"
Cohesion: 0.05
Nodes (24): EarlyEligibilityScanner, Checks Gmail for a recent confirmation email from an ATS for the given company a, ApplicationExecutor, GreenhouseHandler, Page, Executes the Greenhouse application workflow.         Returns a dict with status, Iterates over custom fields. Returns True if all successfully answered and safe, Fix 4: Scan all required fields for empty or invalid values. (+16 more)

### Community 30 - "Credential"
Cohesion: 0.19
Nodes (7): Credential, CredentialExhaustedException, CredentialTelemetry, InMemoryCredentialProvider, Any, Wraps the existing ApifyManager logic for persistent tracking.     Never stores, SQLiteCredentialProvider

### Community 31 - "DiscoveryPlugin"
Cohesion: 0.08
Nodes (12): DiscoveryPlugin, ABC, Any, Name of the ATS provider (e.g. 'greenhouse', 'workday'), Domains used to construct URL guesses., URL fragments or text used to identify this ATS., Parse a URL into an identity and confidence score., Returns the specific inspector for this ATS. (+4 more)

### Community 33 - "ProfileManager"
Cohesion: 0.06
Nodes (44): chunk_document(), Chunker, estimate_tokens(), Any, Split markdown content by heading boundaries (#, ##, ###), fall back to plain te, Split plain text into chunks based on paragraph breaks and token limits, with ov, Rough estimation of token count based on standard English word-to-token ratio (1, EmbeddingProvider (+36 more)

### Community 34 - "StructuredJob"
Cohesion: 0.20
Nodes (14): IntentFilter — wraps JIE (JDExtractor + FitAnalyzer) to score jobs.  This is the, CandidateProfile, FitAnalyzer, BaseModel, CandidateFit, StructuredJob, CandidateFit, FitDetail (+6 more)

### Community 35 - "ATSRegistry"
Cohesion: 0.09
Nodes (11): ATSRegistry, FastPathRegistry, Any, VerificationResult, Attempts to register a batch of companies directly as ACTIVE in the ats_registry, Attempts to register a company directly as ACTIVE in the ats_registry using trus, Any, Normalize a Workday URL to the tenant board URL.          Input examples: (+3 more)

### Community 36 - "import_company_datasets.py"
Cohesion: 0.16
Nodes (24): NamedTuple, CompanyRecord, deduplicate(), domain_to_id(), extract_domain(), fetch_url(), infer_website(), insert_records() (+16 more)

### Community 37 - "Response"
Cohesion: 0.07
Nodes (7): DatabaseAdapter, PostgreSQLAdapter, ABC, Any, SQLiteAdapter, Any, _TxConnectionWrapper

### Community 38 - "CompatCursor"
Cohesion: 0.07
Nodes (16): JobRepository, Any, BaseRepository, Convenient entry‑point for all repository objects.      Example usage::, RepositoryManager, MetricsRepository, BaseRepository, CleanupRepository (+8 more)

### Community 39 - ".transition"
Cohesion: 0.18
Nodes (8): get_row_dict(), main(), _enqueue_batch(), migrate_existing_companies(), is_postgres(), MigrationRunner, BaseRepository, SnapshotRepository

### Community 40 - "seed_discovery_worker.py"
Cohesion: 0.10
Nodes (19): Pipeline B — Company Resolver.  Resolves a free-text company name + apply URL fr, Enum, str, ReasonCode, Stage, Status, Telemetry, ABC (+11 more)

### Community 41 - "ApifyManager"
Cohesion: 0.13
Nodes (6): LinkedInJobsProvider, ApifyManager, Registers credential IDs into SQLite., Returns (db_id, credential_id) of the least used active credential., Returns (ApifyClient, key_id) for the least-used active credential.         tier, ApifyProvider

### Community 42 - "ATSDetector"
Cohesion: 0.09
Nodes (10): ATSDetector, BambooHRSignature, GreenhouseSignature, iCIMSSignature, JazzHRSignature, ABC, The canonical ID of the ATS provider in ats_providers., Return the confidence score of the match (0-100). (+2 more)

### Community 43 - "Telemetry"
Cohesion: 0.33
Nodes (5): EndpointCandidate, EndpointRankingEngine, BaseModel, Ranks available candidates for a given company based on confidence score., Retrieves all active or discovered candidates for a company, sorted by confidenc

### Community 44 - "main.py"
Cohesion: 0.11
Nodes (4): Any, table_exists(), get_db(), get_repos()

### Community 45 - "HttpClient"
Cohesion: 0.10
Nodes (13): ConnectorRepository, Any, ICompanyRepository, ICompanyStateRepository, IConnectorRepository, IJobRepository, IMigrationRepository, IProviderRepository (+5 more)

### Community 46 - "OpportunitySeed"
Cohesion: 0.19
Nodes (9): BaseDiscoveryProvider, OpportunitySeed, ABC, Interface for all discovery providers.      Every provider must return a list of, CompanyIntelligenceProvider, InternetSearchProvider, QueryGenerator, Returns a list of strategy dictionaries to be executed. (+1 more)

### Community 47 - "ATSDetector"
Cohesion: 0.13
Nodes (7): AshbyDetector, ATSDetector, DetectorFactory, GreenhouseDetector, LeverDetector, ABC, Returns (is_match, valid_slug)

### Community 48 - "DiscoveryConnector"
Cohesion: 0.15
Nodes (12): CredentialFactory, LinkedinConnector, Any, Any, Executes the platform-specific search logic and returns (raw_jobs, warnings)., Overrides DiscoveryConnector.discover to implement Search Escalation Policy., Base class for all Search Connectors (Pipeline B1).     Owns Adaptive Escalation, SearchConnectorBase (+4 more)

### Community 49 - "career_discovery.py"
Cohesion: 0.15
Nodes (10): ATSDetector, CareerDiscoveryEngine, ClientSession, Manages optional fallbacks to search engines like Google/LinkedIn if the main cr, Detects ATS endpoints using DOM signatures, URL structures, and Regex fallbacks., Returns (ATS_Name, board_token, confidence), The core async worker logic to discover a company's career page., SearchProviderManager (+2 more)

### Community 50 - "SourceAdapter"
Cohesion: 0.06
Nodes (22): DefaultInspector, Fallback validator for ATS providers that don't have a dedicated API validator y, BoardIngestionEngine, BoardRegistry, ABC, Any, e.g., 'greenhouse', 'lever, e.g., 'v1.0' - Used to determine if jobs need re-parsing. (+14 more)

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
Cohesion: 0.13
Nodes (10): ConfidenceFormula, EndpointIntelligenceService, Any, Called when an endpoint candidate fails verification (e.g. 404, invalid signatur, Called by JobCrawlerWorker after a successful sync., Called by JobCrawlerWorker after a sync fails., confidence = provider_weight + historical_success + freshness + evidence - histo, Centralized service for managing confidence, health, and history of ATS endpoint (+2 more)

### Community 55 - "base_provider.py"
Cohesion: 0.17
Nodes (15): Candidate, PipelineResult, DiscoveryStrategy, ABC, Unique name for this strategy, e.g. 'website_crawler'., Abstract interface for Discovery Strategies.      A strategy's sole job is to re, ProviderRegistry, Factory for instantiating Discovery Providers.     Follows the plugin architectu (+7 more)

### Community 56 - "WebsiteCrawlerStrategy"
Cohesion: 0.14
Nodes (8): _extract_all_urls(), _is_career_link(), Candidate, Find internal pages worth visiting (career pages + about/company)., From a depth-1 page, find links that specifically look like career pages., Pull every URL-shaped string from the full HTML source., Heuristic: does this anchor look like a career/jobs page?, WebsiteCrawlerStrategy

### Community 57 - "ApplicationExecutor"
Cohesion: 0.08
Nodes (11): fetch_jwks(), get_public_key(), Any, Retrieve JWKS public keys directly from Supabase project., Retrieve public key matching kid parameter with lazy refresh., Validate critical environment variables are present., Settings, CloudflareR2Adapter (+3 more)

### Community 58 - "BaseBackend"
Cohesion: 0.19
Nodes (10): BackendFactory, Globally instantiates the active backend based on configuration/environment vari, BaseBackend, ABC, Any, Executes a search query and returns the raw response dictionary.         This mu, Abstract interface for all discovery backends.     Handles HTTP/Apify/SERP API e, DiscoveryCache (+2 more)

### Community 59 - "GreenhouseDiscoveryPlugin"
Cohesion: 0.15
Nodes (3): GreenhouseDiscoveryPlugin, Any, Normalize a Greenhouse URL to the board-level URL.          Input examples:

### Community 60 - "ProviderCapabilities"
Cohesion: 0.11
Nodes (9): ApifyProvider, BaseProvider, StandardJob, CompanyCareersProvider, BaseProvider, GenericCareersProvider, BaseProvider, BaseProvider (+1 more)

### Community 61 - "BaseQueue"
Cohesion: 0.07
Nodes (19): BaseQueue, ABC, Any, Pushes an item onto the queue. Returns item ID., Pops an item from the queue, establishing a lock/lease., Acknowledges successful processing, removing the item from the queue., Negative acknowledgment. Returns the item to the queue or pushes to a DLQ/Retry, Pushes multiple items onto the queue. Returns list of item IDs. (+11 more)

### Community 62 - "IntentFilter"
Cohesion: 0.19
Nodes (11): JIECandidateProfile, _build_jie_profile(), IntentFilter, Any, CandidateProfile, Return 0.0–1.0 based on how well the job title matches target roles., Score a batch of jobs that already passed HardRejectFilter.          Returns:, Legacy interface used by scratch scripts.         Returns (passed, rejected, met (+3 more)

### Community 63 - "CredentialFactory"
Cohesion: 0.24
Nodes (18): BrowserSearchSource, Fallback discovery mechanism using a secondary Exa search strategy.     (Replace, DiscoveryContext, Candidate, DiscoverySource, Evidence, ProbeResult, SourceResult (+10 more)

### Community 64 - "workday.py"
Cohesion: 0.19
Nodes (5): AshbyConnector, WorkdayConnector, WorkdayJSONConnector, CrawlPolicy, Returns the crawl policy configuration for this connector.

### Community 65 - "ATSProvider"
Cohesion: 0.13
Nodes (4): ATSProvider, ProviderCapabilities, ProviderRegistry, Protocol

### Community 66 - "EndpointIdentity"
Cohesion: 0.09
Nodes (5): BaseATSProvider, EndpointIdentity, LeverProvider, ClientSession, WorkableProvider

### Community 67 - "pipeline.py"
Cohesion: 0.18
Nodes (7): Pipeline B — Job Board Provider Registry.  The worker calls JobBoardRegistry.loa, # TODO: from src.discovery.providers.wellfound_board_provider import WellfoundBo, # TODO: from src.discovery.providers.indeed_board_provider import IndeedBoardPro, Instantiate all registered providers, skip those that are unavailable         (e, _registered_classes(), LinkedInBoardProvider, Pipeline B adapter over the existing LinkedInJobsProvider.

### Community 68 - "SourceRegistry"
Cohesion: 0.28
Nodes (3): GoogleJobsBoardProvider, Pipeline B adapter over the existing GoogleJobsProvider., GoogleJobsProvider

### Community 69 - "SmartRecruitersDiscoveryPlugin"
Cohesion: 0.17
Nodes (4): SmartRecruitersInspector, SmartRecruitersParser, Any, SmartRecruitersDiscoveryPlugin

### Community 70 - "LandingPageResolver"
Cohesion: 0.12
Nodes (17): CompanyState, Enum, str, SchedulerState, WorkerState, CrawlHistoryRepository, Any, BaseRepository (+9 more)

### Community 71 - "RAGClient"
Cohesion: 0.12
Nodes (15): generate_daily_queue(), Generates the daily application queue by isolating the top 20 HIGH priority jobs, AutoapplyEngine, Maps the recommended resume string from the DB to an absolute resume path, RAGClient, Dynamically generates chunks from yash_master_profile.md., Retrieves Top 5 chunks using BM25, then reranks, returning the Final Top chunks., compile_and_count_pages() (+7 more)

### Community 72 - "discovery_providers.py"
Cohesion: 0.25
Nodes (9): DiscoveryProvider, DiscoveryRegistry, EndpointCandidatePayload, KnownDatasetDiscoverer, ABC, Any, Generates candidates from known dataset mappings (e.g. from the benchmark CSV)., Generates candidates by guessing common ATS subdomains for the company. (+1 more)

### Community 73 - "DiscoverySession"
Cohesion: 0.19
Nodes (6): ConnectorRegistry, ConnectorManager, Any, Runs all healthy connectors in parallel.         Returns a list of raw payloads., Orchestrates the healthy connectors supplied by the registry.     Connectors ret, DiscoverySession

### Community 74 - "IndeedProvider"
Cohesion: 0.16
Nodes (4): IndeedProvider, BaseProvider, QueryGenerator, Centralizes search query generation for job boards and search providers.

### Community 75 - "CrawlStateMachine"
Cohesion: 0.24
Nodes (3): CrawlState, CrawlStateMachine, Any

### Community 76 - "compilerOptions"
Cohesion: 0.17
Nodes (11): compilerOptions, esModuleInterop, forceConsistentCasingInFileNames, module, moduleResolution, noEmit, skipLibCheck, strict (+3 more)

### Community 77 - "database.py"
Cohesion: 0.16
Nodes (6): DataFrame, ApiClient, fetch_query(), fetch_table(), get_latest_heartbeats(), Any

### Community 78 - "JobCanonicalizer"
Cohesion: 0.21
Nodes (6): JobCanonicalizer, Any, Lowercases, strips punctuation, and normalizes common title variations., Normalizes location string, prioritizing 'remote' if present., Normalizes messy job data and generates deterministic fingerprints for deduplica, Takes a raw scraped job and returns a normalized payload with fingerprint.

### Community 79 - "LinkedinConnector"
Cohesion: 0.19
Nodes (4): BaseRepository, RepositoryManager centralizes repository access and transaction handling. It own, Any, SchemaInspector

### Community 80 - "SourceManager"
Cohesion: 0.23
Nodes (5): Handles cloning, pulling, and incremental sync of Git repositories., RepositoryManager, Runs sync across all sources and returns list of files that need parsing., Orchestrates generic sync over multiple specific source managers (Git, CSV, etc., SourceManager

### Community 81 - "NegativeCache"
Cohesion: 0.11
Nodes (5): For regression safety: creates a backup of the current ats_registry table., NegativeCache, Any, SearchCache, fetch_metrics()

### Community 82 - "SQLiteReservationRepository"
Cohesion: 0.21
Nodes (4): ABC, Any, SQLiteReservationRepository, WorkReservationRepository

### Community 85 - "CuratedRepositoryProvider"
Cohesion: 0.21
Nodes (4): MarkdownJobParser, Parses Markdown tables to extract Job information., CuratedRepositoryProvider, BaseProvider

### Community 87 - "ScanBudgetManager"
Cohesion: 0.19
Nodes (6): PriorityScheduler, Yields target companies for the Job Discovery Engine based on their dynamic prio, Any, Prevents unnecessary scans by balancing daily API budgets against company priori, Creates a scan plan to maximize discovery quality without burning credits., ScanBudgetManager

### Community 88 - "SearchBackend"
Cohesion: 0.15
Nodes (3): CompatConnection, CompatCursor, Any

### Community 89 - "WorkableProvider"
Cohesion: 0.15
Nodes (5): CompanyRepository, Any, BaseRepository, Centralizes the logic for determining the table names for provider-specific regi, RegistryResolver

### Community 90 - "scheduler.py"
Cohesion: 0.13
Nodes (7): WorkerType, Any, BaseRepository, WorkerRepository, get_worker_type(), PipelineScheduler, WorkerRegistry

### Community 91 - "settings.py"
Cohesion: 0.29
Nodes (6): _domain_slug(), _extract_domain(), Push a discovery payload into discovery_queue so Pipeline A will         detect, Extract bare domain from any URL, stripping www., Stable, collision-resistant company_id from a domain., Resolve company_name + apply_url to a company_id.          Returns:

### Community 93 - "registry_generator.py"
Cohesion: 0.33
Nodes (8): init_db(), upsert_contacted_email(), init_registry_db(), Pings ATS providers to find if slug exists., run(), slugify(), verify_ats(), sync_sent_emails()

### Community 94 - "WellfoundConnector"
Cohesion: 0.10
Nodes (8): Response, BreezySignature, LeverSignature, Analyzes the response body/headers/URL to determine if it is this ATS., If this is the ATS, extract or format the canonical URL., Returns the first matching ATSDetector., WorkableSignature, WorkdaySignature

### Community 95 - "EventBus"
Cohesion: 0.20
Nodes (6): EventBus, Any, A lightweight, SQLite-backed event bus for decoupling the Discovery pipeline., Publishes an event to the system_events table., Registers an in-process handler for an event type., Polls the system_events table for PENDING events and executes their registered h

### Community 96 - "JDExtractor"
Cohesion: 0.33
Nodes (4): JDExtractor, Any, StructuredJob, Requirement

### Community 97 - "BreezyDiscoveryPlugin"
Cohesion: 0.15
Nodes (4): BreezyInspector, BreezyParser, BreezyDiscoveryPlugin, Any

### Community 98 - "JobviteDiscoveryPlugin"
Cohesion: 0.15
Nodes (4): JobviteInspector, JobviteParser, JobviteDiscoveryPlugin, Any

### Community 99 - "RecruiteeDiscoveryPlugin"
Cohesion: 0.15
Nodes (4): RecruiteeInspector, RecruiteeParser, Any, RecruiteeDiscoveryPlugin

### Community 100 - "TeamtailorDiscoveryPlugin"
Cohesion: 0.15
Nodes (4): TeamtailorInspector, TeamtailorParser, Any, TeamtailorDiscoveryPlugin

### Community 101 - "WorkableDiscoveryPlugin"
Cohesion: 0.17
Nodes (4): WorkableInspector, WorkableParser, Any, WorkableDiscoveryPlugin

### Community 103 - "InMemoryEventBus"
Cohesion: 0.20
Nodes (8): Any, Dual-Backend Queue implementation.     Delegates to Redis (via QueueManager) in, SQLiteQueue, get_connection(), Gets value from cache., Any, Dequeues an item from a Redis list (blocking pop).         Returns None if queue, Enqueues an item into a Redis list.

### Community 106 - "LeverProvider"
Cohesion: 0.19
Nodes (17): HTTPAuthorizationCredentials, complete_onboarding(), EducationItem, ExperienceItem, get_me(), OnboardingPayload, BaseModel, Upload resume file to Cloudflare R2 and return the storage key/url. (+9 more)

### Community 107 - "DuckDuckGoSearchProvider"
Cohesion: 0.24
Nodes (4): DuckDuckGoSearchProvider, Protocol, SearchProvider, SearchProviderRegistry

### Community 108 - "SearchTask"
Cohesion: 0.43
Nodes (3): MatchEngine, Any, Evaluates opportunities and returns a transparent dual-score with a recommendati

### Community 109 - "JobProvider"
Cohesion: 0.27
Nodes (5): JobProvider, ABC, Abstract base class for all job providers., Discover jobs and return a list of job dictionaries.         Expected keys:, CSVProvider

### Community 110 - "CompanyIntake"
Cohesion: 0.25
Nodes (5): CompanyIntake, Any, Extracts companies from opportunities and processes them through the intake pipe, Checks if company exists. If NO, inserts as P3 NEW.         (Note: In a full pro, Company Discovery as a side-effect of Market Search (Pipeline B).     Extracts c

### Community 111 - "IndeedConnector"
Cohesion: 0.14
Nodes (6): load_generic_credentials(), load_google_credentials(), Pairs GOOGLE_SEARCH_API_KEY_N with GOOGLE_CX_N, Loads keys like PREFIX, PREFIX_1, PREFIX_2, etc., IndeedConnector, Any

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
Cohesion: 0.09
Nodes (18): get_cached_intelligence(), set_cached_intelligence(), calculate_priority_score(), run_intelligence_engine(), ProjectSelector, Returns (Project, [Rejected_Project], Reasoning, Confidence), EmailClient, Exception (+10 more)

### Community 117 - "DuckDuckGoProvider"
Cohesion: 0.28
Nodes (4): DuckDuckGoProvider, Searches DDG for recruiters at a specific company via LinkedIn X-Ray., Searches DDG for potential hiring managers at a specific company., Searches DDG for the company's official career page.

### Community 118 - "ProfileParser"
Cohesion: 0.23
Nodes (8): CacheManager, Sets value in cache with a TTL (default 1 hour)., Checks if key is present in cache., Removes key from cache., HeartbeatManager, LockManager, QueueManager, RedisClient

### Community 119 - "2026 Artificial Intelligence Internship & New Grad Positions"
Cohesion: 0.25
Nodes (7): 2026 Artificial Intelligence Internship & New Grad Positions, 2026 USA AI Internships :books::eagle:, FAANG+, International Positions :globe_with_meridians:, Other, Quant, USA Positions :eagle:

### Community 121 - "BoardRegistry"
Cohesion: 0.19
Nodes (10): discover_contacts(), Phase 1 - Contact Discovery (Safe Job Discovery Architecture)     Order:     1., discover_email(), Phase 4 - Email Discovery     Tries GetProspect first (mocked if no key), falls, Executes the V0.1 Referral Engine flow:     1. Safe Job Discovery (Max 5 contact, run_referral_engine(), Phase 2 - Profile Intelligence     Uses Apify LinkedIn Profile Scraper.     For, scrape_profile() (+2 more)

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
Cohesion: 0.18
Nodes (6): run_smoke_test(), Retrieves list of active registered workers., Registers or updates a worker with a heartbeat TTL., Releases a distributed lock., Acquires a distributed lock using Redis.         Returns True if acquired, False, StorageService

### Community 128 - "provider_effectiveness.py"
Cohesion: 0.33
Nodes (3): adjust_provider_priority(), Historical outcomes automatically adjust provider scan priority.     Providers p, record_application_outcome()

### Community 129 - "ResumeSelector"
Cohesion: 0.38
Nodes (3): Any, Returns (resume_path, resume_variant)         In the future, this will call Resu, ResumeSelector

### Community 130 - "EligibilityEngine"
Cohesion: 0.33
Nodes (3): EligibilityDecision, EligibilityEngine, Deterministic V2 rule-based bouncer.     Determines if an opportunity is ELIGIBL

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
Cohesion: 0.24
Nodes (9): PipelineStateManager, Any, Exception, Executes a lifecycle transition for a batch of companies atomically., Executes a lifecycle transition atomically within a single database transaction., TransitionError, test_fast_path_transitions(), test_invalid_transitions() (+1 more)

### Community 151 - "SubmissionVerifier"
Cohesion: 0.32
Nodes (4): DashboardRepository, Any, BaseRepository, Returns the size of the queue.

### Community 152 - "CredentialTelemetry"
Cohesion: 0.17
Nodes (11): connector_metrics(), coverage_report(), health_check(), pipeline_metrics(), Health & Observability API GET /api/v1/health          - system health check GET, Basic health probe for Railway / uptime monitors., Full pipeline funnel: Discovery → Verification → Crawl → Jobs., Per-ATS connector reliability stats. (+3 more)

### Community 154 - "RateLimiter"
Cohesion: 0.40
Nodes (3): Any, RateLimiter, Handles per-provider request limits, exponential backoff, retries, jitter,

### Community 155 - "GenericParserFallback"
Cohesion: 0.08
Nodes (14): Register an instantiated connector., DiscoveryConnector, ABC, Any, Stateless interface for all Discovery Connectors.     All state (sessions, retri, Defines what this connector is capable of doing., One-time setup (e.g. loading API keys). Raises Exception if config is missing., Verifies API endpoints are reachable or credentials are valid. (+6 more)

### Community 156 - ".get_all_providers"
Cohesion: 0.40
Nodes (3): BaseProvider, Registers a BaseProvider subclass., Returns instantiated versions of all registered providers.

### Community 157 - "hash_job"
Cohesion: 0.29
Nodes (3): CompanyStateRepository, Any, BaseRepository

### Community 158 - ".generate_market_tasks"
Cohesion: 0.40
Nodes (4): Any, Platform-Agnostic Search Planner.     Generates pure Market Discovery intents ba, Generates canonical Market Searches., SearchPlanner

### Community 159 - "BaseDiscoverySource"
Cohesion: 0.40
Nodes (3): BaseDiscoverySource, Any, Interface for all Opportunity Discovery Sources.     Sources are strictly respon

### Community 162 - "profile_learner.py"
Cohesion: 0.20
Nodes (4): DiscoveryRepository, Any, BaseRepository, Imports a single seed from CSV and returns True if a new company was inserted.

### Community 164 - "BambooHRSignature"
Cohesion: 0.25
Nodes (6): HardRejectResult, Any, CandidateProfile, Filter a batch of jobs. Returns (passed, rejected, rejection_counts).          r, Extract minimum experience required from:           1. jie column already stored, Evaluate a single job dict against the candidate profile.          Args:

### Community 168 - "ranking_engine.py"
Cohesion: 0.13
Nodes (9): Validates the URL using the provider's native API., Extracts the Lever board slug and hits their API.         e.g., https://jobs.lev, Extracts the SmartRecruiters board slug and hits their API.         e.g., https:, Validates the Workable board by trying to hit their API.         e.g., https://a, Validates the Workday board by trying to hit the CXS jobs API.         e.g., htt, InspectionResult, Candidate, rank_candidate() (+1 more)

### Community 177 - "verify_scale.py"
Cohesion: 0.27
Nodes (4): Queue, BoardRepository, BaseRepository, Scheduler

### Community 188 - "LeverSignature"
Cohesion: 0.22
Nodes (3): Any, QueryBuilder, A lightweight query builder that prevents repositories from hardcoding     SQL p

### Community 190 - "WorkdaySignature"
Cohesion: 0.33
Nodes (3): OutboxRepository, Any, BaseRepository

### Community 191 - "SessionRepository"
Cohesion: 0.28
Nodes (4): Any, BaseRepository, SessionRepository, Pulls ACTIVE endpoints from the registry that are due for a job crawl,         c

### Community 193 - "ProfileParser"
Cohesion: 0.31
Nodes (4): ProfileParser, Extracts content starting from `section_prefix` until the next `## SECTION` or E, Extracts a specific project block from Section 4 based on a keyword.         Exa, Builds the minimal context for template generation.         Includes ONLY the Sp

### Community 194 - "MigrationRepository"
Cohesion: 0.36
Nodes (3): MigrationRepository, Any, BaseRepository

### Community 195 - "EligibilityRuleProvider"
Cohesion: 0.36
Nodes (4): EligibilityRule, EligibilityRuleProvider, Parses and serves Eligibility Rules from YAML.     Separates rule logic from the, Returns the version string and the ordered list of pre-compiled rules.

### Community 196 - ".promote_endpoints_batch"
Cohesion: 0.29
Nodes (4): Connection, VerificationResult, Promotes a VerificationResult to ACTIVE status.         Compares endpoint_hash t, Promotes a batch of endpoints in a single transaction.         Each item in batc

### Community 199 - "jobs.py"
Cohesion: 0.60
Nodes (5): get_board_jobs(), get_job(), get_jobs(), get_sync_history(), RepositoryManager

### Community 200 - "ProviderRepository"
Cohesion: 0.47
Nodes (3): ProviderRepository, Any, BaseRepository

### Community 201 - "init_mass_execution_schema.py"
Cohesion: 0.50
Nodes (3): get_csv_providers(), init_schema(), migrate()

### Community 202 - "CareerEndpointRepository"
Cohesion: 0.40
Nodes (4): CareerEndpointRepository, BaseRepository, Connection, Updates status, health_status, confidence, failure_reason, and last_verified_at

## Knowledge Gaps
- **94 isolated node(s):** `name`, `version`, `type`, `description`, `build` (+89 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `setup_logger()` connect `setup_logger` to `provider_effectiveness.py`, `LLMRouter`, `Config`, `database.py`, `application_worker.py`, `github_jobs.py`, `SourceConnector`, `add_or_update_lead`, `run_pipeline.py`, `rie_pipeline.py`, `GreenhouseHandler`, `ProfileManager`, `StructuredJob`, `.transition`, `OpportunitySeed`, `career_discovery.py`, `ApplicationResult`, `BaseBackend`, `RAGClient`, `database.py`, `registry_generator.py`, `JobProvider`, `ranking.py`, `run_batch.py`, `BoardRegistry`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Why does `Config` connect `Config` to `provider_effectiveness.py`, `LLMRouter`, `database.py`, `setup_logger`, `application_worker.py`, `DiscoveryQueue`, `add_or_update_lead`, `GreenhouseHandler`, `ATSRegistry`, `ApifyManager`, `OpportunitySeed`, `ApplicationExecutor`, `ProviderCapabilities`, `ProfileParser`, `EligibilityRuleProvider`, `SourceRegistry`, `RAGClient`, `DiscoverySession`, `registry_generator.py`, `EventBus`, `ranking.py`, `EnrichmentLayer`, `run_batch.py`, `BoardRegistry`, `JobRegistry`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `is_postgres()` connect `.transition` to `ProfileManager`, `DiscoveryContext`, `Config`, `import_company_datasets.py`, `ATSRegistry`, `CompatCursor`, `.promote_endpoints_batch`, `seed_discovery_worker.py`, `Telemetry`, `main.py`, `get_version`, `NegativeCache`, `job_crawler_worker.py`, `is_postgres`, `SQLiteReservationRepository`, `EndpointIntelligenceService`, `QuestionClassifier`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `Config` (e.g. with `EmailConfirmationChecker` and `AutoapplyEngine`) actually correct?**
  _`Config` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 37 inferred relationships involving `SourceInspector` (e.g. with `AshbyInspector` and `BreezyInspector`) actually correct?**
  _`SourceInspector` has 37 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `type` to the rest of the system?**
  _94 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SourceInspector` be split into smaller, more focused modules?**
  _Cohesion score 0.12380952380952381 - nodes in this community are weakly interconnected._