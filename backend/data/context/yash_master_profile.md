# YASH KHERWAL — MASTER CANDIDATE INTELLIGENCE FILE
# Final Year B.Tech, IIT Roorkee (Chemical Engineering, 2022–2026)
# Optimised for: Resume Generation, Tailoring, Job Matching, Project Selection, Email Writing
# Last updated: June 2026

---

## SECTION 1: IDENTITY SNAPSHOT

**Name:** Yash Kherwal
**Degree:** B.Tech Chemical Engineering, IIT Roorkee (2022–2026)
**Location:** Ghaziabad / targeting Bangalore · Hyderabad · Gurugram · Noida · Mumbai · Remote
**Contact:** +91 9891148156 | yash.kherwal78@gmail.com
**LinkedIn:** linkedin.com/in/yash-kherwal-944497254
**CPI:** ~5.6 — NEVER include on resume, never mention. Strategy is to impress humans before CPI comes up.

**One-line identity:**
IIT Roorkee engineer who builds end-to-end AI systems independently, treats job search as an engineering problem, and thinks in systems and failure modes before features.

**Target Roles (ranked by preference):**
1. AI Product Manager / Associate Product Manager (APM)
2. Founder's Office AI (direct co-founder access, 0-to-1 ownership)
3. Applied AI Engineer / GenAI Engineer / LLM Engineer
4. ML Engineer / SDE with AI focus

**Target Companies:**
Mid-size funded Indian startups (Razorpay, CRED, Groww, Meesho, PhonePe, ShareChat) + product companies (InMobi, EA, JPMorgan, Zimmer Biomet, Auric AI, EXL, Pine Labs, Sprinklr, Vedantu)

**Anti-targets:** IT services companies (TCS, Infosys, Wipro) — avoid

---

## SECTION 2: HOW YASH THINKS

**Problem-Solving Approach:**
- Identifies the upstream root cause before designing solutions. Example: ScoreMe — didn't just build a classifier, identified that "manual review of every document" was the systemic bottleneck first.
- Frames problems as systems with defined failure modes. Always asks: what happens when this breaks?
- Thinks in product decisions, not just engineering decisions. Naturally articulates tradeoffs with explicit rationale (latency vs accuracy, automation coverage vs data quality, retraining vs inference-time personalisation).
- Data-first but not data-paralysed. Makes explicit prioritisation decisions (RICE, Knapsack) and can defend ranking.
- Willing to accept suboptimal accuracy for significantly lower complexity when reliability matters more.

**How He Learns:**
- Builds to learn. Does not study then build. Builds, hits a wall, then goes deep.
- Used AI tools during building but follows a strategy of reverse-engineering projects to answer interview questions authentically.
- Iterates fast under pressure.

**How He Handles Ambiguity:**
- Structures it immediately. Infers target positioning without being told.
- Does not wait for complete information. Ships a version, iterates.

**Communication Style:**
- Direct, curious, builder-minded, practical.
- Dislikes corporate language, buzzwords, fake enthusiasm, over-selling.
- Avoids phrases like "passionate about," "great fit," "exciting opportunity," "cutting-edge."
- If an email sounds like a cover letter, it does not sound like Yash.

---

## SECTION 3: EXPERIENCE INTELLIGENCE

### Experience 1: OrangeLabs (Feb 2026 – Apr 2026)
**Title on Resume:** Product Manager Intern (later updated to AI Engineer Intern on some versions)
**Company type:** EdTech ERP platform for schools and colleges

**What Yash worked on:**
- CCTV-based automated attendance (computer vision pipeline → ERP sync)
- AI-generated personalised lecture pipeline (teacher voice/likeness cloning for student-facing content)
- n8n ERP workflow automation (weaker signal, de-emphasised)

