import re
import json
from src.applications.profile import ProfileManager
from src.config.config import Config
from src.utils.llm_router import LLMRouter

class SalaryEngineV1:
    @staticmethod
    def calculate(role: str, location: str) -> dict:
        """
        Deterministic salary calculation based on location and role.
        Targeting 75th percentile for given role/geography.
        """
        loc = location.lower()
        role_low = role.lower()
        
        # Base multiplier based on geography
        if "us" in loc or "united states" in loc or "remote us" in loc:
            base = 100000
            currency = "$"
        elif "uk" in loc or "london" in loc:
            base = 65000
            currency = "£"
        elif "europe" in loc or "germany" in loc or "france" in loc:
            base = 70000
            currency = "€"
        else:
            # Default to India compensation as fallback/base
            base = 1500000 # INR
            currency = "₹"
            
        # Role Multipliers
        if "senior" in role_low or "lead" in role_low:
            multiplier = 1.5
        elif "associate" in role_low or "junior" in role_low:
            multiplier = 0.8
        elif "intern" in role_low:
            multiplier = 0.4
        else:
            multiplier = 1.0 # Mid-level
            
        # Family Multipliers
        if "data scientist" in role_low or "ai engineer" in role_low:
            multiplier *= 1.2
        elif "product manager" in role_low:
            multiplier *= 1.3
        
        target = int(base * multiplier)
        # Round to nearest logical boundary
        if currency == "₹":
            target = round(target / 100000) * 100000 # Nearest Lakh
            formatted_target = f"{currency}{target/100000:g} LPA"
            formatted_range = f"{currency}{(target-200000)/100000:g} LPA - {currency}{(target+200000)/100000:g} LPA"
        else:
            target = round(target / 5000) * 5000 # Nearest 5k
            formatted_target = f"{currency}{target:,}"
            formatted_range = f"{currency}{target-10000:,} - {currency}{target+15000:,}"
            
        return {
            "expected_salary": formatted_target,
            "salary_range": formatted_range,
            "confidence": 0.85
        }

class LocationResolver:
    PRIORITY_LOCATIONS = ["gurgaon", "gurugram", "bangalore", "bengaluru", "noida", "delhi", "pune", "navi mumbai", "hyderabad", "mumbai"]
    
    @staticmethod
    def is_location_question(question: str) -> bool:
        q_lower = question.lower()
        keywords = ["preferred office", "preferred location", "work location", "office preference", "top location preference", "location preference", "which office"]
        return any(kw in q_lower for kw in keywords)
        
    @staticmethod
    def resolve(question: str, options: list) -> dict:
        if not options:
            return {"selected_location": "REVIEW_REQUIRED", "confidence": 0, "reasoning": "No options available"}
            
        opts_lower = {str(opt).lower(): opt for opt in options}
        
        # Step 1: Priority Match
        for pref in LocationResolver.PRIORITY_LOCATIONS:
            for opt_l, opt_orig in opts_lower.items():
                if pref in opt_l:
                    return {"selected_location": opt_orig, "confidence": 100, "reasoning": f"Matched priority location: {pref}"}
                    
        # Step 2: Remote Check
        for opt_l, opt_orig in opts_lower.items():
            if "remote" in opt_l or "anywhere" in opt_l:
                return {"selected_location": opt_orig, "confidence": 100, "reasoning": "Remote option available"}
                
        # Step 3: India Check
        india_keywords = ["india", "in", "ind"]
        for opt_l, opt_orig in opts_lower.items():
            words = opt_l.split()
            if any(kw == w.strip(",.") for kw in india_keywords for w in words):
                return {"selected_location": opt_orig, "confidence": 100, "reasoning": "India option available"}
                
        # Step 4: First Available Fallback (Candidate is open to relocation)
        first_opt = options[0]
        # Just in case the first option is a placeholder like "Please Select"
        if len(options) > 1 and "select" in str(first_opt).lower():
            first_opt = options[1]
            
        return {"selected_location": first_opt, "confidence": 80, "reasoning": "Candidate is willing to relocate. Selecting first available location."}

