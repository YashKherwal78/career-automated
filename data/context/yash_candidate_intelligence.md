# CANDIDATE INTELLIGENCE DATABASE
# Yash Kherwal — Permanent Profile
# Optimized for: Resume Generation, Tailoring, Job Matching, Project Selection, Email Writing
# Consumer: Groq LLM (downstream agent)

---

## 1. IDENTITY SNAPSHOT

**Name:** Yash Kherwal
**Degree:** B.Tech Chemical Engineering, IIT Roorkee (2022–2026)
**Location:** India (targeting Bangalore/Hyderabad)
**Contact:** +91 9891148156 | yash.kherwal78@gmail.com
**LinkedIn:** linkedin.com/in/yash-kherwal-944497254
**CPI:** ~5.6 — NEVER include on resume

**One-line identity:**
IIT Roorkee engineer who builds end-to-end AI systems independently, treats job search as an engineering problem, and thinks in systems and failure modes before features.

---

## 2. CAREER TARGETS

**Primary roles (in order of preference):**
1. Associate Product Manager (APM) / AI Product Manager
2. ML Engineer / AI Engineer
3. SDE with AI/ML focus

**Target companies:**
Mid-size funded Indian startups (Razorpay, CRED, Groww, Meesho, PhonePe) + product companies (InMobi, EA, JPMorgan, Zimmer Biomet, Auric AI, EXL, Orange Labs)

**Anti-targets:**
IT services companies (TCS, Infosys, Wipro) — avoid

**Geography:** Bangalore primary, Hyderabad secondary

---

## 3. INTERNSHIP EXPERIENCE

### 3.1 Orange Labs (Feb 2026 – Apr 2026)
**Title:** AI Engineer Intern
**Company type:** EdTech ERP platform for schools and colleges
**What they build:** School/college ERP systems, Attendance Plus (CCTV attendance), AI-generated teacher lecture product

**What Yash worked on:**
- CCTV-based automated attendance (computer vision pipeline → ERP sync)
- AI-generated personalised lecture pipeline (teacher voice/likeness cloning for student-facing content)
- n8n ERP workflow automation (not featured on resume — weakest signal)

**Honest depth:** Yash studied the stack post-internship; has certificate titled "AI Engineer." Bullets are directionally accurate but implementation depth is moderate. Interview prep required on: YOLO/DeepFace for attendance, Wav2Lip/SadTalker for video synthesis.

**Best used for:** AI Engineer, ML Engineer, EdTech product roles
**Do not use for:** Pure backend SDE roles, finance/banking roles

---

### 3.2 ScoreMe Solutions (May 2025 – Jun 2025)
**Title:** Software Development Intern
**Company type:** Fintech — credit scoring, PDF document processing

**What Yash built:**
- Two-stage ML classification pipeline: rule-based pre-filter → Random Forest classifier
- Confidence calibration layer: low-confidence predictions quarantined from credit scoring pipeline
- Tesseract OCR + PDFBox fallback for scanned/handwritten inputs

**Why it matters on resume:**
Shows real fintech data pipeline thinking — failure mode awareness (silent misclassification), production-grade confidence thresholding, fallback design. Strong signal for any data/ML role.

**Best used for:** Data Science, ML Engineer, fintech SDE, any role that values production ML thinking
**Interview talking points:** Why two-stage instead of one model; why confidence thresholding matters in credit contexts; OCR fallback design decision

---

### 3.3 Bharat Electronics Limited (Jun 2025 – Jul 2025)
**Title:** Engineering Intern
**Company type:** Defense PSU — radar systems

**What Yash built:**
- Binary stream parser for ASTERIX CAT048 radar protocol (EUROCONTROL spec)
- Decoded variable-length optional-field packet structures
- Concurrent ingestion with backpressure handling

**Why it matters:**
Shows low-level systems thinking, protocol parsing, concurrency — strong signal for SDE roles at companies like InMobi that care about distributed systems fundamentals.