**Reality:** Friend's company. Yash was involved in 0-to-1 product ideation for both flagship products. Work was real but informal/collaborative rather than structured employment.
**Honest depth:** Studied stack post-internship. Has certificate titled "AI Engineer." Bullets are directionally accurate but implementation depth is moderate. Interview prep required on: YOLO/DeepFace for attendance, Wav2Lip/SadTalker for video synthesis.

**Best used for:** AI Engineer, ML Engineer, EdTech product roles, PM roles (0-to-1 signal)
**Do not use for:** Pure backend SDE roles, finance/banking roles

---

### Experience 2: ScoreMe Solutions (May 2025 – Jun 2025)
**Title:** Software Development Intern
**Company type:** Fintech — credit scoring, PDF document processing

**What Yash built:**
- Two-stage ML classification pipeline: rule-based pre-filter → Random Forest classifier
- Confidence calibration layer: low-confidence predictions quarantined from credit scoring pipeline
- Tesseract OCR + PDFBox fallback for scanned/handwritten inputs

**Reality:** Genuine engineering internship. Built and shipped a real ML classification pipeline. Most technically defensible internship.
**Why it matters:** Shows real fintech data pipeline thinking — failure mode awareness (silent misclassification), production-grade confidence thresholding, fallback design.

**Interview talking points:** Why two-stage instead of one model; why confidence thresholding matters in credit contexts; OCR fallback design decision; precision-recall tradeoff; prioritised false negative reduction (misclassification into credit scoring is worse than over-routing to human review)

**Best used for:** ML Engineer, fintech SDE, Data Science, any role valuing production ML thinking
**Do not use for:** Pure PM roles

---

### Experience 3: Bharat Electronics Limited (Jun 2025 – Jul 2025)
**Title:** Engineering Intern
**Company type:** Defense PSU — radar systems

**What Yash built:**
- Binary stream parser for ASTERIX CAT048 radar protocol (EUROCONTROL spec)
- Decoded variable-length optional-field packet structures
- Concurrent ingestion with backpressure handling

**Reality:** Genuine engineering internship. EUROCONTROL ASTERIX CAT048 is a real standard. Can explain binary parsing, variable-length optional fields, concurrent queue design.
**Why it matters:** Shows low-level systems thinking, protocol parsing, concurrency — strong signal for SDE roles.

**Best used for:** SDE roles, backend-heavy roles, systems companies (Auric AI)
**Do not use for:** Pure product/PM roles where it adds noise

---

## SECTION 4: PROJECT INTELLIGENCE

### Project 1: YAAR — AI Behavioral Companion

**Elevator Pitch:** A zero-input AI companion for Gen Z in Tier 2/3 India that learns your personality from how you react to content — not what you tell it — and gets more "you" over time. Primary revenue is contextual native brand integration.

**Stack:** React Native, LLM APIs (Gemini Flash), FastAPI, shared_preferences, EAS Build

**Origin:** Identified that social media platforms optimise for passive consumption — dopamine without emotional ownership. Designed YAAR as the inverse: a system that reflects you back to yourself.

**Problem Being Solved:** Gen Z in Tier 2/3 India has limited access to self-expression platforms that feel personal. Existing apps treat them as audiences, not individuals. Most digital products focus heavily on content generation when personalization is actually the bigger problem.

**Key Technical Decisions:**
- Preference engine tracks 3 personality dimensions (humour tolerance, self-awareness index, reaction intensity) from tap reactions — no retraining, purely inference-time via dynamic prompt construction
- Output variance deliberately preserved (not minimised) to prevent staleness
- Server-side state persistence across sessions

**Key Product Decisions:**
- Brand integration framed as behavioral state-triggered suggestion, not ad placement
- Identity card share mechanic designed as viral acquisition loop (deep-linked, friend sees teaser, gets own output)
- Monetisation: Free (50 reactions/day) vs Premium (₹49/mo) with brand integration as primary
- North star: D7 retention; DAU/WAU as health check