class QuestionClassifier:
    @staticmethod
    def classify(question: str) -> str:
        q_lower = question.lower()
        
        # 1. KNOCKOUT
        knockout_keywords = ["sponsorship", "authorized to work", "visa", "relocate", "relocation", "willing to relocate"]
        if any(kw in q_lower for kw in knockout_keywords):
            return "KNOCKOUT"
            
        # 2. LEGAL
        legal_keywords = ["veteran", "disability", "gender", "sex", "race", "hispanic", "latino", "criminal", "felony", "background", "bgv", "consent", "identify as"]
        if any(kw in q_lower for kw in legal_keywords):
            return "LEGAL"
            
        # 3. COMPENSATION
        comp_keywords = ["salary", "compensation", "expected pay", "rate", "remuneration"]
        if any(kw in q_lower for kw in comp_keywords):
            return "COMPENSATION"
            
        # 4. PROFILE
        profile_keywords = ["notice period", "start date", "graduation", "passout", "expected graduation", "school", "university", "linkedin", "portfolio", "github", "website", "organisation", "organization", "current role", "years of experience", "relative", "family member", "related party", "previously employed", "former employee", "previously been employed", "employer", "company", "institute", "college", "degree", "education", "travel", "first name", "last name", "email", "phone", "location", "city", "country", "state", "reside", "hear about", "source", "how did you find out", "referral"]
        if any(kw in q_lower for kw in profile_keywords):
            essay_hints = ["describe", "tell me about", "explain", "essay"]
            if any(kw in q_lower for kw in essay_hints):
                return "PROFILE_ESSAY"
            return "PROFILE_FACT"
            
        # 5. MOTIVATION
        motivation_keywords = ["why do you want to", "why are you interested", "what excites you"]
        if any(kw in q_lower for kw in motivation_keywords):
            return "MOTIVATION"
            
        # 6. BEHAVIORAL
        behavioral_keywords = ["tell me about a time", "describe a situation", "greatest challenge", "proudest"]
        if any(kw in q_lower for kw in behavioral_keywords):
            return "BEHAVIORAL"
            
        # 7. TECHNICAL (Fallback for complex custom questions)
        # We classify long questions or questions about specific technologies as technical.
        return "TECHNICAL"

