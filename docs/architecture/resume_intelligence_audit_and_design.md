# Resume Intelligence Platform Audit & Architecture Design Document

**Auditor Role**: Senior Staff Software Engineer & AI Systems Architect  
**Target Platform**: CareerAutomated Resume Intelligence Subsystem  
**Date**: July 24, 2026  

---

## PART 1 — Existing Resume Tailoring Engine Audit

### Current Architecture & Pipeline Flow
The existing codebase contains pieces of a candidate extraction and advisory tailoring flow across `src/services/profile_extractor.py`, `src/utils/document_extractor.py`, `src/career_intelligence/tailoring/engine.py`, `src/applications/resume_selector.py`, and `src/career_intelligence/resume/analyzer.py`.

```text
Actual System Architecture & Data Flow:

Raw Document File (.pdf, .docx, .txt)
          │
          ▼
DocumentTextExtractor (pypdf / python-docx / UTF-8)
          │
          ▼
Raw Unstructured Text
          │
          ▼
ProfileExtractionService (LLMRouter chat_completion)
          │
          ├─────────────────────────────────────────┐
          ▼                                         ▼
Canonical JSON Profile                      RAG Passage Documents
(personal_info, education, experience,       (vector embeddings for Q&A)
 projects, skills, certifications)
          │
          ▼
CandidateContext (CandidateAnalyzer)
          │
          ▼
ComparisonEngine (Deterministic Match vs Job)
          │
          ▼
ComparisonResult / EvidenceReport
          │
          ├─────────────────────────────────────────┐
          ▼                                         ▼
ResumeTailoringEngine                       ResumeIntelligenceAnalyzer
(Generates JSON suggestions for             (Calculates ATS Score &
 keywords & project reordering)              missing keyword report)
```

### Key Architectural Finding
The current system **does NOT rewrite or generate documents**. `ResumeTailoringEngine` returns string recommendations (`"Incorporate 'FastAPI' into your summary"`), and `ResumeSelector` falls back to returning pre-existing static PDF files (`data/Resume_aiml.pdf`). There is **zero document compilation (LaTeX / PDF / DOCX)**, zero bullet-level AI rewriting, and zero PDF OCR capability.

---

## PART 2 — Repository Map & Code Responsibilities