**What This Says About Yash:** He ships. He thinks about retention mechanics, growth loops, and monetisation at product design time — not as afterthoughts. Understands Gen Z consumer psychology for India's Tier 2/3 market.

**Engineering framing (for ML/SDE resumes):** Persistent personality memory system, 3-dimension metric vector, inference-time LLM personalisation via dynamic prompt construction, server-side state persistence across sessions.

**Resume Highlight:** "Shipped Android APK (React Native + EAS Build) — preference engine tracks 3 personality dimensions from tap reactions, delivering identity-calibrated LLM outputs from first session without retraining; sub-2s streamed response latency"

**Interview Story:** Walk through the preference engine design — why no retraining (latency and cost), why variance is a feature not a bug (staleness kills retention), why brand integration works (behavioral state = purchase intent signal)

**Best Roles:** Consumer AI PM, AI Product at startups, Founder's Office AI, any role asking for "shipped product" evidence
**Best Companies:** Meesho, ShareChat, Josh, Moj, early-stage consumer AI startups, Vedantu, Unacademy (engagement layer)

---

### Project 2: Echo Pod — AI Stillness Companion

**Elevator Pitch:** An on-device AI product that intercepts idle moments on your phone and redirects you toward reflection instead of more scrolling — not by blocking, by competing for the same moment.

**Origin:** Diagnosed that screen blocker apps have 25% first-session churn because they fight behavior instead of rewiring reward. Designed around interception and redirection.

**Key Product Insight:** People don't fear boredom — they fear unmediated thought. The problem isn't attention span, it's discomfort avoidance. People don't have an information problem — they have a time and attention problem.

**Key Technical Decision:** On-device inference (not cloud) — zero round-trip latency is a product constraint, not just an engineering preference. A 3-second ambient trigger window does not tolerate cloud round-trip.

**What This Says About Yash:** Diagnoses the failure mode of competitors before designing. Thinks about why existing solutions fail, not just what the solution should do.

**Resume Highlight:** "Diagnosed 25% first-session churn on screen blockers; designed 3-layer AI UX (ambient 3s trigger → on-device voice AI → daily stillness score) with on-device inference as a deliberate zero-latency product decision"

**Best Roles:** Consumer wellness tech PM, AI interaction design roles, Founder's Office
**Best Companies:** Headspace-style wellness, mental health tech, any EdTech with engagement problems
**Do NOT use for:** Engineering-heavy roles (no substantial engineering substance)

---

### Project 3: AI Data Analyst Agent

**Elevator Pitch:** A 5-agent LangGraph system where non-technical users type a question in plain English and get a data analysis result in under 60 seconds — no SQL, no engineer required.

**Stack:** Python, LangGraph, CrewAI, n8n (orchestration), MCP (tool standardisation), FastAPI, Docker (sandboxed execution), AWS EC2

**Architecture:** Query Planner → Code Writer → Executor → Error Fixer → Insight Generator

**Key Technical Decisions:**
- LangGraph for stateful agent workflow (not vanilla LangChain) — explicit state management per agent
- Query Planner does intent classification BEFORE generation — eliminates downstream type errors
- n8n as orchestration layer separate from agent logic — non-technical operators can modify routing without redeployment
- MCP to expose tools (files, DBs, APIs) as standardised context — extensible by design
- Error Fixer agent: classify exception → regenerate targeted fix → retry 3x before user escalation (ReAct-style)
- Docker sandbox to isolate LLM-generated code from host

**What This Says About Yash:** Thinks about production constraints at design time. The Error Fixer, sandbox, and n8n decoupling are all failure-mode-first decisions. This is systems thinking, not tutorial execution.

**Resume Highlight:** "Built 5-agent LangGraph workflow — reduced time-to-insight from hours (engineering queue) to under 60s; Error Fixer agent handles autonomous exception recovery (3-attempt retry) before user escalation"