class ResponseNormalizer:
    _dropdown_cache = {}

    @staticmethod
    def _semantic_rule_match(ans_lower: str, options: list) -> str:
        # Rule definitions based on intent -> option
        rules = {
            "yes": ["agree", "accept", "consent", "authorized", "eligible to work", "relocate", "open to relocation", "yes", "true", "y", "1"],
            "no": ["not authorized", "require sponsorship", "disagree", "no", "false", "n", "0"]
        }
        
        for option_key, intent_keywords in rules.items():
            if any(kw in ans_lower for kw in intent_keywords):
                for opt in options:
                    if option_key in str(opt).lower():
                        return opt
        
        # Notice Period and CTC rules
        if "immediate" in ans_lower or ans_lower == "0":
            for opt in options:
                opt_l = str(opt).lower()
                if "immediate" in opt_l or "0" in opt_l or "15 days" in opt_l:
                    return opt
        if "15" in ans_lower or ans_lower == "15":
            for opt in options:
                opt_l = str(opt).lower()
                if "15 days" in opt_l or "less than 30" in opt_l or "0-15" in opt_l:
                    return opt
                    
        return None

    @staticmethod
    def _llm_fallback(raw_answer: str, options: list, label_text: str, llm_client) -> str:
        if not llm_client:
            return "REVIEW_REQUIRED"
            
        print(f"[Dropdown] Attempting LLM Fallback (Groq) for: '{label_text}'")
        
        prompt = f"""
You are mapping an applicant's intent to a required dropdown field.
Question/Label: {label_text}
Applicant Intent: {raw_answer}
Available Options: {options}

Select the single best option that semantically matches the intent.
Output strictly in JSON format.
Example: {{"selected_option": "Yes", "confidence": 95, "reasoning": "Intent explicitly agrees."}}
"""
        messages = [
            {"role": "system", "content": "You are a precise data mapping engine."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # Force intent="utility" which defaults to Groq
            response = llm_client.chat_completion(
                messages=messages, 
                temperature=0.0, 
                response_format={"type": "json_object"}, 
                intent="utility"
            )
            
            import json
            data = json.loads(response.choices[0].message.content)
            selected = data.get("selected_option")
            conf = data.get("confidence", 0)
            reason = data.get("reasoning", "")
            
            if conf > 90 and selected in options:
                print(f"  -> LLM Fallback (Groq) mapped '{selected}' with >90% conf.")
                return selected
            elif conf >= 60 and selected in options:
                print(f"  -> LLM Fallback (Groq) mapped '{selected}' with {conf}% conf. Reason: {reason}")
                return selected
            else:
                print(f"  -> LLM Fallback (Groq) returned confidence {conf} < 60%. REVIEW_REQUIRED.")
                return "REVIEW_REQUIRED"
                
        except Exception as e:
            print(f"[Dropdown] LLM Fallback Failed: {e}")
            return "REVIEW_REQUIRED"

    @staticmethod
    def normalize(
        raw_answer: str, 
        classification: str, 
        field_type: str = "text", 
        placeholder: str = "", 
        label_text: str = "", 
        options: list = None,
        llm_client = None
    ) -> str:
        if not raw_answer:
            if options and isinstance(options, list) and len(options) > 0:
                for opt in options:
                    opt_str = str(opt).lower()
                    if "decline" in opt_str or "wish to answer" in opt_str or "prefer not" in opt_str or "prefer to self-describe" in opt_str:
                        return opt
                return options[-1]
            return ""
            
        ans = str(raw_answer).strip()
        hints = (placeholder + " " + label_text).lower()

        # 1. Dropdowns
        if options and isinstance(options, list) and len(options) > 0:
            ans_lower = ans.lower()
            
            # Cache Check
            cache_key = f"{label_text}_{ans_lower}_{str(options)}"
            if cache_key in ResponseNormalizer._dropdown_cache:
                print(f"  -> Cache Hit: {ResponseNormalizer._dropdown_cache[cache_key]}")
                return ResponseNormalizer._dropdown_cache[cache_key]
            
            # Phase A: Exact Match
            for opt in options:
                if ans_lower == str(opt).lower().strip():
                    ResponseNormalizer._dropdown_cache[cache_key] = opt
                    return opt
                    
            # Phase B: Semantic Rule Match
            rule_match = ResponseNormalizer._semantic_rule_match(ans_lower, options)
            if rule_match:
                ResponseNormalizer._dropdown_cache[cache_key] = rule_match
                return rule_match
                
            # Phase C: LLM Fallback Match
            llm_match = ResponseNormalizer._llm_fallback(raw_answer, options, hints, llm_client)
            if llm_match and llm_match != "REVIEW_REQUIRED":
                ResponseNormalizer._dropdown_cache[cache_key] = llm_match
                return llm_match
            
            # Phase D: Safe Fallback
            for opt in options:
                opt_str = str(opt).lower()
                if "decline" in opt_str or "wish to answer" in opt_str or "prefer not" in opt_str or "prefer to self-describe" in opt_str:
                    return opt
            
            return "REVIEW_REQUIRED"

        # If options are provided but we somehow skipped the block above (shouldn't happen),
        # enforce the rule: never return free-form text for dropdowns.
        if field_type in ["dropdown", "multiselect", "radio", "checkbox"] and options:
            return "REVIEW_REQUIRED"


        # 2. Boolean
        if ans.lower() in ["yes", "no", "true", "false", "y", "n"]:
            if "true/false" in hints:
                return "True" if ans.lower() in ["yes", "y", "true"] else "False"
            if "y/n" in hints:
                return "Y" if ans.lower() in ["yes", "y", "true"] else "N"
            return "Yes" if ans.lower() in ["yes", "y", "true"] else "No"

        # 3. Date Engine (Priority 4)
        date_keywords = ["date", "mm/yyyy", "yyyy", "mm-dd-yyyy", "dd-mm-yyyy", "month", "year", "when did you"]
        if any(kw in hints for kw in date_keywords) and not options:
            import dateutil.parser
            from datetime import datetime
            
            try:
                # Try to parse the raw answer
                parsed_date = dateutil.parser.parse(ans)
                
                # Determine format from hints
                if "mm/yyyy" in hints:
                    return parsed_date.strftime("%m/%Y")
                elif "yyyy-mm-dd" in hints:
                    return parsed_date.strftime("%Y-%m-%d")
                elif "mm-dd-yyyy" in hints:
                    return parsed_date.strftime("%m-%d-%Y")
                elif "dd-mm-yyyy" in hints or "dd/mm/yyyy" in hints:
                    return parsed_date.strftime("%d-%m-%Y")
                elif "yyyy" in hints:
                    return parsed_date.strftime("%Y")
                elif "month" in hints and "year" not in hints:
                    return parsed_date.strftime("%B")
                
                # Default format if not specified but date is expected
                return parsed_date.strftime("%Y-%m-%d")
                
            except Exception:
                # Could not parse or resolve format
                return "REVIEW_REQUIRED"

        # 4. Salary / Compensation
        if classification == "COMPENSATION":
            # Extract purely numbers
            numbers = re.sub(r'[^\d.]', '', ans)
            if not numbers:
                return "NORMALIZATION_FAILED"
            val = float(numbers)
            
            # If LPA hint
            if "lpa" in hints:
                # If they passed 1500000, convert to 15
                if val > 1000:
                    val = val / 100000
                return str(int(val) if val.is_integer() else val)
                
            # If INR / USD hint but field requires numbers
            if field_type == "number" or "numeric" in hints:
                return str(int(val) if val.is_integer() else val)
                
            # Return raw if text field without specific hints
            return ans

        # 4. Experience
        if "years of experience" in hints or "experience" in hints:
            # e.g. "1.5 years" -> "1.5"
            match = re.search(r'(\d+(\.\d+)?)', ans)
            if match:
                num = float(match.group(1))
                if field_type == "number" or "number" in hints or "numeric" in hints:
                    return str(int(num) if num.is_integer() else num)
                return str(int(num) if num.is_integer() else num)
            return "NORMALIZATION_FAILED"

        # 5. Notice Period
        if "notice period" in hints or "start" in hints:
            # Extract number
            match = re.search(r'(\d+)', ans)
            if match:
                val = int(match.group(1))
                # Base normalization to days (assume raw answer is in days if "Immediate" -> 0)
                if ans.lower() == "immediate":
                    days = 0
                elif "month" in ans.lower():
                    days = val * 30
                elif "week" in ans.lower():
                    days = val * 7
                else:
                    days = val
                    
                # Format to requested unit
                if "month" in hints:
                    out = days / 30
                    return str(int(out) if out.is_integer() else out)
                if "week" in hints:
                    out = days / 7
                    return str(int(out) if out.is_integer() else out)
                # If day is in hints, or no other unit specified, return days
                return str(days)
            
            # If "Immediate" and asks for days
            if ans.lower() == "immediate":
                if "day" in hints or field_type == "number": return "0"

        # 6. Date Normalization
        if "date" in hints or "year" in hints or "month" in hints or "yyyy" in hints:
            # Simplified for now. If it wants YYYY and answer is June 2026 -> 2026
            year_match = re.search(r'(\d{4})', ans)
            if year_match:
                if "yyyy" in hints and "mm" not in hints:
                    return year_match.group(1)
                # Map months
                months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
                month_num = "01"
                for i, m in enumerate(months):
                    if m in ans.lower():
                        month_num = f"{i+1:02d}"
                        break
                if "mm/yyyy" in hints:
                    return f"{month_num}/{year_match.group(1)}"
                if "mm-yyyy" in hints:
                    return f"{month_num}-{year_match.group(1)}"
                    
                # If there's a year match and it's a date field but no format is specified
                if field_type == "date":
                    return ans

        # Default fallback
        if field_type == "number":
            numbers = re.sub(r'[^\d.]', '', ans)
            if not numbers:
                return "NORMALIZATION_FAILED"
            return str(int(float(numbers)) if float(numbers).is_integer() else numbers)
            
        return ans

class QuestionEngine:
    def __init__(self, profile_manager, rag_client, llm_client, company_context: str, job_title: str):
        self.profile = profile_manager
        self.rag = rag_client
        self.llm_client = llm_client
        self.company_context = company_context
        self.job_title = job_title
        self.audit_log = []

    def log_decision(self, question: str, classification: str, source: str, raw: str, normalized: str, metadata: dict = None):
        if metadata is None: metadata = {}
        self.audit_log.append({
            "question": question,
            "classification": classification,
            "answer_source": source,
            "raw_answer": raw,
            "normalized_answer": normalized,
            "confidence": metadata.get("confidence", 0),
            "css_selector": metadata.get("css_selector", ""),
            "input_tag": metadata.get("input_tag", ""),
            "required": metadata.get("required", False),
            "visible": metadata.get("visible", True),
            "disabled": metadata.get("disabled", False),
            "field_label": metadata.get("label_text", ""),
            "field_type": metadata.get("field_type", ""),
            "placeholder": metadata.get("placeholder", ""),
            "options": metadata.get("options", []),
            "current_value": metadata.get("current_value", ""),
            "final_value": metadata.get("final_value", ""),
            "validation_error": metadata.get("validation_error", "")
        })

    def answer(
        self, 
        question: str, 
        field_type: str = "text", 
        placeholder: str = "", 
        options: list = None,
        label_text: str = "",
        required: bool = False,
        dom_meta: dict = None
    ) -> str:
        """
        Generates and normalizes an answer using Candidate RAG + LLM with Deterministic Normalization V5.
        """
        if dom_meta is None: dom_meta = {}
        
        classification = QuestionClassifier.classify(question)
        raw_answer = ""
        source = ""
        confidence = 100
        
        q_lower = question.lower()
        hints = (placeholder + " " + label_text).lower()
        
        dom_meta["llm_tokens_used"] = 0
        dom_meta["profile_lookup_used"] = False
        dom_meta["retrieved_chunks"] = 0
        
        # V2.1 Location Resolver Intercept
        if options and field_type in ["dropdown", "multiselect", "native_select", "react_select"] and LocationResolver.is_location_question(q_lower):
            loc_result = LocationResolver.resolve(question, options)
            
            # Telemetry for location forensics
            if "location_forensics" not in dom_meta:
                dom_meta["location_forensics"] = []
            
            # Because dom_meta is technically an item in telemetry['interaction_log'] usually, 
            # we'll just log it clearly to console which gets picked up, and set the value.
            print(f"\n[LocationResolver]")
            print(f"  -> Question: {question}")
            print(f"  -> Options: {options}")
            print(f"  -> Selected: {loc_result['selected_location']}")
            print(f"  -> Reasoning: {loc_result['reasoning']} (Conf: {loc_result['confidence']})")
            
            normalized = loc_result["selected_location"]
            dom_meta["confidence"] = loc_result["confidence"]
            dom_meta["final_value"] = normalized
            self.log_decision(question, "LOCATION_RESOLVER", "LocationResolver", "", normalized, metadata=dom_meta)
            return normalized

        # V5 DETERMINISTIC NORMALIZATION RULES
        is_binary_dropdown = False
        if field_type in ["dropdown", "multiselect", "radio_or_checkbox", "checkbox_group", "radio_group"] or dom_meta.get("widget_type") in ["react_select", "native_select", "radio_group", "checkbox_group"]:
            if options:
                opts_lower = [str(o).lower() for o in options]
                if set(["yes", "no"]).issubset(set(opts_lower)) or set(["true", "false"]).issubset(set(opts_lower)) or set(["accept", "decline"]).issubset(set(opts_lower)):
                    is_binary_dropdown = True
        
        def apply_deterministic_fallback():
            ans = ""
            if "sponsor" in q_lower or "visa" in q_lower: ans = "No"
            elif "authoriz" in q_lower or "work auth" in q_lower: ans = "Yes"
            elif "previously employed" in q_lower or "former employee" in q_lower or "employed by stripe" in q_lower: ans = "No"
            elif "whatsapp" in q_lower: ans = "Yes"
            elif "background" in q_lower or "bgv" in q_lower: ans = "Yes"
            elif "relocat" in q_lower: ans = "Yes"
            elif "travel" in q_lower: ans = "Yes"
            elif "remote" in q_lower: ans = "Yes"
            return ans

        # Add robust check for is_binary_dropdown
        if options:
            opts_lower = [str(o).lower() for o in options]
            if "yes" in opts_lower and "no" in opts_lower:
                is_binary_dropdown = True
                
        # Force deterministic evaluation for problem fields
        aggressive_keywords = ["sponsor", "visa", "authoriz", "work auth", "previously employed", "employed by stripe", "whatsapp", "background", "bgv", "relocat", "travel", "remote"]
        if any(kw in q_lower for kw in aggressive_keywords):
            is_binary_dropdown = True

        if is_binary_dropdown:
            det_ans = apply_deterministic_fallback()
            if det_ans:
                raw_answer = det_ans
                source = "Deterministic Logic"
                dom_meta["profile_lookup_used"] = True

        # TYPE 1: PROFILE FACTS (0 LLM Calls)
        type_1_classes = ["KNOCKOUT", "LEGAL", "COMPENSATION", "PROFILE"]
        if not raw_answer and classification in type_1_classes + ["PROFILE_FACT"]:
            source = "CandidateProfile"
            dom_meta["profile_lookup_used"] = True
            
            # Step 1: Canonical Field Detection
            canonical_field = None
            
            # Education
            if any(kw in q_lower or kw in hints for kw in ["university", "college", "school"]):
                canonical_field = "EDUCATION_INSTITUTION"
            elif any(kw in q_lower or kw in hints for kw in ["degree", "qualification", "education"]):
                canonical_field = "DEGREE"
                
            # Employment
            elif any(kw in q_lower or kw in hints for kw in ["current employer", "present employer", "current organization"]):
                canonical_field = "CURRENT_ORGANIZATION"
            elif any(kw in q_lower or kw in hints for kw in ["previous employer", "former employer"]):
                canonical_field = "PREVIOUS_ORGANIZATION"
            elif any(kw in q_lower or kw in hints for kw in ["employer", "company", "organization"]):
                canonical_field = "EMPLOYMENT_HISTORY"
                
            # Location
            elif any(kw in q_lower or kw in hints for kw in ["preferred location", "office preference", "work location", "which office"]):
                # These are preference questions, DO NOT use CURRENT_LOCATION.
                # If they are dropdowns, LocationResolver handles them. If text, we should return the highest priority.
                canonical_field = "PREFERRED_LOCATION"
                raw_answer = LocationResolver.PRIORITY_LOCATIONS[0].title() # e.g. "Gurgaon"
            elif any(kw in q_lower or kw in hints for kw in ["residence location", "current residence", "where do you live", "current location", "reside"]):
                canonical_field = "CURRENT_LOCATION"
                raw_answer = self.profile.get_field("location")
            elif any(kw in q_lower or kw in hints for kw in ["location"]):
                canonical_field = "LOCATION"
            elif any(kw in q_lower or kw in hints for kw in ["city", "current city", "location city", "location (city)"]):
                canonical_field = "CITY"
            elif any(kw in q_lower or kw in hints for kw in ["country", "nationality", "residence country", "reside"]):
                canonical_field = "COUNTRY"
                
            # Logistics/Legal
            elif "notice period" in hints:
                canonical_field = "NOTICE_PERIOD"
            elif "sponsorship" in hints or "visa" in hints:
                canonical_field = "VISA_REQUIREMENT"
            elif "authorized" in hints or "work authorization" in hints:
                canonical_field = "WORK_AUTHORIZATION"
                
            # Personal
            elif "linkedin" in hints:
                canonical_field = "LINKEDIN"
            elif "phone" in hints:
                canonical_field = "PHONE"
            elif "email" in hints:
                canonical_field = "EMAIL"
            
            # Languages
            elif any(kw in q_lower or kw in hints for kw in ["language", "speak", "proficienc"]):
                canonical_field = "LANGUAGE"
                
            # Availability / Dates
            elif any(kw in q_lower or kw in hints for kw in ["start date", "earliest start", "latest start", "when can you start", "available to start"]):
                canonical_field = "START_DATE"
            elif any(kw in q_lower or kw in hints for kw in ["graduation date", "passout", "expected graduation", "end date"]):
                canonical_field = "GRADUATION_DATE"
                
            # Hotfix V2.2 Additions
            elif any(kw in q_lower or kw in hints for kw in ["years of experience", "how many years"]):
                canonical_field = "EXPERIENCE"
            elif any(kw in q_lower or kw in hints for kw in ["hear about", "source", "how did you find out"]):
                canonical_field = "SOURCE"
                
            # Other mappings (Legacy)
            elif "relative" in hints or "family member" in hints or "related party" in hints:
                raw_answer = "Yes" if self.profile.get_field("has_relative_in_company") else "No"
            elif "previously employed" in hints or "former employee" in hints or "previously been employed" in q_lower:
                raw_answer = "Yes" if self.profile.get_field("previously_employed") else "No"
            elif classification == "COMPENSATION":
                raw_answer = str(self.profile.get_field("expected_salary"))

            # Step 2: Profile Value Lookup
            if canonical_field:
                if canonical_field == "EDUCATION_INSTITUTION":
                    raw_answer = "IIT Roorkee"
                elif canonical_field == "DEGREE":
                    raw_answer = "B.Tech Chemical Engineering"
                elif canonical_field == "CURRENT_ORGANIZATION":
                    raw_answer = "OrangeLabs"
                elif canonical_field == "PREVIOUS_ORGANIZATION":
                    raw_answer = "ScoreMe"
                elif canonical_field == "EMPLOYMENT_HISTORY":
                    raw_answer = "OrangeLabs"  # Default if they just ask "Employer"
                elif canonical_field == "RESIDENCE_LOCATION":
                    raw_answer = str(self.profile.get_field("residence_location"))
                elif canonical_field == "LOCATION":
                    raw_answer = str(self.profile.get_field("current_location"))
                elif canonical_field == "CITY":
                    raw_answer = str(self.profile.get_field("city"))
                elif canonical_field == "COUNTRY":
                    raw_answer = str(self.profile.get_field("country"))
                elif canonical_field == "EXPERIENCE":
                    raw_answer = "0"
                elif canonical_field == "SOURCE":
                    raw_answer = "LinkedIn"
                elif canonical_field == "NOTICE_PERIOD":
                    # Notice period logic
                    if field_type in ["number", "tel"] or (options and all(opt.isdigit() for opt in options)):
                        raw_answer = "0"
                    else:
                        raw_answer = "Immediate"
                elif canonical_field == "VISA_REQUIREMENT":
                    raw_answer = "Yes" if self.profile.get_field("visa_sponsorship_required") else "No"
                elif canonical_field == "WORK_AUTHORIZATION":
                    raw_answer = "Yes" if self.profile.get_field("work_authorization") else "No"
                elif canonical_field == "LINKEDIN":
                    raw_answer = str(self.profile.get_field("linkedin"))
                elif canonical_field == "PHONE":
                    raw_answer = str(self.profile.get_field("phone"))
                elif canonical_field == "EMAIL":
                    raw_answer = str(self.profile.get_field("email"))
                elif canonical_field == "LANGUAGE":
                    if "hindi" in q_lower: raw_answer = "Native"
                    elif "english" in q_lower: raw_answer = "Professional"
                    else: raw_answer = "None"
                elif canonical_field == "START_DATE":
                    raw_answer = "Immediate"
                elif canonical_field == "GRADUATION_DATE":
                    raw_answer = "May 2026"
                
        # If it's a PROFILE_FACT but failed deterministic mapping, DO NOT SEND TO LLM
        if not raw_answer and classification == "PROFILE_FACT":
            print(f"  -> [Warning] PROFILE_FACT missing deterministic mapping. Bypassing LLM.")
            return "REVIEW_REQUIRED"

        # TYPE 2, 3, 4: RAG + LLM Calls
        if not raw_answer and classification in ["MOTIVATION", "BEHAVIORAL", "TECHNICAL", "PROFILE", "PROFILE_ESSAY"]:
            source = "LLM + RAG"
            
            # Retrieve Top 3 Chunks
            retrieved_items = self.rag.retrieve(question, top_k_initial=5, top_k_final=3) if self.rag else []
            dom_meta["retrieved_chunks"] = len(retrieved_items)

            
            # Log Retrieval Scores & Check Confidence
            max_score = 0
            chunk_texts = []
            print(f"\n[Essay Debug] Question: {question}")
            for i, item in enumerate(retrieved_items):
                score = item.get("score", 0)
                text = item.get("text", "")
                if score > max_score: max_score = score
                chunk_texts.append(text)
                title = text.split("\n")[0] if "\n" in text else text[:50]
                print(f"  -> Retrieved Chunk {i+1}: {title} (Score: {score:.2f})")
                
            # If retrieval confidence is low, fallback to REVIEW_REQUIRED
            # Assuming a BM25 base score + tag boost, a score < 1.0 means practically no matching terms.
            if max_score < 1.0 and classification in ["TECHNICAL", "BEHAVIORAL"]:
                print(f"  -> [Warning] Low retrieval confidence ({max_score:.2f}). Triggering REVIEW_REQUIRED.")
                raw_answer = "REVIEW_REQUIRED"
                normalized = "REVIEW_REQUIRED"
                source = "Low_Confidence_Gate"
                confidence = 0
            else:
                chunk_text = "\n\n".join(chunk_texts)
                context_block = f"CANDIDATE PROJECTS / CONTEXT:\n{chunk_text}"
                if classification == "MOTIVATION" and self.company_context:
                    context_block += f"\n\nCOMPANY CONTEXT:\n{self.company_context}"
                    
                profile_context = self.profile.get_llm_context()
                
                SYSTEM_PROMPT = f"""
You are an automated application assistant filling out a job application for {self.profile.get_field("first_name")}.
Job Title: {self.job_title}
Candidate Profile Summary: {profile_context}

{context_block}

Instructions:
- Answer the question strictly using facts from the provided context chunks.
- Do not hallucinate external projects or experience.
- STRICT METRIC GROUNDING RULE: NEVER fabricate metrics, percentages, revenue, user counts, or business impact. 
- If the prompt asks for metrics, but there are no explicit numbers in the provided context, DO NOT INVENT THEM. Instead, answer honestly. If the entire answer relies on missing metrics, use this fallback: "I focused on building the system and validating the workflow. I do not have production metrics available for this project."
- Keep the answer concise. Maximum 50 words unless an essay is requested.
- Write in the first person ("I", "my").
- ONLY output the raw answer text. No greetings, no explanations.
"""
                current_prompt = f"Question: {question}\nOptions (if any): {options}"
                
                try:
                    response = self.llm_client.chat_completion(
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": current_prompt}
                        ],
                        temperature=0.0,
                        intent="utility"
                    )
                    raw_answer = response.choices[0].message.content.strip()
                    print(f"  -> Final LLM Answer: {raw_answer}")
                    
                    # Metric Validation
                    import re
                    chunk_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', chunk_text))
                    if options:
                        options_text = " ".join([str(o) for o in options])
                        chunk_nums.update(re.findall(r'\b\d+(?:\.\d+)?\b', options_text))
                    
                    gen_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', raw_answer))
                    unsupported = gen_nums - chunk_nums
                    
                    print(f"  [Metric Grounding] Numbers in Context: {chunk_nums}")
                    print(f"  [Metric Grounding] Numbers Generated: {gen_nums}")
                    
                    if unsupported:
                        print(f"  [Metric Grounding] Validation FAILED! Unsupported Numbers: {unsupported}")
                        print(f"  [Metric Grounding] Replacing with fallback.")
                        raw_answer = "I focused on building the system and validating the workflow. I do not have production metrics available for this project."
                    else:
                        print(f"  [Metric Grounding] Validation Passed.")

                    approx_tokens = (len(SYSTEM_PROMPT) + len(current_prompt) + len(raw_answer)) // 4
                    dom_meta["llm_tokens_used"] = approx_tokens
                    confidence = 90
                except Exception as e:
                    print(f"QuestionEngine LLM Error: {e}")
                    raw_answer = ""
                    confidence = 0
                
        # Apply Normalization Layer
        if str(raw_answer) in ["[]", "null", "None", "", "REVIEW_REQUIRED"] or (isinstance(raw_answer, list) and not raw_answer):
            det_ans = apply_deterministic_fallback()
            if det_ans:
                raw_answer = det_ans
                source = "Deterministic Fallback"
            else:
                raw_answer = "REVIEW_REQUIRED"

        if raw_answer != "REVIEW_REQUIRED":
            normalized = ResponseNormalizer.normalize(
                raw_answer=raw_answer,
                classification=classification,
                field_type=field_type,
                placeholder=placeholder,
                label_text=label_text,
                options=options,
                llm_client=self.llm_client
            )
            
            # Validation checks
            if str(normalized) in ["[]", "null", "None", "", "REVIEW_REQUIRED"] or (isinstance(normalized, list) and not normalized):
                det_ans = apply_deterministic_fallback()
                if det_ans:
                    normalized = ResponseNormalizer.normalize(
                        raw_answer=det_ans,
                        classification=classification,
                        field_type=field_type,
                        placeholder=placeholder,
                        label_text=label_text,
                        options=options,
                        llm_client=self.llm_client
                    )
                    source = "Deterministic Fallback"

            # Final Validation for dropdowns
            if options and field_type in ["dropdown", "multiselect", "radio_or_checkbox"]:
                string_options = [str(o) for o in options]
                if normalized not in string_options:
                    normalized = "REVIEW_REQUIRED"
                        
            if required and not normalized:
                normalized = "NORMALIZATION_FAILED"
        else:
            normalized = "REVIEW_REQUIRED"
        
        # Telemetry Logging
        print(f"\n[Classification]: {classification} -> {question}")
        if options:
            print(f"[Dropdown Debug]")
            print(f"  -> Question: {question}")
            print(f"  -> Detected Type: {classification}")
            print(f"  -> Mapped Value (Raw): {raw_answer}")
            print(f"  -> Available Options: {options}")
            print(f"  -> Selected Option (Normalized): {normalized}")
            
        dom_meta["confidence"] = confidence
        dom_meta["label_text"] = label_text
        dom_meta["field_type"] = field_type
        dom_meta["placeholder"] = placeholder
        dom_meta["options"] = json.dumps(options) if options else ""
        dom_meta["required"] = required
        dom_meta["final_value"] = normalized
        
        self.log_decision(question, classification, source, raw_answer, normalized, metadata=dom_meta)
        return normalized
