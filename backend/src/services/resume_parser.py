import json
import logging
from typing import Dict, Any
from src.utils.llm_router import LLMRouter
from src.utils.document_extractor import DocumentTextExtractor

logger = logging.getLogger("resume_parser")

class ResumeParserService:
    def __init__(self):
        self.llm = LLMRouter()

    def parse_resume(self, file_path: str) -> Dict[str, Any]:
        """Extract structured resume data using LLMRouter with schema enforcement."""
        logger.info(f"Extracting raw text from resume: {file_path}")
        raw_text = DocumentTextExtractor.extract_text(file_path)
        
        if not raw_text.strip():
            raise ValueError("No text content could be extracted from the resume file.")

        logger.info("Parsing resume text using LLMRouter...")
        system_prompt = (
            "You are an expert resume parsing assistant.\n"
            "Your task is to convert the raw resume text into a highly structured JSON profile.\n"
            "Enforce normalization rules:\n"
            "1. Technologies: Normalize names (e.g. 'React', 'ReactJS', 'React.js' -> 'React.js'; "
            "'Node', 'NodeJS', 'Node.js' -> 'Node.js'; 'Python3' -> 'Python').\n"
            "2. Dates: Format consistently as 'MMM YYYY' (e.g. 'Jan 2024') or 'Present'.\n"
            "3. Deduplication: Remove all duplicate skills.\n"
            "4. Quality: Do not hallucinate or guess fields. If not present in the text, leave it null or empty list.\n"
            "5. Maintain exactly the requested JSON output structure."
        )

        user_prompt = f"Raw Resume Text:\n---\n{raw_text}\n---"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Enforce json_object response format
        schema = {
            "type": "json_object"
        }

        try:
            # We add a specific instruction inside the user message to guide schema parameters
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
                '      "technologies": [string]\n'
                "    }\n"
                "  ],\n"
                '  "projects": [\n'
                "    {\n"
                '      "name": string,\n'
                '      "description": string or null,\n'
                '      "technologies": [string],\n'
                '      "github_link": string or null,\n'
                '      "live_link": string or null\n'
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
            return self._normalize_empty_sections(parsed_data)

        except Exception as e:
            logger.error(f"Failed to parse resume: {e}")
            raise RuntimeError(f"Resume parsing failure: {str(e)}")

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