**Best used for:** SDE roles, backend-heavy roles, defense/systems companies (Auric AI)
**Do not use for:** Pure product/PM roles where it adds noise

---

## 4. PROJECTS

### 4.1 Autonomous Data Analysis Agent
**Elevator pitch:** A 5-agent LangGraph pipeline that takes a natural language question, routes it to SQL or Python execution, auto-fixes runtime errors, and returns actionable insights — fully automated end-to-end.

**Stack:** Python, LangGraph, CrewAI, n8n, MCP, FastAPI, Docker, AWS EC2

**Architecture:**
Query Planner → Code Writer → Executor → Error Fixer → Insight Generator

**Key technical decisions:**
- Query Planner does intent classification BEFORE generation — eliminates downstream type errors
- Error Fixer: classify → regenerate → retry loop (ReAct-style)
- MCP standardises tool context across agents
- Docker sandbox isolates LLM-generated code from host
- n8n decouples orchestration from agent logic

**What this says about Yash:**
Thinks about failure modes before features. Designs inter-agent contracts. Understands why single-agent systems break on ambiguous inputs.

**Best roles:** ML Engineer, AI Engineer, Agentic AI Engineer, SDE (AI-focused)
**Best companies:** EA (EADP), JPMorgan (Transformation & Analytics), GCP role, Auric AI
**Do NOT use for:** Pure PM roles, data analyst roles, companies that don't care about agentic systems

**Resume highlights:**
- Stateful multi-agent architecture with deterministic routing
- Autonomous exception recovery
- Production deployment on AWS EC2 with Docker isolation

**Interview story:** "I built this because single-agent code generation kept breaking on ambiguous queries. The fix wasn't better prompting — it was separating intent classification from generation entirely."

---

### 4.2 Hybrid RAG / Semantic Document Search
**Elevator pitch:** A hybrid retrieval system over 500+ documents that combines dense semantic embeddings with sparse keyword scores, deployed as a decoupled ingestion + serving pipeline on AWS.

**Also known as:** GDSC IIT Roorkee project (Semantic Document Search)

**Stack:** Python, LangChain, BGE-M3, AstraDB, FastAPI, AWS EC2

**Key technical decisions:**
- BGE-M3 chosen over Sentence-Transformers for multilingual + cross-lingual capability
- Hybrid retrieval: dense (BGE-M3) + sparse (BM25) — addresses vocabulary mismatch
- AstraDB for managed ANN indexing — no self-hosted infra overhead
- Decoupled ingestion and serving: corpus updates without downtime
- Prompt constraints for response groundedness — hallucination prevention

**What this says about Yash:**
Diagnoses root causes (vocabulary mismatch, not just "retrieval is bad"). Makes informed model selection decisions. Thinks about operational concerns (downtime, provenance).

**Best roles:** ML Engineer, AI Engineer, Data Scientist (NLP), any role involving document intelligence
**Best companies:** Auric AI (multilingual entity resolution), Zimmer Biomet (contract analysis), JPMorgan (unstructured data), InMobi
**Do NOT use for:** Roles with no NLP/retrieval component

**Resume highlights:**
- Root cause diagnosis before solution
- BGE-M3 multilingual selection rationale
- Decoupled architecture for operational resilience
- Hallucination mitigation via prompt constraints

**Interview story:** "BM25 was missing semantically identical documents described in different words. Adding dense embeddings wasn't enough — I needed hybrid scoring to handle both vocabulary match and semantic similarity."

---

### 4.3 YAAR — Personality-Adaptive LLM System
**Elevator pitch:** An Android app where the AI companion adapts its personality to you over time — tracking a personality metric vector across sessions and injecting it into the LLM context to steer tone without fine-tuning.

**Stack:** React Native, LLM APIs (Gemini Flash), FastAPI, shared_preferences, EAS Build

**Key design decisions:**
- Personality metric vector: humour tolerance, self-awareness index, reaction intensity
- Updated via tap-based reactions — weighted delta per dimension
- Injected into LLM context window at inference time
- Cold-start: random outputs → identity-calibrated as confidence accumulates
- Persistent server-side across sessions