| File Path | Primary Responsibilities | Dependencies | Clean vs. Mixed Responsibilities |
| :--- | :--- | :--- | :--- |
| [`src/utils/document_extractor.py`](file:///Users/yashkherwal/Downloads/hrmailfiles/backend/src/utils/document_extractor.py) | Reads raw text from `.pdf`, `.docx`, `.txt`, `.md`. | `pypdf`, `python-docx` | **Clean**: Pure text extraction utility. |
| [`src/services/profile_extractor.py`](file:///Users/yashkherwal/Downloads/hrmailfiles/backend/src/services/profile_extractor.py) | Converts raw text into JSON schema and creates RAG passage documents. | `LLMRouter`, `DocumentTextExtractor` | **Mixed**: Handles LLM prompting, JSON normalization, AND vector passage chunking. |
| [`src/career_intelligence/tailoring/engine.py`](file:///Users/yashkherwal/Downloads/hrmailfiles/backend/src/career_intelligence/tailoring/engine.py) | Generates textual tailoring recommendations based on `ComparisonResult`. | `MatchScoreEngine` | **Clean**: Pure advisory logic, but missing actual document modification. |
| [`src/applications/resume_selector.py`](file:///Users/yashkherwal/Downloads/hrmailfiles/backend/src/applications/resume_selector.py) | Selects a static resume variant based on job title string matching. | Standard library `os` | **Legacy Mock**: Uses hardcoded filename dict (`Yash_product.pdf`, `Resume_aiml.pdf`). |
| [`src/career_intelligence/resume/analyzer.py`](file:///Users/yashkherwal/Downloads/hrmailfiles/backend/src/career_intelligence/resume/analyzer.py) | Calculates ATS score and keyword gap analysis from `EvidenceReport`. | `EvidenceReport` | **Clean**: Immutable evaluation metric engine. |

---

## PART 3 — Resume Tailoring Pipeline Breakdown

The real pipeline as it exists in the codebase today:

1. **Input Document**: Uploaded `.pdf`, `.docx`, or `.txt` file path.
2. **Text Extraction**: `DocumentTextExtractor.extract_text()` calls `pypdf` or `docx.Document` to obtain plain string content.
3. **LLM Extraction**: `ProfileExtractionService.extract_profile()` sends raw text to `LLMRouter.chat_completion()` with a JSON schema instruction.
4. **JSON Normalization**: `_normalize_empty_sections()` sets default lists/dicts for missing sections.
5. **RAG Document Generation**: `_generate_embedding_documents()` creates formatted text passages for vector index storage.
6. **Comparison Engine Match**: `ComparisonEngine.compare()` evaluates candidate capabilities against job requirements.
7. **Advisory Tailoring**: `ResumeTailoringEngine.generate_tailoring_plan()` returns string suggestions based on `technologies.missing` and `projects.matched_projects`.

---

## PART 4 — Candidate Representation & Knowledge Sharing

- **Is there a CandidateProfile?**: Yes, as a raw dictionary returned by `ProfileExtractionService` and a Pydantic model `CandidateProfile` in `candidate_intelligence/models.py`.
- **Is there structured data?**: Yes, structured into `personal_info`, `education`, `experience`, `projects`, `skills`, `certifications`, `publications`, `languages`, `external_links`.
- **Is information duplicated?**: Yes. `ProfileExtractionService` outputs dicts, `CandidateAnalyzer` transforms them into `CandidateContext`, and `ResumeSelector` ignores both to read raw PDFs from `data/`.
- **Can downstream systems reuse it?**: Currently limited. Each module re-transforms profile data rather than reading from a single shared **Canonical Candidate Knowledge Graph**.

---

## PART 5 — Tailoring Logic Capabilities Audit

| Tailoring Feature | Current Implementation Status |
| :--- | :--- |
| **Rewrite Bullets** | ❌ Not Implemented (Only advisory string suggestions) |
| **Reorder Bullets** | ❌ Not Implemented |
| **Rewrite Summary** | ❌ Not Implemented |
| **Reorder Projects** | ⚠️ Partial (Returns string advice: `"Move 'Project X' to top"`) |
| **Modify Skills** | ⚠️ Partial (Lists missing technologies as suggestions) |
| **Remove Irrelevant Content** | ❌ Not Implemented |
| **PDF Compiler Output** | ❌ Not Implemented (No Typst / LaTeX / ReportLab compiler) |

---

## PART 6 — ATS Optimization & Truthfulness Audit

- **Keyword Selection**: Extracted directly from `ComparisonResult.technologies.missing`.
- **ATS Score Estimation**: `ResumeIntelligenceAnalyzer` estimates score deterministically using:
  $$\text{ATS Score} = \max(40.0, 100.0 - 12.0 \times |\text{missing\_capabilities}|)$$
- **Truthfulness & Hallucination Prevention**: Currently relies solely on system prompt instructions (`"Do not hallucinate or guess fields"`). There is **no programmatic post-generation assertion engine** verifying that generated bullet points only reference skills present in the candidate's master profile.

---

## PART 7 — Prompt Audit

### Prompts in Codebase
1. **Profile Extraction Prompt** ([`profile_extractor.py:L22-L130`](file:///Users/yashkherwal/Downloads/hrmailfiles/backend/src/services/profile_extractor.py#L22-L130)):
   - **Structure**: System role instructions + normalization rules (dates as `MMM YYYY`, deduplication) + inline JSON schema string.
   - **Weaknesses**: Extremely large prompt string (over 100 lines inline); lacks few-shot parsing examples for edge cases (e.g. military experience or publications).

---

## PART 8 — AI vs. Deterministic Logic Matrix

| Component | Current Implementation | Recommendation |
| :--- | :--- | :--- |
| **Text Extraction** | Deterministic (`pypdf`, `python-docx`) | Keep Deterministic |
| **Document Classification** | AI (`LLMRouter`) | Switch to Regex/Rules for standard fields; AI for ambiguous sections |
| **ATS Scoring** | Deterministic (`ResumeIntelligenceAnalyzer`) | Keep Deterministic |
| **Keyword Gap Detection** | Deterministic (`ComparisonEngine`) | Keep Deterministic |
| **Bullet Point Rewriting** | None | **AI (`LLMRouter`) with Deterministic Fact Verification** |
| **PDF Rendering** | None | **Deterministic (Typst / Weasyprint HTML-to-PDF Engine)** |

---

## PART 9 — Resume Validation Safeguards Audit

Currently, validation safeguards are **minimal**:
- `_normalize_empty_sections()` ensures empty lists exist so UI calls don't throw `KeyError`.
- No verification of missing dates, chronological ordering, duplicate bullet detection, or hallucinated claims.

---

## PART 10 — Performance & Caching Audit

- **LLM Overhead**: Every profile extraction makes an un-cached LLM call with temperature `0.1`. Extracting a 3-page resume takes **4.5 to 8.0 seconds**.
- **Caching Opportunity**: Profile extraction should hash the input document (`MD5` / `SHA256`) and cache structured profiles in Redis / disk store.

---

## PART 11 — Production Readiness Score

### System Rating: **4.5 / 10**

- **SOLID Violations**: `ProfileExtractionService` handles LLM calls, schema enforcement, data defaults, AND vector embedding chunking in a single file.
- **Missing Core Capability**: Tailoring does not generate actual downloadable resumes.
- **No PDF Compiler**: Cannot compile tailored profiles into clean PDF deliverables.

---

## PART 12 — Testing Coverage Audit

- **Current Tests**: Unit tests exist for `CandidateAnalyzer` and `ResumeIntelligenceAnalyzer`.
- **Missing Tests**:
  - Invalid / corrupted PDF extraction tests.
  - Multi-column resume layout extraction.
  - Truthfulness & hallucination regression tests for bullet rewrites.
  - PDF rendering compiler tests.

---

## PART 13 — Resume Parser Capabilities

- **PDF**: Supported via `pypdf` (Text layer only).
- **DOCX**: Supported via `python-docx`.
- **TXT / MD**: Supported via UTF-8 file reading.
- **Unsupported Formats**: Scanned image PDFs, DOC, RTF, PNG/JPG images, ZIP uploads.

---

## PART 14 — OCR Audit

- **Current Status**: **NO OCR Engine exists**.
- **Failure Mode**: If a user uploads a scanned PDF or a canvas-exported image PDF, `pypdf.extract_text()` returns an empty string `""`, throwing an unhandled `ValueError("No text content could be extracted")`.
- **Architectural Requirement**: Integrate `pdf2image` + `pytesseract` / `EasyOCR` fallback pipeline for image-based PDFs.

---

## PART 15 — Candidate Extraction Completeness

| Field Category | Supported in Current Extractor? |
| :--- | :--- |
| Personal Info (Name, Email, Phone, Location) | ✅ Supported |
| LinkedIn / GitHub / Portfolio Links | ✅ Supported |
| Education & Degrees | ✅ Supported |
| Work Experience & Bullets | ✅ Supported |
| Projects & Tech Stack | ✅ Supported |
| Skills (Languages, Frameworks, DBs, Cloud) | ✅ Supported |
| Certifications | ✅ Supported |
| Publications & Awards | ✅ Supported |
| Patents, Volunteer Work, Open Source | ❌ Not Supported |

---

## PART 16 — Canonical Resume Knowledge Graph Architecture

Target unified data flow across all system components:

```text
Upload Resume (.pdf/.docx) ──► Resume Parser ──┐
                                               │
User Scratch Form ───────────► Resume Builder ─┼──► Canonical Candidate Profile
                                               │    (Single Source of Truth)
External Imports ────────────► Profile Importer┘               │
(LinkedIn, GitHub)                                              │
                                                                ▼
                     ┌──────────────────────────────────────────┼──────────────────────────────────────────┐
                     ▼                                          ▼                                          ▼
           Career Intelligence                          Resume Tailoring                            AutoApply Engine
         (Match & Gap Analytics)                   (Typst/HTML PDF Compiler)                       (Form Field Filler)
```

---

## PART 17 — External Profile Import System Design

Design for importing & enriching candidate profiles:
1. **GitHub Connector**: Fetches top repositories, language distributions, and commit volume using GitHub GraphQL API.
2. **LinkedIn PDF Importer**: Parses exported LinkedIn profiles using specialized section rules.
3. **LeetCode / Codeforces Importer**: Fetches rating, problem counts, and verified algorithms tags.
4. **Human Verification Gate**: All newly discovered external skills/projects require user approval (`CONFIRM` / `REJECT`) before merging into the Canonical Profile.

---

## PART 18 — Resume Builder (From Scratch) Architecture

A 6-step guided wizard for generating a candidate's Master Profile without uploading a resume:

```text
Step 1: Contact & Social Links
Step 2: Education & Academic Honors
Step 3: Work Experience & Metric Bullets
Step 4: Key Projects & Tech Stack
Step 5: Categorized Skills & Tools
Step 6: Certifications & Languages
           │
           ▼
 Master Candidate Profile JSON ──► Master Typst Template Compiler ──► Master Resume PDF
```

---

## PART 19 — Master Resume Platform Architecture

```text
                           Resume Intelligence Platform
                                         │
       ┌─────────────────────────────────┼─────────────────────────────────┐
       │                                 │                                 │
       ▼                                 ▼                                 ▼
1. Resume Parser                 2. Resume Builder                 3. Resume Tailoring
   (OCR + Document Extractor)       (Multi-Step Wizard Engine)        (ATS Optimization & PDF Compiler)
       │                                 │                                 │
       └─────────────────────────────────┼─────────────────────────────────┘
                                         │
                                         ▼
                            Canonical Candidate Profile
                                         │
       ┌─────────────────────────────────┼─────────────────────────────────┐
       ▼                                 ▼                                 ▼
Career Intelligence Engine        Interview Intelligence              AutoApply Pipeline
```

---

## PART 20 — Target Architecture & Folder Structure

### Proposed Directory Layout (`src/resume_intelligence/`)

```text
src/resume_intelligence/
├── __init__.py
├── canonical_profile.py        # Shared Canonical Profile Pydantic models
├── parser/
│   ├── __init__.py
│   ├── extractor.py            # PDF/DOCX/TXT text extractor
│   ├── ocr_engine.py           # Tesseract/EasyOCR fallback for scanned PDFs
│   └── llm_parser.py           # LLM extraction & schema normalizer
├── builder/
│   ├── __init__.py
│   └── wizard_service.py       # Master profile step-by-step construction
├── tailoring/
│   ├── __init__.py
│   ├── bullet_rewriter.py      # Targeted action-verb bullet generator
│   ├── keyword_optimizer.py    # ATS density & gap alignment
│   └── validator.py            # Deterministic truthfulness & anti-hallucination checker
├── compiler/
│   ├── __init__.py
│   ├── typst_compiler.py       # Production Typst -> PDF rendering engine
│   └── templates/              # Production modern resume templates
└── importers/
    ├── __init__.py
    ├── github_importer.py      # GitHub API profile enrichment
    └── linkedin_importer.py    # LinkedIn PDF export parser
```

### Risk Assessment & Implementation Roadmap
1. **Phase 1: Shared Canonical Profile & Compiler Infrastructure**  
   - Define unified `CanonicalCandidateProfile`.
   - Build `TypstCompiler` to convert profiles into pixel-perfect PDFs.
2. **Phase 2: Robust Parser with OCR Engine**  
   - Add Tesseract OCR fallback for scanned PDFs.
   - Separate LLM parsing from passage chunking.
3. **Phase 3: Production Tailoring & Truthfulness Validator**  
   - Build AI bullet rewriter with strict deterministic validation ensuring zero hallucinated experience.
