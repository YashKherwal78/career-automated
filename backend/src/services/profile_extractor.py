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
            "2. Dates: Format consistently as 'MMM YYYY' (e.g. 'Jan 2024') or 'Present'.\n"
            "3. Deduplication: Remove all duplicate skills.\n"
            "4. Quality: Do not hallucinate or guess fields. If not present in the text, leave it null or empty list.\n"
            "5. Maintain exactly the requested JSON output structure."
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
                '      "technologies": [string],\n'
                '      "github_link": string or null,\n'
                '      "live_link": string or null,\n'
                '      "skills_demonstrated": [string],\n'
                '      "domains": [string]\n'
                "    }\n"
                "  ],\n"
                '  "skills": {\n'
                '    "programming_languages": [string],\n'
                '    "frameworks": [string],\n'
                '    "libraries": [string],\n'
                '    "databases": [string],\n'
                '    "cloud": [string],\n'
                '    "ai_ml": [string],\n'
                '    "developer_tools": [string],\n'
                '    "other": [string]\n'
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
                "programming_languages": [],
                "frameworks": [],
                "libraries": [],
                "databases": [],
                "cloud": [],
                "ai_ml": [],
                "developer_tools": [],
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