**Interview Story:** Why n8n sits outside agent code (decoupling workflow logic from agent logic), why MCP over hardcoded integrations (extensibility), why Error Fixer pattern (push recovery responsibility into system, not user), why LangGraph over CrewAI (stateful graph execution)

**Best Roles:** AI Engineer, Applied AI Engineer, LLM Engineer, AI PM at technical companies, GenAI tooling
**Best Companies:** EA (EADP), JPMorgan, GCP roles, Auric AI, Pine Labs, Sprinklr, Vedantu
**Do NOT use for:** Pure PM roles, data analyst roles, companies that don't care about agentic systems

---

### Project 4: Semantic Document Search — GDSC IIT Roorkee

**Elevator Pitch:** Rebuilt a 500+ document knowledge base from keyword search to hybrid RAG — users get direct grounded answers instead of a list of documents to manually search.

**Stack:** Python, LangChain, BGE-M3 (embeddings), AstraDB (vector store, ANN indexing), FastAPI, AWS EC2

**Key Technical Decisions:**
- BGE-M3 over Sentence-Transformers: better zero-shot and multilingual retrieval
- Hybrid RAG (dense BGE-M3 + sparse BM25): recall improvement on paraphrased/domain-specific queries where keyword search fails — addresses vocabulary mismatch
- AstraDB for managed ANN indexing — no self-hosted infra overhead
- Decoupled ingestion and serving: corpus updates without serving downtime
- Response groundedness enforced via prompt constraints: outputs anchored to retrieved context, hallucination prevention

**What This Says About Yash:** Diagnoses root causes (vocabulary mismatch, not just "retrieval is bad"). Makes informed model selection decisions. Understands retrieval quality as a product requirement, not just a technical parameter.

**Resume Highlights:**
- Root cause diagnosis before solution
- BGE-M3 multilingual selection rationale
- Decoupled architecture for operational resilience
- Hallucination mitigation via prompt constraints

**Interview Story:** "BM25 was missing semantically identical documents described in different words. Adding dense embeddings wasn't enough — I needed hybrid scoring to handle both vocabulary match and semantic similarity."

**Best Roles:** LLM Engineer, RAG Systems, AI Engineer, Data Scientist (NLP), document intelligence roles
**Best Companies:** Auric AI (multilingual entity resolution), Zimmer Biomet (contract analysis), JPMorgan (unstructured data), InMobi, Sprinklr
**Do NOT use for:** Roles with no NLP/retrieval component

---

### Project 5: CareerAutomated — AI Recruiting Intelligence Platform

**Elevator Pitch:** An autonomous 10-Agent AI platform that finds jobs, researches companies, tailors LaTeX resumes, and submits applications end-to-end with zero human intervention.

**Stack:** Python, Playwright, SQLite, Anthropic/Gemini APIs, RAG (BM25 + Semantic), LangGraph, Streamlit

**Key Technical Decisions:**
- Component-based architecture separating discovery, intelligence, routing, and execution
- Human-in-the-loop review gate for safety before final submission
- Waterfall UI normalization strategy (Exact -> Rules -> Fuzzy) to handle modern custom ATS widgets like React-Select
- Embedding-free RAG using BM25 for zero-cost, high-speed knowledge retrieval
- Strict prompt grounding rules and low-confidence gating to prevent LLM hallucinations on business metrics

**What This Says About Yash:** Thinks in autonomous workflows and agentic safety. Designs systems that map unstructured intent to structured web interactions. Prioritizes robustness (failure handling, waterfall parsing) over pure happy-path execution.

**Resume Highlights:**
- Shipped end-to-end agentic workflow
- Bypassed complex web UI barriers using Playwright
- Implemented human-in-the-loop safety gates
- Custom low-cost BM25 RAG pipeline

**Interview Story:** "Web automation breaks easily. I realized I couldn't just throw LLM outputs at web forms. I had to build a waterfall normalization engine that handled everything from native selects to custom React widgets before it could successfully auto-apply."

