import json
import logging
from typing import Dict, Any, List
from src.utils.llm_router import LLMRouter
from src.utils.document_extractor import DocumentTextExtractor

logger = logging.getLogger("profile_extractor")

class ProfileExtractionService:
    def __init__(self):
        self.llm = LLMRouter()

    def extract_profile(self, file_path: str) -> Dict[str, Any]:
        """Extract structured canonical candidate profile from resume/document text, including expanded fields and RAG embedding documents."""
        logger.info(f"Extracting raw text from file: {file_path}")
        raw_text = DocumentTextExtractor.extract_text(file_path)
        
        if not raw_text.strip():
            raise ValueError("No text content could be extracted from the document.")

        logger.info("Extracting structured candidate profile using LLMRouter...")
        system_prompt = (
            "You are an expert profile extraction assistant.\n"
            "Your task is to convert the raw document text into a canonical candidate profile JSON object.\n"
            "Enforce normalization rules:\n"
            "1. Technologies: Normalize names (e.g. 'React', 'ReactJS', 'React.js' -> 'React.js'; "
            "'Node', 'NodeJS', 'Node.js' -> 'Node.js'; 'Python3' -> 'Python').\n"
            "2. Dates: Preserve the SOURCE TEXT's own granularity -- never invent a month that isn't in the "
            "original. If the source gives 'MMM YYYY' (e.g. 'Feb 2026'), output 'MMM YYYY'. If the source gives "
            "ONLY a bare year (e.g. education showing '2022 -- 2026' with no month anywhere), output the bare "
            "year ('2022', '2026') -- do NOT format it as 'Jan 2022'/'Dec 2026'. Getting this wrong is a factual "
            "error, not a style choice: it invents a specific month the candidate never stated. 'Present' stays "
            "as 'Present' when the source uses that word (not a real date, don't invent one).\n"
            "3. Deduplication: Remove all duplicate skills.\n"
            "4. Quality: Do not hallucinate or guess fields. If not present in the text, leave it null or empty list.\n"
            "5. Maintain exactly the requested JSON output structure.\n"
            "6. TECHNOLOGIES/SKILLS WHITELIST — this rule applies ONLY to terms you are inferring from bullet "
            "PROSE (a technology mentioned in passing while describing what was built). It does NOT apply to a "
            "term the candidate ALREADY put in an explicit, self-curated list: their own 'Skills'/'Technical "
            "Skills' section, or a project header line like 'ProjectName | Tech1, Tech2, Tech3'. Those lists are "
            "the candidate's own deliberate skill claim -- extract them near-verbatim (normalize naming per rule "
            "1, dedupe per rule 3, but do NOT run the transferability test below on them and do NOT drop an entry "
            "because it looks like a technique/protocol/generic name). Getting this wrong silently deletes a "
            "skill the candidate explicitly listed themselves, which is worse than including a borderline one.\n"
            "   Also: if the candidate wrote a joined/slash label as ONE item (e.g. 'OpenAI/Gemini/Groq APIs', "
            "'Cloudflare (R2, DNS)'), keep it as ONE array entry -- do not split it into separate items per "
            "provider/service.\n"
            "   For terms you're inferring ONLY from bullet prose (not present in a Skills section or stack "
            "header), before adding a term, ask: 'would this candidate list this on a different resume, for a "
            "different job, as a transferable skill?' If no, leave it out. This means EXCLUDING all of the "
            "following when they appear ONLY in bullet prose (never exclude them if they also appear in an "
            "explicit Skills section or stack header per the paragraph above):\n"
            "   - Protocol/spec/standard names the candidate implemented or worked with (e.g. 'ASTERIX CAT048', "
            "'EUROCONTROL spec', 'OAuth PKCE' as a spec) — these describe WHAT the candidate built, not a "
            "reusable tool. Note: an underlying real technology used to build it (e.g. 'Playwright', 'FastAPI') "
            "still belongs in the list; only the protocol/standard/spec name itself is excluded.\n"
            "   - Third-party product/brand names mentioned only as an integration TARGET, not something the "
            "candidate has skill IN (e.g. a bullet about building OAuth login 'for Claude, Codex, Grok, GitHub "
            "Copilot' means those are clients being integrated with, not the candidate's own skills — 'OAuth "
            "PKCE' as an implementation technique may qualify, the four product names do not).\n"
            "   - Implementation concepts, workflow descriptions, or techniques copied from bullet prose (e.g. "
            "'binary stream parser', 'human-in-the-loop', 'Persistent Memory', 'LLM context', 'weighted deltas', "
            "'ML pipeline') — these are what the candidate did, not a tool name.\n"
            "   - Generic algorithm/output-format names with no ecosystem of their own (e.g. 'SHA256' is a hash "
            "function, not a technology skill; 'REST APIs' as a bare, unqualified phrase is too generic — prefer "
            "the actual framework used to build them if named in the text).\n"
            "   - Company/product names the candidate integrated WITH rather than built, unless the role was "
            "literally administering that platform (e.g. 'Greenhouse', 'Lever', 'Ashby' listed because the "
            "candidate built automation THAT TARGETS those ATS platforms are the subject matter of the work, not "
            "a skill the candidate has in using them as an end-user — do not list them as standalone skills).\n"
            "When genuinely unsure whether a term qualifies, leave it out — an incomplete skills list is honest; "
            "an inflated one is not."
        )

        user_prompt = f"Raw Document Text:\n---\n{raw_text}\n---"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        schema = {
            "type": "json_object"
        }

        try:
            instructions = (
                "\n\nProduce a JSON object matching this schema structure:\n"
                "{\n"
                '  "personal_info": {\n'
                '    "full_name": string or null,\n'
                '    "email": string or null,\n'
                '    "phone": string or null,\n'
                '    "location": string or null,\n'
                '    "linkedin": string or null,\n'
                '    "github": string or null,\n'
                '    "portfolio": string or null\n'
                "  },\n"
                '  "summary": string or null,\n'
                '  "education": [\n'
                "    {\n"
                '      "institution": string,\n'
                '      "degree": string or null,\n'
                '      "field_of_study": string or null,\n'
                '      "gpa": string or null,\n'
                '      "start_date": string or null,\n'
                '      "end_date": string or null,\n'
                '      "location": string or null\n'
                "    }\n"
                "  ],\n"
                '  "experience": [\n'
                "    {\n"
                '      "company": string,\n'
                '      "role": string,\n'
                '      "employment_type": string or null,\n'
                '      "location": string or null,\n'
                '      "start_date": string or null,\n'
                '      "end_date": string or null,\n'
                '      "current_position": boolean,\n'
                '      "bullet_points": [string],\n'
                '      "technologies": [string],\n'
                '      "achievements": [string],\n'
                '      "domains": [string],\n'
                '      "keywords": [string]\n'
                "    }\n"
                "  ],\n"
                '  "projects": [\n'
                "    {\n"
                '      "name": string,\n'
                '      "description": string or null,\n'
                '      "bullet_points": [string] (one entry per bullet/achievement line describing this project — mirror the source document\'s own bullets verbatim rather than summarizing them into skills_demonstrated),\n'
                '      "technologies": [string],\n'
                '      "github_link": string or null,\n'
                '      "live_link": string or null,\n'
                '      "skills_demonstrated": [string],\n'
                '      "domains": [string]\n'
                "    }\n"
                "  ],\n"
                '  "skills": {\n'
                '    "Languages & Backend": [string] (programming languages, backend frameworks, '
                'databases, ORMs/query builders -- e.g. Python, FastAPI, PostgreSQL, Redis),\n'
                '    "Frontend": [string] (frontend frameworks, UI libraries, styling -- e.g. React, '
                'Tailwind CSS, Vite),\n'
                '    "AI & Agents": [string] (AI/ML frameworks, agent frameworks, retrieval/embedding '
                'techniques, named LLM provider APIs -- e.g. LangGraph, RAG, OpenAI API. Do NOT include '
                'bare "LLM" alone -- name the actual provider/framework instead),\n'
                '    "Infra & Tools": [string] (cloud platforms, deployment/CI tooling, containers, '
                'version control, dev tools -- e.g. Docker, GCP, Git. Do NOT include build-step-only '
                'actions like "EAS Build" or a spec/protocol name),\n'
                '    "other": [string] (only for a genuine skill that doesn\'t fit any category above -- '
                'this should usually be empty)\n'
                "  },\n"
                '  "certifications": [\n'
                "    {\n"
                '      "name": string,\n'
                '      "issuer": string or null,\n'
                '      "date": string or null\n'
                "    }\n"
                "  ],\n"
                '  "achievements": [string],\n'
                '  "awards": [string],\n'
                '  "publications": [\n'
                "    {\n"
                '      "title": string,\n'
                '      "publisher": string or null,\n'
                '      "date": string or null\n'
                "    }\n"
                "  ],\n"
                '  "languages": [string],\n'
                '  "external_links": [\n'
                "    {\n"
                '      "label": string,\n'
                '      "url": string\n'
                "    }\n"
                "  ]\n"
                "}"
            )
            messages[-1]["content"] += instructions
            
            response = self.llm.chat_completion(
                messages=messages,
                temperature=0.1,
                response_format=schema,
                intent="reasoning"
            )
            
            parsed_data = json.loads(response.choices[0].message.content)
            
            # Post-process to guarantee all sections exist
            normalized_data = self._normalize_empty_sections(parsed_data)
            
            # Generate RAG Embedding Documents
            normalized_data["embedding_documents"] = self._generate_embedding_documents(normalized_data)
            normalized_data["raw_text"] = raw_text
            
            return normalized_data

        except Exception as e:
            logger.error(f"Failed to extract profile: {e}")
            raise RuntimeError(f"Profile extraction failure: {str(e)}")

    def _normalize_empty_sections(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure every requested field and structure exists to prevent UI render crashes."""
        default_structure = {
            "personal_info": {"full_name": None, "email": None, "phone": None, "location": None, "linkedin": None, "github": None, "portfolio": None},
            "summary": None,
            "education": [],
            "experience": [],
            "projects": [],
            "skills": {
                "Languages & Backend": [],
                "Frontend": [],
                "AI & Agents": [],
                "Infra & Tools": [],
                "other": []
            },
            "certifications": [],
            "achievements": [],
            "awards": [],
            "publications": [],
            "languages": [],
            "external_links": []
        }
        
        for key, default_val in default_structure.items():
            if key not in data or data[key] is None:
                data[key] = default_val
            elif isinstance(default_val, dict) and isinstance(data[key], dict):
                for sub_key, sub_val in default_val.items():
                    if sub_key not in data[key]:
                        data[key][sub_key] = sub_val
                        
        return data

    def _generate_embedding_documents(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Splits the canonical profile into formatted RAG passage documents for embeddings."""
        documents = []
        name = profile["personal_info"].get("full_name") or "Candidate"

        # 1. Identity Document
        identity_text = (
            f"Candidate: {name}\n"
            f"Location: {profile['personal_info'].get('location') or 'Not Specified'}\n"
            f"Summary: {profile.get('summary') or 'No summary provided.'}"
        )
        documents.append({
            "section": "identity",
            "text": identity_text,
            "metadata": {
                "owner": name,
                "fields": ["full_name", "location", "summary"]
            }
        })

        # 2. Education Documents
        for edu in profile.get("education", []):
            degree_str = f" pursuing a {edu.get('degree') or ''} in {edu.get('field_of_study') or ''}" if edu.get('degree') else ""
            edu_text = (
                f"Education entry for {name}:\n"
                f"Institution: {edu.get('institution')}\n"
                f"Degree/Field: {degree_str.strip()}\n"
                f"Duration: {edu.get('start_date') or ''} to {edu.get('end_date') or ''}\n"
                f"GPA: {edu.get('gpa') or 'N/A'}"
            )
            documents.append({
                "section": "education",
                "text": edu_text,
                "metadata": {
                    "institution": edu.get("institution"),
                    "degree": edu.get("degree"),
                    "gpa": edu.get("gpa")
                }
            })

        # 3. Work Experience Documents
        for exp in profile.get("experience", []):
            bullets = "\n".join([f"- {b}" for b in exp.get("bullet_points", [])])
            tech = ", ".join(exp.get("technologies", []))
            ach = ", ".join(exp.get("achievements", []))
            domains = ", ".join(exp.get("domains", []))
            
            exp_text = (
                f"Work Experience for {name}:\n"
                f"Role: {exp.get('role')} at {exp.get('company')}\n"
                f"Duration: {exp.get('start_date') or ''} to {exp.get('end_date') or 'Present'}\n"
                f"Domains: {domains or 'General software engineering'}\n"
                f"Key Responsibilities:\n{bullets}\n"
                f"Technologies Used: {tech}\n"
                f"Key Achievements: {ach}"
            )
            documents.append({
                "section": "experience",
                "text": exp_text,
                "metadata": {
                    "company": exp.get("company"),
                    "role": exp.get("role"),
                    "technologies": exp.get("technologies", []),
                    "domains": exp.get("domains", [])
                }
            })

        # 4. Project Documents
        for proj in profile.get("projects", []):
            tech = ", ".join(proj.get("technologies", []))
            skills = ", ".join(proj.get("skills_demonstrated", []))
            domains = ", ".join(proj.get("domains", []))
            
            proj_text = (
                f"Project Profile for {name}:\n"
                f"Project: {proj.get('name')}\n"
                f"Description: {proj.get('description') or ''}\n"
                f"Tech Stack: {tech}\n"
                f"Skills Demonstrated: {skills}\n"
                f"Domains: {domains}"
            )
            documents.append({
                "section": "projects",
                "text": proj_text,
                "metadata": {
                    "project_name": proj.get("name"),
                    "technologies": proj.get("technologies", []),
                    "domains": proj.get("domains", [])
                }
            })

        # 5. Skills Document
        skills_text = f"Skills directory for {name}:\n"
        for category, list_items in profile.get("skills", {}).items():
            if list_items:
                cat_label = category.replace("_", " ").title()
                skills_text += f"- {cat_label}: {', '.join(list_items)}\n"
                
        documents.append({
            "section": "skills",
            "text": skills_text.strip(),
            "metadata": {
                "categories": list(profile.get("skills", {}).keys())
            }
        })

        return documents