**What this says about Yash:**
Thinks about user behavior modeling, not just AI capabilities. Understands the difference between fine-tuning and prompt-based steering. Ships — Android APK delivered.

**Target market:** Tier 2/3 India, Hinglish users, behavioral AI / micro-recognition niche

**Best roles:** AI PM, APM, consumer AI product roles, ML Engineer (personalization)
**Best companies:** Consumer tech startups, EdTech, social/companion AI companies
**Do NOT use for:** Enterprise B2B roles, defense/intelligence roles, pure backend SDE

**Resume highlights:**
- Persistent personality memory without fine-tuning
- Shipped Android APK
- Behavioral metric system from user interactions

**Interview story:** "The insight was that personality adaptation doesn't need fine-tuning — you just need a structured state that gets richer with every interaction and shapes the prompt."

---

### 4.4 Recruiting Intelligence Platform
**Elevator pitch:** A 9-agent autonomous recruiting system that discovers jobs, scores fit, finds hiring contacts, generates personalised outreach, and manages the full application workflow — zero manual intervention daily.

**Stack:** Python, LangGraph, multi-agent system, CRM, FastAPI

**Architecture:**
Mission Control orchestration → agents for: job discovery, fit scoring, contact identification, resume tailoring, email generation, outreach validation, CRM tracking, inbox monitoring, executive summary

**Key design decisions:**
- Centralised Mission Control layer for agent routing and task sequencing
- Interview-probability scoring before outreach — quality gate
- Bounce-rate protection — prevents domain blacklisting
- Duplicate-prevention via CRM state management
- Daily autonomous execution cycle

**Origin story:**
Yash built this to solve his own job search. Treats recruiting as an engineering problem with KPIs (interviews generated). Classic "scratch your own itch" product.

**What this says about Yash:**
Extreme ownership. Builds systems to solve his own problems. Thinks in pipelines, KPIs, and quality gates — not just features. Meta-signal: he's smart enough to automate his own job search.

**Best roles:** APM, AI PM, AI Engineer, any role that values autonomous systems thinking
**Best companies:** Startups that value scrappiness and self-driven builders; product companies
**Do NOT use for:** Conservative enterprise companies (JPMorgan) where "automating your job search" may read as gimmicky; defense roles

**Resume highlights:**
- Mission Control orchestration layer design
- Quality-control mechanisms (bounce protection, probability scoring)
- Fully autonomous daily execution cycle
- End-to-end system ownership

**Interview story:** "I was applying to jobs manually and realized I was doing the same 8 steps every time. So I built a system that does them. It's not a script — it's an agent network with quality gates because bad outreach is worse than no outreach."

---

### 4.5 SC-MFC Power Optimisation (BTP Thesis)
**Elevator pitch:** Built a multi-output ANN (R²=0.963) to model microbial fuel cell power output, then ran a Pareto-style random search to find the optimal operating configuration — pH 7.40, 25.34°C, 2.32cm spacing, 1920 mg/L COD → 62.60 mW/m².

**Stack:** Python, TensorFlow, Scikit-learn, KNN imputation, StandardScaler

**Key technical decisions:**
- KNN imputation over mean imputation — preserves local structure
- StandardScaler fitted on training set only — prevents data leakage
- 64-32-16 ANN with BatchNorm + Dropout
- Weighted multi-task loss for multi-output regression
- EarlyStopping + ReduceLROnPlateau
- R² improved from 0.547 (baseline) to 0.963

**What this says about Yash:**
Can do rigorous ML from scratch on real messy data. Understands data leakage, regularization, multi-task learning. Academic credibility despite non-CS degree.

**Best roles:** Data Scientist, ML Engineer (research-adjacent), any role requiring statistical modelling
**Best companies:** EXL, Zimmer Biomet, JPMorgan (quantitative), research-adjacent startups
**Do NOT use for:** Pure product/PM roles, SDE roles where it adds noise