**Best Roles:** AI Engineer, Automation Engineer, SDE, Technical PM
**Best Companies:** Any company valuing agentic workflows or internal tooling.

---

### Project 5: SC-MFC Power Optimisation (B.Tech Thesis)

**Elevator Pitch:** End-to-end ML pipeline to predict and optimise power output vs operational cost in Sediment-type Microbial Fuel Cells — Pareto frontier of operating configurations, R² improved from 0.547 (baseline) to 0.963.

**Stack:** Python, TensorFlow/Keras, Scikit-learn, pdfplumber (data extraction)

**Key Technical Decisions:**
- Multi-output ANN (64-32-16 architecture with BatchNorm + Dropout) — not separate models — to capture power-cost interdependency
- Pareto-style random search to surface solution frontier (not single optimal point) — gives researchers decision-relevant output with competing priorities
- Weighted multi-task loss to balance output importance
- KNN imputation over mean imputation for sparse experimental data — preserves local structure
- StandardScaler fitted on training set only — prevents data leakage
- EarlyStopping + ReduceLROnPlateau
- Supervised by Dr. P.P. Kundu

**What This Says About Yash:** Can execute rigorous research-grade ML work. Understands multi-objective optimisation framing. Strong analytical foundation despite non-CS degree.

**Best Roles:** Data Science, ML Engineer (research-adjacent), consulting analytics roles, roles requiring quantitative modelling evidence
**Best Companies:** EXL, Zimmer Biomet, JPMorgan (quantitative), Bain Vector CoE, McKinsey QuantumBlack
**Do NOT use for:** Pure product/PM roles, SDE roles where it adds noise

---

## SECTION 5: PERSONAL PROFILE

### Strengths
1. **Systems architecture thinking** — decomposes complex problems into clean pipelines
2. **Failure mode awareness** — thinks about what breaks before being asked
3. **End-to-end ownership** — ships complete systems independently
4. **Root cause diagnosis** — doesn't treat symptoms
5. **Self-direction** — builds what he needs, including tools to solve his own problems
6. **Communication** — articulates technical decisions clearly and with rationale

### Strongest Technical Skills
- LangGraph-based multi-agent system design
- Hybrid RAG pipeline architecture
- LLM inference-time personalisation (without retraining)
- MCP and n8n workflow orchestration
- FastAPI + Docker + AWS EC2 deployment
- SQL for analytical queries (funnel, cohort, window functions)
- Python (data + backend)
- React Native (shipped to production)
- TensorFlow, Scikit-learn, multi-output regression

### Strongest Product Skills
- User problem diagnosis (identifies root cause before designing)
- Product tradeoff articulation (explicit rationale for every decision)
- Consumer engagement loop design
- Metrics definition and north star selection
- Funnel analysis and drop-off diagnosis
- 0-to-1 product scoping

### Strongest Ownership Signals
- Shipped a working Android APK (YAAR) — rare at fresher level
- Independently scoped and shipped production ML pipeline (ScoreMe)
- Built and deployed full LLM system on AWS EC2 (AI Analyst Agent)
- Led product definition for startup from zero (OrangeLabs)
- B.Tech thesis with R² = 0.963

### Working Style
- High velocity, low ceremony
- Builds first, refines through iteration
- Prefers direct feedback over polite hedging
- Treats job search as an engineering project
- Works well in ambiguous, resource-constrained environments
- Does not need external structure to ship

### Weaknesses (Honest)
- CPI 5.6 — structural disadvantage at companies with hard GPA filters; never mention
- Orange Labs implementation depth is moderate — needs prep before CV/synthesis interview questions
- No explicit GCP/Vertex AI experience — claim only "familiar"
- No LoRA/QLoRA fine-tuning experience — gap for some ML roles
- No Hugging Face hands-on — gap for NLP-heavy roles
- Relatively shallow on formal PM execution (Jira, Confluence, formal Agile ceremonies)
- Some projects built with AI assistance — follow strategy of reverse-engineering for authentic defence
- 0 years official experience — fresher; internships are the counter-argument

