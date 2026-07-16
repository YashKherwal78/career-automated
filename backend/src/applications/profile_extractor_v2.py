from src.api.db import get_connection
from src.system.logger import setup_logger
logger = setup_logger('profile_extractor_v2')
import os
import sqlite3
import json
import re
from collections import defaultdict
from src.utils.llm_router import LLMRouter

WORKSPACE_DIR = "/Users/yashkherwal/Downloads/hrmailfiles"
DATA_DIR = os.path.join(WORKSPACE_DIR, "data")
CONTEXT_DIR = os.path.join(DATA_DIR, "context")
DB_PATH = os.path.join(DATA_DIR, "crm.db")

REQUIRED_FIELDS = {
    "expected_full_time_ctc": "Compensation",
    "expected_internship_stipend": "Compensation",
    "salary_negotiable": "Compensation",
    "preferred_currency": "Compensation",
    "graduation_date": "Availability",
    "earliest_start_date": "Availability",
    "latest_start_date": "Availability",
    "available_for_internship": "Availability",
    "available_for_full_time": "Availability",
    "notice_period": "Availability",
    "english_proficiency": "Languages",
    "hindi_proficiency": "Languages",
    "other_languages": "Languages",
    "relocation": "Work Preferences",
    "travel": "Work Preferences",
    "remote": "Work Preferences",
    "hybrid": "Work Preferences",
    "onsite": "Work Preferences",
    "university": "Education",
    "degree": "Education"
}