---

## 5. PERSONAL PROFILE

### 5.1 How Yash Thinks
- **Systems first:** Yash naturally decomposes problems into pipelines, stages, and failure modes before writing code
- **Diagnosis before solution:** Consistently identifies root cause (vocabulary mismatch, silent misclassification propagation, single-agent ambiguity) rather than applying generic fixes
- **Engineering lens on everything:** Even his job search became an engineered system with KPIs
- **Tradeoff-aware:** Chooses BGE-M3 over Sentence-Transformers with explicit rationale; chooses two-stage over single-model with explicit rationale
- **Failure mode-first:** Designs confidence thresholds, quarantine layers, bounce protection — thinks about what breaks before it breaks

### 5.2 How Yash Builds
- **Independent end-to-end:** Builds full systems alone — frontend, backend, ML, deployment
- **Iterative with conversation:** Uses conversations to think through architecture before building (evidenced by this very session)
- **Ships:** Android APK delivered, EC2 deployments live, PDFs compiled — not just designs
- **Structured outputs:** Thinks in contracts between components; enforces schemas at boundaries
- **Documentation by conversation:** Doesn't write docs first but articulates decisions clearly when asked

### 5.3 Working Style
- Prefers direct, honest feedback over cautious hedging
- Builds and iterates through conversation — uses dialogue as a thinking tool
- High ownership: treats assigned problems as his own, not as tasks
- Comfortable with ambiguity — figures out the architecture when there's no playbook
- Impatient with process for its own sake; respects process that prevents failures

### 5.4 How He Learns
- Learns by building — not by courses or tutorials
- Studies a stack after using it (Orange Labs: studied CV/synthesis post-internship)
- Uses conversations to reverse-engineer understanding of systems he built with AI assistance
- Prefers targeted short resources over long crash courses

### 5.5 Strengths
1. **Systems architecture thinking** — decomposes complex problems into clean pipelines
2. **Failure mode awareness** — thinks about what breaks before being asked
3. **End-to-end ownership** — ships complete systems independently
4. **Root cause diagnosis** — doesn't treat symptoms
5. **Self-direction** — builds what he needs, including tools to solve his own problems
6. **Communication** — articulates technical decisions clearly and with rationale

### 5.6 Weaknesses / Honest Gaps
- CPI ~5.6 — academic signal is weak; never include
- Orange Labs implementation depth is moderate — needs prep before CV/synthesis interview questions
- No explicit GCP/Vertex AI experience — claim only "familiar"
- No LoRA/QLoRA fine-tuning experience — gap for some ML roles
- No Hugging Face hands-on — gap for NLP-heavy roles
- 0 years official experience — fresher; internships are the counter-argument

---

## 6. RESUME STRATEGY

### 6.1 AI / ML Engineer Resume Strategy
**Include:** Autonomous Data Analysis Agent, Semantic Document Search, YAAR, SC-MFC (optional for depth)
**Exclude:** Recruiting Intelligence Platform (too product-y for pure ML)
**Lead experience with:** Orange Labs (most recent, most AI-relevant)
**Skills emphasis:** LangGraph, LangChain, RAG, BGE-M3, AstraDB, TensorFlow, Docker, AWS EC2, Multi-agent orchestration
**Key framing:** Failure mode thinking, deterministic routing, production-grade deployment, autonomous error recovery
**Tone:** Technical depth, architecture decisions, tradeoff rationale

---

### 6.2 Product / APM Resume Strategy
**Include:** YAAR, Recruiting Intelligence Platform, Semantic Document Search
**Exclude:** BEL (too systems/defense), SC-MFC (too academic)
**Lead experience with:** Orange Labs (AI product, teacher cloning — strong product story)
**Skills emphasis:** Product thinking, user behavior modeling, 0-to-1 building, AI product design, shipped Android APK
**Key framing:** Why built (origin story), who it's for, what problem it solves, what was shipped
**Tone:** Product intuition, user empathy, business impact, ownership