---

## SECTION 6: RESUME STRATEGY

### Formatting Rules (Override Everything)
Every resume must use Jake's Resume Format:
- **Font:** 10.5pt
- **Margins:** oddsidemargin -0.55in · textwidth +1.1in · topmargin -0.65in · textheight +1.3in
- `\color{black}\titlerule` with `\vspace{-4pt}` before and `\vspace{-5pt}` after
- `resumeProjectHeading` at `\vspace{-7pt}`
- `resumeItemListStart` with no topsep override
- Section heading: "Technical Skills"
- One page strictly
- Experience before Projects: ALWAYS
- CPI: NEVER included

---

### Strategy 1: AI Product Manager Resume
**Target:** AI APM at Pine Labs, Sprinklr, Vedantu, Peoplebox, AI-native startups

**Projects to Include:**
- AI Data Analyst Agent (leads — strongest AI systems signal)
- Semantic Document Search (retrieval depth)
- YAAR (shipped consumer AI product)
- Echo Pod (AI product design thinking)

**Projects to Exclude:** SC-MFC thesis (research angle, wrong positioning)

**Experience Ordering:** OrangeLabs first → ScoreMe second → BEL third

**Skills Emphasis:** LangGraph, MCP, n8n, Hybrid RAG, Multi-Agent Orchestration, Human-in-the-loop design, Latency-accuracy tradeoffs, PRD writing, funnel analysis, A/B testing, north star metrics

**Key Positioning:** "PM who can build AI systems, not just spec them"

---

### Strategy 2: Product Manager Resume (Non-AI focused)
**Target:** APM at consumer tech — MMT, IDFC, Navi, EazyDiner, ixigo, Newton School

**Projects to Include:**
- YAAR (consumer product shipped, engagement mechanics, monetisation thinking) — leads
- Echo Pod (product design depth, competitive diagnosis)
- AI Data Analyst Agent (technical credibility — 1 bullet only)
- Semantic Document Search (1 bullet only)

**Projects to Exclude:** SC-MFC thesis

**Skills Emphasis:** Consumer product design, funnel analysis, retention, A/B testing, PRD writing, SQL, cohort queries, event tracking schema. Domain row tailored per company (fintech / travel / edtech / food-tech).

**Key Positioning:** "Consumer product thinker with technical depth to work with AI engineers"

---

### Strategy 3: AI / ML Engineer Resume
**Target:** Applied AI Engineer, LLM Engineer, GenAI Engineer roles

**Projects to Include (in order):**
1. AI Data Analyst Agent (leads)
2. Semantic Document Search / Hybrid RAG System
3. YAAR — framed as "Personality-Adaptive LLM System" (NOT consumer product framing)
4. SC-MFC thesis (quantitative ML evidence)

**Projects to Exclude:** Echo Pod (no engineering substance)

**YAAR Engineering Framing:** Persistent personality memory system, 3-dimension metric vector, inference-time LLM personalisation via dynamic prompt construction, server-side state persistence across sessions.

**Skills Emphasis:** LangGraph, LangChain, MCP, Structured Outputs, Agentic Workflows, Hybrid RAG, BGE-M3, Dense+Sparse, AstraDB, ANN Indexing, TensorFlow, Scikit-learn, Multi-Agent Orchestration, Inference Optimisation, FastAPI, Docker, AWS EC2, Stream Processing

**Key Positioning:** "Applied AI engineer who understands production constraints, not tutorial-level developer"

---

### Strategy 4: Data / Analytics Resume
**Target:** Agoda performance marketing, Bain Vector CoE, data science roles

**Projects to Include:**
- SC-MFC thesis (leads — R²=0.963, Pareto optimisation, quantitative modelling)
- AI Data Analyst Agent (SQL execution layer, pipeline design)
- YAAR (A/B test design, behavioral segmentation, retention metrics)
- Semantic Document Search (retrieval model evaluation)