class ProfileExtractorV2:
    def __init__(self):
        self.profile = {}
        for f in REQUIRED_FIELDS:
            self.profile[f] = {"value": None, "source": "None", "confidence": 0, "human_verified": False}
            
        # Load existing to preserve human verified fields
        existing_path = os.path.join(CONTEXT_DIR, "master_candidate_profile.json")
        if os.path.exists(existing_path):
            try:
                with open(existing_path, 'r') as f:
                    existing_data = json.load(f)
                    for k, v in existing_data.items():
                        if k in self.profile and v.get("human_verified", False):
                            self.profile[k] = v
            except Exception:
                pass
                
        self.question_frequency = defaultdict(int)
        self.llm_calls_used = 0
        self.llm_client = LLMRouter()
        self.missing_fields = []
        
    def run(self):
        logger.info("Starting Profile Extraction V2.2...")
        self._extract_from_db()
        self._extract_from_markdown()
        self._detect_gaps()
        self._llm_ambiguity_resolution()
        self._generate_reports()
        logger.info("Extraction complete.")
        
    def _extract_from_db(self):
        logger.info(" -> Extracting from crm.db (application_answer_audit)")
        if not os.path.exists(DB_PATH):
            logger.info("    [WARNING] crm.db not found.")
            return
            
        try:
            conn = get_connection()
            c = conn.cursor()
            
            # Analyze question frequency
            c.execute("SELECT question_category, normalized_answer, COUNT(*) as freq FROM application_answer_audit WHERE confidence >= 90 AND normalized_answer != 'REVIEW_REQUIRED' GROUP BY question_category, normalized_answer")
            rows = c.fetchall()
            
            for category, answer, freq in rows:
                if not category:
                    continue
                    
                # Track frequency for top missing fields report
                self.question_frequency[category] += freq
                
                # Profile Learning (Promote if 3+ occurrences)
                if freq >= 3:
                    # Map generic ATS categories to our structured profile fields
                    field_key = self._map_category_to_field(category)
                    if field_key and self.profile[field_key]["confidence"] < 100:
                        self.profile[field_key] = {
                            "value": answer,
                            "source": f"crm.db (Answered {freq} times)",
                            "confidence": 100,
                            "human_verified": False
                        }
                        logger.info(f"    [LEARNING] Promoted '{field_key}' = '{answer}' from {freq} ATS occurrences.")
                        
            conn.close()
        except Exception as e:
            logger.info(f"    [ERROR] DB extraction failed: {e}")

    def _map_category_to_field(self, category):
        cat = category.lower()
        if "salary" in cat or "compensation" in cat: return "expected_full_time_ctc"
        if "notice period" in cat: return "notice_period"
        if "graduat" in cat: return "graduation_date"
        if "relocat" in cat: return "relocation"
        return None

    def _extract_from_markdown(self):
        logger.info(" -> Extracting from markdown profiles using Regex")
        master_profile_path = os.path.join(CONTEXT_DIR, "yash_master_profile.md")
        
        if not os.path.exists(master_profile_path):
            return
            
        with open(master_profile_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regex mappings for expected explicit deterministic fields
        patterns = {
            "expected_full_time_ctc": r"Expected Full-Time Salary:\s*\*?\*?\s*([^\]\n]+)",
            "expected_internship_stipend": r"Expected Internship Stipend:\s*\*?\*?\s*([^\]\n]+)",
            "graduation_date": r"Expected Graduation Date:\s*\*?\*?\s*([^\]\n]+)",
            "notice_period": r"Notice Period:\s*\*?\*?\s*([^\]\n]+)",
            "english_proficiency": r"English:\s*\*?\*?\s*([^\]\n]+)",
            "hindi_proficiency": r"Hindi:\s*\*?\*?\s*([^\]\n]+)",
            "relocation": r"Willing To Relocate:\s*\*?\*?\s*([^\]\n]+)",
            "university": r"University:\s*\*?\*?\s*([^\]\n]+)|Indian Institute of Technology Roorkee|IIT Roorkee",
            "degree": r"Degree:\s*\*?\*?\s*([^\]\n]+)|B\.Tech"
        }
        
        for field, pattern in patterns.items():
            if self.profile[field]["confidence"] == 100:
                continue # Already confident from DB
                
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                val = match.group(1).strip() if match.groups() and match.group(1) else match.group(0).strip()
                if "PENDING USER INPUT" in val:
                    continue # Ignore placeholder
                    
                self.profile[field] = {
                    "value": val,
                    "source": "yash_master_profile.md",
                    "confidence": 95,
                    "human_verified": False
                }
                logger.info(f"    [REGEX] Found {field}: {val}")

    def _detect_gaps(self):
        for field, data in self.profile.items():
            if data["confidence"] < 70 or data["value"] is None:
                self.missing_fields.append(field)
                
    def _llm_ambiguity_resolution(self):
        logger.info(" -> Running LLM Ambiguity Resolution (Max 5 calls)")
        master_profile_path = os.path.join(CONTEXT_DIR, "yash_master_profile.md")
        if not os.path.exists(master_profile_path): return
        
        with open(master_profile_path, 'r') as f:
            content = f.read()
            
        # We only send isolated snippets to LLM based on keywords
        resolved_count = 0
        
        for missing in list(self.missing_fields):
            if self.llm_calls_used >= 5:
                logger.info("    [WARNING] LLM token budget exceeded. Stopping resolution.")
                break
                
            # Find a tiny snippet related to the missing field
            snippet = self._get_context_snippet(missing, content)
            if not snippet:
                continue
                
            self.llm_calls_used += 1
            logger.info(f"    [LLM] Attempting resolution for: {missing}...")
            prompt = f"Extract '{missing}' from this text. If ambiguous, return 'UNKNOWN'. Text: {snippet}"
            
            try:
                response = self.llm_client.chat_completion([{"role": "user", "content": prompt}], intent="utility")
                ans = response.choices[0].message.content.strip()
                if ans != 'UNKNOWN' and len(ans) < 50:
                    self.profile[missing] = {
                        "value": ans,
                        "source": "LLM Inference",
                        "confidence": 75,
                        "human_verified": False
                    }
                    self.missing_fields.remove(missing)
                    resolved_count += 1
                    logger.info(f"      -> Resolved: {ans}")
            except Exception as e:
                pass
                
    def _get_context_snippet(self, field, content):
        if "date" in field:
            idx = content.find("Date")
            if idx > 0: return content[max(0, idx-100):idx+200]
        if "currency" in field or "ctc" in field or "salary" in field:
            idx = content.find("Compensation")
            if idx > 0: return content[max(0, idx-50):idx+300]
        return None

    def _generate_reports(self):
        out_dir = "/Users/yashkherwal/.gemini/antigravity/brain/85072219-ca5f-4b8a-911f-47be32349a8b"
        
        # 1. Master Profile JSON
        with open(os.path.join(CONTEXT_DIR, "master_candidate_profile.json"), "w") as f:
            json.dump(self.profile, f, indent=4)
            
        # 2. Gaps
        with open(os.path.join(out_dir, "candidate_profile_gaps.md"), "w") as f:
            f.write("# Profile Gaps\n")
            for gap in self.missing_fields:
                f.write(f"- {gap} (Confidence < 70)\n")
                
        # 3. Candidate Questions
        with open(os.path.join(out_dir, "candidate_questions.md"), "w") as f:
            f.write("# Please Provide the Following Information:\n\n")
            for i, q in enumerate(self.missing_fields[:10]):
                f.write(f"{i+1}. What is your {q.replace('_', ' ')}? (Missing Field: {q})\n")
                
        # 4. Top Missing Fields (from DB frequency)
        with open(os.path.join(out_dir, "top_missing_fields.md"), "w") as f:
            f.write("# Top Requested ATS Questions\n\n")
            for cat, count in sorted(self.question_frequency.items(), key=lambda x: x[1], reverse=True)[:15]:
                f.write(f"- {cat}: {count} occurrences\n")
                
        # 5. Extraction Report
        total_fields = len(REQUIRED_FIELDS)
        missing_count = len(self.missing_fields)
        coverage = ((total_fields - missing_count) / total_fields) * 100
        
        with open(os.path.join(out_dir, "profile_extraction_report.md"), "w") as f:
            f.write("# Profile Extraction Report V2.2\n\n")
            f.write(f"- **Fields Extracted**: {total_fields - missing_count}\n")
            f.write(f"- **Fields Missing**: {missing_count}\n")
            f.write(f"- **Profile Coverage Score**: {coverage:.1f}%\n")
            f.write(f"- **LLM Calls Used**: {self.llm_calls_used}/5\n")
            
        logger.info(f"Generated reports in artifacts dir. Coverage: {coverage:.1f}%")

if __name__ == "__main__":
    extractor = ProfileExtractorV2()
    extractor.run()