---

### 6.3 Software Engineer Resume Strategy
**Include:** Autonomous Data Analysis Agent, Semantic Document Search, Recruiting Intelligence Platform
**Exclude:** YAAR (too product-y), SC-MFC (too academic/research)
**Lead experience with:** BEL (systems, concurrency, protocol parsing — strongest SDE signal) or ScoreMe
**Skills emphasis:** Python, Java, C++, DSA, concurrency, multi-threading, REST APIs, Docker, AWS, SQL
**Key framing:** Scale, throughput, backpressure, deterministic routing, system reliability
**Tone:** Engineering fundamentals, clean architecture, production thinking

---

### 6.4 Data Scientist Resume Strategy
**Include:** SC-MFC (BTP), Semantic Document Search, Autonomous Data Analysis Agent
**Exclude:** YAAR, Recruiting Intelligence Platform
**Lead experience with:** ScoreMe (ML pipeline, confidence calibration — strongest DS signal)
**Skills emphasis:** Python, SQL, TensorFlow, Scikit-learn, EDA, regression, NLP, RAG, statistical modelling, Pandas
**Key framing:** EDA → insight → model → production pipeline; rigorous model evaluation; actionable outputs for stakeholders
**Tone:** Analytical rigor, business impact of model decisions, stakeholder communication

---

## 7. EMAIL / OUTREACH STRATEGY

**Core narrative for cold outreach:**
"IIT Roorkee engineer building at the intersection of AI systems and product — I don't just use LLM APIs, I design the pipelines, failure modes, and deployment architecture around them."

**For AI/ML roles:**
Lead with the agentic workflow or RAG system — focus on the architecture decision, not the tech stack.

**For PM/APM roles:**
Lead with YAAR or Recruiting Intelligence Platform — focus on the problem origin, user insight, and what was shipped.

**For SDE roles:**
Lead with BEL (systems credibility) + ScoreMe (production ML) — establishes fundamentals before AI work.

**Subject line formulas:**
- "IIT Roorkee → built a 5-agent autonomous pipeline → applying for [role]"
- "Built a RAG system for [relevant domain] — applying for [role] at [company]"
- "Shipped an Android AI companion app — interested in [PM/APM role]"

---

## 8. JOB MATCHING SIGNALS

| Signal | Weight | Notes |
|---|---|---|
| Mentions "agentic AI" or "multi-agent" | HIGH | Direct match to core projects |
| Mentions RAG, vector databases, embeddings | HIGH | Direct match |
| Mentions NLP, unstructured text, document intelligence | HIGH | Strong match |
| Mentions LangChain, LangGraph | HIGH | Direct match |
| Mentions production deployment, Docker, AWS | MEDIUM | Match |
| Mentions GCP, Vertex AI | LOW | Claim familiar only |
| Mentions LoRA, QLoRA, fine-tuning | LOW | Gap — needs honest flagging |
| Mentions DSA, system design, Java | MEDIUM | Match via BEL + ScoreMe |
| Mentions 0-to-1 product building | HIGH | Match via YAAR + Recruiting platform |
| Requires 2+ years experience | FLAG | Counter with internship depth |

---

## 9. FORMATTING RULES (for resume generation)

- **Format:** Jake's resume format ALWAYS
- **Font:** 10.5pt
- **Margins:** oddsidemargin -0.5in, textwidth +1.0in, topmargin -0.5in, textheight +1.1in
- **Section rule:** `\color{black}\titlerule` with `\vspace{-4pt}` before and `\vspace{-5pt}` after
- **Project heading:** `\vspace{-4pt}` before
- **Item spacing:** `itemsep=2pt, topsep=2pt`
- **Page limit:** STRICTLY 1 page
- **CPI:** NEVER include
- **Experience before Projects:** ALWAYS
- **No fabrication:** Never invent technical details not confirmed by Yash

---

*Last updated: June 2026*
*Built from: resume sessions, project discussions, tailoring conversations with Claude*