**Projects to Exclude:** Echo Pod

**Skills Emphasis:** Python, SQL (window functions, cohort queries, funnel arithmetic), Pandas, NumPy, TensorFlow, Scikit-learn, A/B testing, regression, multi-objective optimisation, Pareto analysis, LangGraph, Hybrid RAG

**Key Positioning:** "Quantitative thinker from IIT with hands-on ML and analytics execution"

---

### Strategy 5: Software Engineer Resume
**Target:** Backend SDE, systems-heavy roles at InMobi, EA, JPMorgan

**Projects to Include:**
- AI Data Analyst Agent
- Semantic Document Search / Hybrid RAG System
- Recruiting Intelligence Platform (if needed for volume)

**Projects to Exclude:** YAAR (too product-y), SC-MFC (too academic/research), Echo Pod

**Lead Experience With:** BEL (systems, concurrency, protocol parsing — strongest SDE signal) or ScoreMe

**Skills Emphasis:** Python, Java, C++, DSA, concurrency, multi-threading, REST APIs, Docker, AWS, SQL

**Key Positioning:** Engineering fundamentals, clean architecture, production thinking

---

## SECTION 7: EMAIL / OUTREACH INTELLIGENCE

**Core Narrative for Cold Outreach:**
"IIT Roorkee final year who builds AI systems and thinks about them as products — shipped a mobile AI companion, built a multi-agent analytics pipeline, and spent the last year going deep on LLM infrastructure. Looking for a role where I can do both: own product decisions and be technical enough to implement them."

**Tone:** Direct, confident, no apologetics about ChemE background or CPI. Lead with what exists.

**Strongest Hooks by Company Type:**
- AI Startup: YAAR APK (proof of shipping) + AI Analyst Agent (proof of systems)
- Enterprise PM: Research into the company domain (proof of domain preparation)
- Consulting: Structured analytical thinking (proof of framework thinking)
- Engineering: LangGraph + RAG + Docker/EC2 (proof of technical depth)

**What NOT to Do in Outreach:**
- Don't mention CPI
- Don't apologise for ChemE background
- Don't oversell experience years (fresher is fine, own it)
- Don't use generic "passionate about" language
- Don't sound like a cover letter

**Subject Line Formulas:**
- "IIT Roorkee → built a 5-agent autonomous pipeline → applying for [role]"
- "Built a RAG system for [relevant domain] — applying for [role] at [company]"
- "Shipped an Android AI companion app — interested in [PM/APM role]"

---

## SECTION 8: INTERVIEW INTELLIGENCE

### Questions Yash Can Answer Deeply

**On YAAR:**
- "Why no retraining?" → latency and cost; inference-time is sufficient for behavioral steering
- "How does the preference engine work?" → 3 dimensions, weighted delta per reaction type, injected at inference time
- "What's your north star?" → D7 retention; DAU/WAU as health check
- "Why brand integration over pure freemium?" → behavioral state = purchase intent; CPM premium is real

**On AI Data Analyst Agent:**
- "Why LangGraph over CrewAI for orchestration?" → stateful graph execution, explicit state management per agent
- "Why n8n?" → decouples workflow logic from agent code; non-technical modification without redeployment
- "Why MCP?" → standardised tool context across any agent; extensible by design
- "How does the Error Fixer work?" → intercepts exception, classifies type, regenerates targeted fix, retries 3x before escalation

**On ScoreMe:**
- "Why two stages instead of one model?" → deterministic cases don't need ML overhead; isolates failure modes
- "How did you set the threshold?" → precision-recall tradeoff; prioritised false negative reduction (misclassification into credit scoring is worse than over-routing to human review)

