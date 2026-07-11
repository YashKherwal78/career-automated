# PROJECT INTELLIGENCE DATABASE

## YAAR — AI Behavioral Companion
**Tags:** product, consumer, personalization, recommendation, engagement, genai, llm, react native, behavioral

**Elevator Pitch:** A zero-input AI companion for Gen Z in Tier 2/3 India that learns your personality from how you react to content — not what you tell it — and gets more "you" over time. Primary revenue is contextual native brand integration.
**Stack:** React Native, LLM APIs (Gemini Flash), FastAPI, shared_preferences, EAS Build
**Key Technical Decisions:**
- Preference engine tracks 3 personality dimensions (humour tolerance, self-awareness index, reaction intensity) from tap reactions — no retraining, purely inference-time via dynamic prompt construction
- Output variance deliberately preserved (not minimised) to prevent staleness
- Server-side state persistence across sessions
**Key Product Decisions:**
- Brand integration framed as behavioral state-triggered suggestion, not ad placement
- Identity card share mechanic designed as viral acquisition loop (deep-linked, friend sees teaser, gets own output)
**What This Says About Yash:** He ships. He thinks about retention mechanics, growth loops, and monetisation at product design time — not as afterthoughts. Understands Gen Z consumer psychology for India's Tier 2/3 market.

---

## Echo Pod — AI Stillness Companion
**Tags:** wellness, interaction-design, on-device, voice, latency, consumer, mobile

**Elevator Pitch:** An on-device AI product that intercepts idle moments on your phone and redirects you toward reflection instead of more scrolling — not by blocking, by competing for the same moment.
**Origin:** Diagnosed that screen blocker apps have 25% first-session churn because they fight behavior instead of rewiring reward. Designed around interception and redirection.
**Key Product Insight:** People don't fear boredom — they fear unmediated thought. The problem isn't attention span, it's discomfort avoidance. People don't have an information problem — they have a time and attention problem.
**Key Technical Decision:** On-device inference (not cloud) — zero round-trip latency is a product constraint, not just an engineering preference. A 3-second ambient trigger window does not tolerate cloud round-trip.
**What This Says About Yash:** Diagnoses the failure mode of competitors before designing. Thinks about why existing solutions fail, not just what the solution should do.

---

## AI Data Analyst Agent
**Tags:** automation, agents, workflow, recruitment, langgraph, crewai, orchestration, python, fastapi, aws

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

---

## Semantic Document Search — GDSC IIT Roorkee
**Tags:** search, retrieval, rag, vector-db, semantic-search, embeddings, hybrid-search, full-stack

**Elevator Pitch:** Rebuilt a 500+ document knowledge base from keyword search to hybrid RAG — users get direct grounded answers instead of a list of documents to manually search.
**Architecture:** Hybrid Search (BM25 + Vector Embeddings) → Re-ranking → LLM Synthesis
**Key Challenges & Decisions:**
- Pure semantic search failed on acronyms (e.g., "IITR", "GDSC"). Reverted to hybrid search combining BM25 (exact keyword match) with dense embeddings (semantic intent).
- Implemented aggressive caching at the query layer to avoid re-embedding standard queries.
- Optimised for speed: Users drop off if search takes > 2s. Kept the synthesis prompt extremely short and focused on extractive rather than abstractive answering.
**What This Says About Yash:** Pragmatic builder. Discovered the limitations of purely theoretical AI architectures (pure vector search) when applied to real-world messy data (acronyms) and correctly pivoted to a hybrid architecture.