**On Hybrid RAG:**
- "Why BGE-M3 over Sentence-Transformers?" → better zero-shot, multilingual, cross-lingual retrieval
- "Why hybrid?" → dense alone misses exact-match queries; sparse alone misses semantic paraphrases
- "What is response groundedness?" → output constrained to retrieved context via prompt; prevents hallucination

**On BEL:**
- "What is ASTERIX CAT048?" → EUROCONTROL standard for binary radar surveillance data — real spec, variable-length optional fields
- "How did you handle concurrency?" → concurrent ingestion queues with backpressure handling

**On SC-MFC thesis:**
- "Why multi-output ANN instead of separate models?" → captures power-cost interdependency
- "Why Pareto search instead of single optimum?" → gives researchers decision-relevant output when priorities compete
- "How did you prevent data leakage?" → StandardScaler fitted on training set only; KNN imputation preserving local structure

### Questions Yash Needs Prep On
- Deep SQL query writing (knows concepts, needs practice writing)
- Formal Agile ceremony details (sprint planning, backlog grooming)
- STAR-format behavioural stories for each experience
- "Describe a time you failed" — honest story needed, not fabricated
- Orange Labs CV/synthesis stack if asked at depth (YOLO/DeepFace, Wav2Lip/SadTalker)

---

## SECTION 9: JOB MATCHING SIGNALS

| Signal in JD | Weight | Notes |
|---|---|---|
| Mentions "agentic AI" or "multi-agent" | HIGH | Direct match to core projects |
| Mentions RAG, vector databases, embeddings | HIGH | Direct match |
| Mentions NLP, unstructured text, document intelligence | HIGH | Strong match |
| Mentions LangChain, LangGraph | HIGH | Direct match |
| Mentions production deployment, Docker, AWS | MEDIUM | Match |
| Mentions GCP, Vertex AI | LOW | Claim familiar only — do not overstate |
| Mentions LoRA, QLoRA, fine-tuning | LOW | Gap — flag honestly |
| Mentions DSA, system design, Java | MEDIUM | Match via BEL + ScoreMe |
| Mentions 0-to-1 product building | HIGH | Match via YAAR + OrangeLabs |
| Requires 2+ years experience | FLAG | Counter with internship depth |
| Mentions Hugging Face | LOW | Gap — flag honestly |

---

## SECTION 10: ATS DETERMINISTIC ANSWERS

### COMPENSATION
- **Expected Annual Compensation:** [PENDING USER INPUT - e.g. 15,00,000 INR]
- **Expected Monthly Compensation:** [PENDING USER INPUT - e.g. 1,00,000 INR]
- **Expected Internship Stipend:** [PENDING USER INPUT - e.g. 50,000 INR]
- **Expected Full-Time Salary:** [PENDING USER INPUT - e.g. 15,00,000 INR]
- **Salary Negotiable:** Yes

### AVAILABILITY
- **Can Start Immediately:** Yes
- **Notice Period:** 0 Days
- **Available For Internship:** Yes
- **Available For Full-Time:** Yes
- **Earliest Start Date:** [PENDING USER INPUT - e.g. 2026-07-01]
- **Latest Start Date:** [PENDING USER INPUT - e.g. 2026-08-01]
- **Expected Graduation Date:** May 2026

### LANGUAGES
- **English:** Professional
- **Hindi:** Native
- **Other Languages:** None

### WORK AUTHORIZATION
- **India Work Authorization:** Yes
- **US Work Authorization:** No
- **Requires Sponsorship:** Yes (for US roles)
- **Security Clearance:** No

### RELOCATION
- **Willing To Relocate:** Yes
- **Preferred Locations:** Gurgaon, Bangalore, Noida, Delhi, Pune, Navi Mumbai, Hyderabad, Mumbai

---

*Version: 2.1 — Merged master file with ATS deterministic answers*
*Sources: yash_candidate_intelligence_db.txt, yash_candidate_intelligence.md, yash_profile.md, projects.md*
*Company-specific concept projects excluded per instruction*
