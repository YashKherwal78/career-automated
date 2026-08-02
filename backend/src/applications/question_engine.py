from src.system.logger import setup_logger
logger = setup_logger('question_engine')
import re
import json
from datetime import datetime, timedelta
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
        legal_keywords = ["veteran", "disability", "gender", "sex", "race", "hispanic", "latino", "criminal", "felony", "convicted", "conviction", "background", "bgv", "consent", "identify as", "privacy", "acknowledg", "conflict of interest"]
        if any(kw in q_lower for kw in legal_keywords):
            return "LEGAL"
            
        # 3. COMPENSATION
        comp_keywords = ["salary", "compensation", "expected pay", "rate", "remuneration"]
        if any(kw in q_lower for kw in comp_keywords):
            return "COMPENSATION"
            
        # 4. PROFILE
        # Name variants are listed first inside this group's keyword set below;
        # without them "Preferred Name" fell through every branch to the
        # TECHNICAL fallback, which routes to the low-confidence gate and
        # returns REVIEW_REQUIRED for a field the profile answers outright.
        profile_keywords = ["legal name", "full name", "preferred name", "nickname",
                            "middle name", "surname", "family name", "your name",
                            "notice period", "start date", "earliest date", "available to start", "when can you join",
                            "total work experience", "total experience", "come to know about", "relocate", "relocation",
                            "availability", "when can you start", "date you are available",
                            "graduation", "passout", "expected graduation", "school", "university", "linkedin", "portfolio", "github", "website", "organisation", "organization", "current role", "years of experience", "relative", "family member", "related party", "previously employed", "former employee", "previously been employed", "employer", "company", "institute", "college", "degree", "education", "travel", "first name", "last name", "email", "phone", "location", "city", "country", "state", "reside", "hear about", "source", "how did you find out", "referral"]
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
            "yes": ["agree", "accept", "consent", "acknowledge", "authorized", "eligible to work", "relocate", "open to relocation", "yes", "true", "y", "1"],
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
            
        logger.info(f"[Dropdown] Attempting LLM Fallback (Groq) for: '{label_text}'")
        
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
                logger.info(f"  -> LLM Fallback (Groq) mapped '{selected}' with >90% conf.")
                return selected
            elif conf >= 60 and selected in options:
                logger.info(f"  -> LLM Fallback (Groq) mapped '{selected}' with {conf}% conf. Reason: {reason}")
                return selected
            else:
                logger.info(f"  -> LLM Fallback (Groq) returned confidence {conf} < 60%. REVIEW_REQUIRED.")
                return "REVIEW_REQUIRED"
                
        except Exception as e:
            logger.info(f"[Dropdown] LLM Fallback Failed: {e}")
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

        # React-select widgets (Greenhouse) render their real option list
        # only once opened, so the DOM extractor can't see it ahead of time
        # and `options` comes through empty even for a plain Yes/No question.
        # The RAG/LLM path then answers in full-sentence form (e.g. "No, I
        # have not worked at DoorDash.") instead of a bare option value,
        # which the widget interaction can't match against a real "Yes"/"No"
        # option. If it's an unresolved dropdown and the answer opens with
        # Yes/No, use just that word.
        if field_type == "dropdown" and not options:
            leading_yn = re.match(r"^(yes|no)\b", ans, re.IGNORECASE)
            if leading_yn:
                return leading_yn.group(1).capitalize()

        # 1. Dropdowns
        if options and isinstance(options, list) and len(options) > 0:
            ans_lower = ans.lower()
            
            # Cache Check
            cache_key = f"{label_text}_{ans_lower}_{str(options)}"
            if cache_key in ResponseNormalizer._dropdown_cache:
                logger.info(f"  -> Cache Hit: {ResponseNormalizer._dropdown_cache[cache_key]}")
                return ResponseNormalizer._dropdown_cache[cache_key]
            
            # Phase A: Exact Match
            for opt in options:
                if ans_lower == str(opt).lower().strip():
                    ResponseNormalizer._dropdown_cache[cache_key] = opt
                    return opt

            # Phase A1: Punctuation-insensitive exact match. Phase A compares
            # raw strings, so a purely cosmetic difference in hyphenation or
            # punctuation defeats it: the profile stores "Decline to Self
            # Identify" while the form offers "Decline to self-identify".
            # That near-miss used to fall through to the fuzzy path, which
            # picked the FIRST race option ("Hispanic or Latino") — silently
            # submitting a false statement about a protected characteristic
            # on a form the candidate had explicitly declined to answer.
            def _squash(s: str) -> str:
                return re.sub(r"[^a-z0-9]", "", str(s).lower())

            ans_squashed = _squash(ans_lower)
            for opt in options:
                if ans_squashed and ans_squashed == _squash(opt):
                    ResponseNormalizer._dropdown_cache[cache_key] = opt
                    return opt

            # Phase A1b: Decline-to-answer intent match. Any phrasing of "I'd
            # rather not say" must land on the option that means the same
            # thing, never on a substantive category. Voluntary EEO surveys
            # word this half a dozen different ways across ATSs, so intent is
            # matched on both sides rather than string-compared.
            # "n't wish" deliberately covers the contracted forms ("I don't
            # wish to answer", "doesn't wish") without matching a bare
            # affirmative "I wish to answer".
            _DECLINE_MARKERS = ("decline", "prefer not", "wish not", "not wish",
                                "n't wish", "rather not", "do not want to answer",
                                "don't want to answer", "prefer to self-describe",
                                "choose not", "opt out")
            if any(m in ans_lower for m in _DECLINE_MARKERS):
                for opt in options:
                    if any(m in str(opt).lower() for m in _DECLINE_MARKERS):
                        ResponseNormalizer._dropdown_cache[cache_key] = opt
                        return opt

            # Phase A2: Containment match — for a compound answer like
            # "Ghaziabad, Uttar Pradesh, India" against a bare country
            # list, Phase A's exact-equality check never fires (the full
            # string isn't equal to any single option). Before falling to
            # a fuzzy LLM guess (which can genuinely mis-pick an unrelated
            # option, e.g. once returned "Lebanon" for an Indian city/state/
            # country string), check whether an option name appears in the
            # answer as a whole word — a free, deterministic, and far safer
            # signal for exactly this shape of question.
            # A second variant — just the last comma-separated segment
            # (typically the country, e.g. "india" from "Ghaziabad, Uttar
            # Pradesh, India") — catches compound MULTI-word options like
            # "India Remote" that a bare-option-in-answer check can't (the
            # option itself is longer than any single segment of the
            # answer, so it has to be checked the other way around: does
            # the short variant appear inside the option).
            last_segment = ans_lower.split(",")[-1].strip()
            answer_variants = [last_segment] if last_segment and last_segment != ans_lower else []

            containment_matches = []
            for opt in options:
                opt_l = str(opt).lower().strip()
                if re.search(r'\b' + re.escape(opt_l) + r'\b', ans_lower):
                    containment_matches.append(opt)
                    continue
                if any(v and re.search(r'\b' + re.escape(v) + r'\b', opt_l) for v in answer_variants):
                    containment_matches.append(opt)

            if containment_matches:
                # Prefer a "remote" option among ambiguous matches — a
                # country-only match (e.g. "india") can equally hit a
                # specific-hub option ("Bengaluru, India") and a remote
                # option ("India Remote"); the candidate isn't necessarily
                # IN a listed hub city, just eligible for remote work from
                # that broader country.
                remote_matches = [o for o in containment_matches if "remote" in str(o).lower()]
                pool = remote_matches or containment_matches
                best = max(pool, key=lambda o: len(str(o)))
                ResponseNormalizer._dropdown_cache[cache_key] = best
                return best

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
    def __init__(self, profile_manager, rag_client, llm_client, company_context: str, job_title: str, job_location: str = ""):
        self.profile = profile_manager
        self.rag = rag_client
        self.llm_client = llm_client
        self.company_context = company_context
        self.job_title = job_title
        self.job_location = job_location or ""
        self.audit_log = []

    # Country-specific work-authorization keys already present on the profile.
    # Ordered so the more specific patterns are tested before broader ones.
    # Patterns are matched against a period-stripped copy of the text (see
    # _work_authorized_for): "U.S." becomes "us", so a single \bus\b handles
    # "US", "U.S." and "U.S.A." without needing optional-dot patterns, which
    # break on a trailing period ("...work in the U.S.?" left no word boundary
    # after the final dot and silently failed to match at all).
    _WORK_AUTH_COUNTRIES = [
        (r"\bus\b|\busa\b|united states|america", "work_authorized_us"),
        (r"\buk\b|united kingdom|britain", "work_authorized_uk"),
        (r"\beu\b|european union|europe|schengen", "work_authorized_eu"),
        (r"\bindia\b", "work_authorized_india"),
    ]

    def _work_authorized_for(self, question: str, hints: str = "") -> bool:
        """Answer 'are you authorized to work in X?' against the RIGHT country.

        This previously read the single generic `work_authorization` flag,
        which is True (the candidate is authorized to work in India). On a US
        posting that produced "Are you authorized to work in the U.S.?" -> Yes,
        a false statement on a legally-significant knockout question, and one
        that directly contradicted the very next answer ("Will you require
        sponsorship?" -> Yes). The profile has always carried per-country keys
        (work_authorized_us / _uk / _eu / _india); nothing was reading them.

        Country is taken from the question text first, then the job location.
        If neither names a country the fallback is the generic flag, matching
        the previous behaviour for genuinely ambiguous phrasing.
        """
        haystack = re.sub(r"\.", "", f"{question} {hints}".lower())
        for pattern, field in self._WORK_AUTH_COUNTRIES:
            if re.search(pattern, haystack):
                return bool(self.profile.get_field(field))
        loc = re.sub(r"\.", "", (self.job_location or "").lower())
        for pattern, field in self._WORK_AUTH_COUNTRIES:
            if re.search(pattern, loc):
                return bool(self.profile.get_field(field))
        return bool(self.profile.get_field("work_authorization"))

    def _visa_sponsorship_needed(self) -> bool:
        """India-based roles: no sponsorship needed. Anything else (or
        unknown location): sponsorship is needed, per candidate preference."""
        return "india" not in self.job_location.lower()

    def _expected_salary_answer(self) -> str:
        """Remote + US-based roles get a distinct, lower anchor figure
        ($30,000) per explicit candidate instruction — everything else
        (including domestic India roles) uses the profile's own stored INR
        expectation."""
        loc = self.job_location.lower()
        is_us = bool(re.search(r'\bu\.?s\.?a?\b|united states', loc))
        if "remote" in loc and is_us:
            return "$30,000"
        return str(self.profile.get_field("expected_salary"))

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
            logger.info(f"\n[LocationResolver]")
            logger.info(f"  -> Question: {question}")
            logger.info(f"  -> Options: {options}")
            logger.info(f"  -> Selected: {loc_result['selected_location']}")
            logger.info(f"  -> Reasoning: {loc_result['reasoning']} (Conf: {loc_result['confidence']})")
            
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
            if "sponsor" in q_lower or "visa" in q_lower: ans = "Yes" if self._visa_sponsorship_needed() else "No"
            # Was hardcoded to "Yes". For a binary Yes/No widget this fast path
            # runs BEFORE the profile lookup below, so it was the thing actually
            # answering "Are you authorized to work in the U.S.?" — always Yes,
            # regardless of country and regardless of the per-country flags on
            # the profile saying otherwise. On a US posting that is a false
            # statement on a knockout question, and it directly contradicted the
            # sponsorship answer produced one line above it.
            elif "authoriz" in q_lower or "work auth" in q_lower:
                ans = "Yes" if self._work_authorized_for(q_lower, hints) else "No"
            elif "previously employed" in q_lower or "former employee" in q_lower or "employed by stripe" in q_lower: ans = "No"
            elif "whatsapp" in q_lower: ans = "Yes"
            elif "background" in q_lower or "bgv" in q_lower: ans = "Yes"
            elif "relocat" in q_lower: ans = "Yes"
            elif "travel" in q_lower: ans = "Yes"
            elif "remote" in q_lower: ans = "Yes"
            elif "criminal" in q_lower or "felony" in q_lower or "convicted" in q_lower or "conviction" in q_lower: ans = "No"
            elif "conflict of interest" in q_lower: ans = "No"
            elif "relative" in q_lower or "family member" in q_lower or "related party" in q_lower: ans = "No"
            elif "privacy" in q_lower or "acknowledg" in q_lower: ans = "Yes"
            return ans

        # Add robust check for is_binary_dropdown
        if options:
            opts_lower = [str(o).lower() for o in options]
            if "yes" in opts_lower and "no" in opts_lower:
                is_binary_dropdown = True
                
        # Force deterministic evaluation for problem fields
        aggressive_keywords = ["sponsor", "visa", "authoriz", "work auth", "previously employed", "employed by stripe", "whatsapp", "background", "bgv", "relocat", "travel", "remote", "criminal", "felony", "convicted", "conviction", "conflict of interest", "relative", "family member", "related party", "privacy", "acknowledg"]
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
            # "country"/"city" are more specific than the generic "reside"/
            # "current location" keywords below, so they must be checked
            # first — otherwise "What country do you reside in?" matches the
            # generic CURRENT_LOCATION branch (via "reside") and never
            # reaches the COUNTRY branch, answering with the wrong field.
            # A question naming BOTH city and country ("Which country and city
            # are you currently based in?") must be checked before the bare
            # COUNTRY branch below, which otherwise matches on "country" and
            # answers with just "India" — technically true but only half the
            # answer the form asked for.
            elif ("country" in q_lower or "country" in hints) and any(
                    kw in q_lower or kw in hints for kw in ["city", "town", "located", "based"]):
                canonical_field = "CURRENT_LOCATION"
                raw_answer = str(self.profile.get_field("current_location")
                                 or self.profile.get_field("location") or "")
            elif any(kw in q_lower or kw in hints for kw in ["country", "nationality", "residence country"]):
                canonical_field = "COUNTRY"
            elif any(kw in q_lower or kw in hints for kw in ["city", "current city", "location city", "location (city)"]):
                canonical_field = "CITY"
            elif any(kw in q_lower or kw in hints for kw in ["residence location", "current residence", "where do you live", "current location", "reside"]):
                canonical_field = "CURRENT_LOCATION"
                raw_answer = self.profile.get_field("location")
            elif any(kw in q_lower or kw in hints for kw in ["location"]):
                canonical_field = "LOCATION"
                
            # Logistics/Legal
            elif "notice period" in hints:
                canonical_field = "NOTICE_PERIOD"
            elif "sponsorship" in hints or "visa" in hints:
                canonical_field = "VISA_REQUIREMENT"
            elif "authorized" in hints or "work authorization" in hints:
                canonical_field = "WORK_AUTHORIZATION"

            # Legal / EEO — background, conduct, and consent questions the
            # candidate has given a standing answer for, so these resolve
            # from profile facts instead of falling through to the RAG/essay
            # path (which has nothing relevant to retrieve for these and
            # would otherwise escalate them as unanswerable).
            elif any(kw in q_lower or kw in hints for kw in ["criminal", "felony", "convicted", "conviction"]):
                canonical_field = "CRIMINAL_RECORD"
            elif "conflict of interest" in q_lower or "conflict of interest" in hints:
                canonical_field = "CONFLICT_OF_INTEREST"
            elif any(kw in q_lower or kw in hints for kw in ["privacy", "acknowledg"]):
                canonical_field = "PRIVACY_ACK"

            # EEO / Demographics — profile already stores these; without
            # this mapping every gender/veteran/disability question falls
            # through to "no deterministic mapping" and gets escalated even
            # though a real, correct answer exists.
            # "transgender" must be checked before the generic "gender" match
            # below — "gender" is a substring of "transgender", so without
            # this ordering "Do you identify as transgender?" gets silently
            # mapped to the GENDER field and answered "Male" (matches no
            # real option, so the widget interaction fails, silently, same
            # failure mode as an unmapped field).
            elif "transgender" in q_lower or "transgender" in hints:
                canonical_field = "TRANSGENDER_STATUS"
            elif any(kw in q_lower or kw in hints for kw in ["gender"]):
                canonical_field = "GENDER"
            elif any(kw in q_lower or kw in hints for kw in ["veteran"]):
                canonical_field = "VETERAN_STATUS"
            elif any(kw in q_lower or kw in hints for kw in ["disability"]):
                canonical_field = "DISABILITY_STATUS"
            elif "race" in q_lower or "race" in hints:
                canonical_field = "RACE"
            elif any(kw in q_lower or kw in hints for kw in ["hispanic", "latino"]):
                canonical_field = "HISPANIC_LATINO"

            # Personal — name variants.
            # Ashby (and some Greenhouse boards) ask for the candidate's name
            # as a *custom* question rather than a standard system field:
            # "Legal Name (First Name Last Name)", "Preferred Name", "Full
            # Name". None of these had a canonical mapping, so they fell all
            # the way through to "PROFILE_FACT missing deterministic mapping"
            # and escalated the whole application to REVIEW_REQUIRED — on a
            # required field whose answer the profile obviously already holds.
            # Matched on specific phrases, never a bare "name", so that
            # "company name" / "university name" / "manager's name" keep
            # resolving through their own branches above.
            elif any(kw in q_lower or kw in hints for kw in ["preferred name", "nickname", "goes by", "preferred first name"]):
                canonical_field = "PREFERRED_NAME"
            elif any(kw in q_lower or kw in hints for kw in ["legal name", "full name", "full legal name", "your name", "name (first", "first and last name", "first name last name"]):
                canonical_field = "FULL_NAME"
            elif "middle name" in q_lower or "middle name" in hints:
                canonical_field = "MIDDLE_NAME"
            elif "first name" in q_lower or "first name" in hints:
                canonical_field = "FIRST_NAME"
            elif "last name" in q_lower or "surname" in q_lower or "family name" in q_lower:
                canonical_field = "LAST_NAME"

            # Personal — links. "Website / Portfolio" is optional on most
            # forms, so an unmapped miss here was silently leaving it blank
            # rather than blocking, but the profile does hold a GitHub URL
            # that is the correct answer for a portfolio prompt.
            elif any(kw in q_lower or kw in hints for kw in ["portfolio", "personal website", "personal site", "website"]):
                canonical_field = "PORTFOLIO"
            elif "linkedin" in hints:
                canonical_field = "LINKEDIN"
            elif "github" in hints:
                canonical_field = "GITHUB"
            elif "phone" in hints:
                canonical_field = "PHONE"
            elif "email" in hints:
                canonical_field = "EMAIL"
            
            # Languages
            elif any(kw in q_lower or kw in hints for kw in ["language", "speak", "proficienc"]):
                canonical_field = "LANGUAGE"
                
            # Availability / Dates
            elif any(kw in q_lower or kw in hints for kw in ["start date", "earliest start", "latest start", "when can you start",
                                                          "available to start", "earliest date", "availability", "when can you join",
                                                          "by when can you join", "how soon can you join",
                                                          "date you are available", "available date"]):
                canonical_field = "START_DATE"
            elif any(kw in q_lower or kw in hints for kw in ["graduation date", "passout", "expected graduation", "end date"]):
                canonical_field = "GRADUATION_DATE"
                
            # Hotfix V2.2 Additions
            elif any(kw in q_lower or kw in hints for kw in ["years of experience", "how many years", "total work experience",
                                                          "total experience", "work experience in a similar",
                                                          "years of professional"]):
                canonical_field = "EXPERIENCE"
            elif any(kw in q_lower or kw in hints for kw in ["hear about", "source", "how did you find out",
                                                          "come to know about", "get to know about",
                                                          "how did you learn about"]):
                canonical_field = "SOURCE"
                
            # Other mappings (Legacy)
            elif "relative" in hints or "family member" in hints or "related party" in hints:
                raw_answer = "Yes" if self.profile.get_field("has_relative_in_company") else "No"
            elif "previously employed" in hints or "former employee" in hints or "previously been employed" in q_lower:
                raw_answer = "Yes" if self.profile.get_field("previously_employed") else "No"
            elif classification == "COMPENSATION":
                raw_answer = self._expected_salary_answer()

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
                    raw_answer = "Yes" if self._visa_sponsorship_needed() else "No"
                elif canonical_field == "WORK_AUTHORIZATION":
                    raw_answer = "Yes" if self._work_authorized_for(q_lower, hints) else "No"
                elif canonical_field == "CRIMINAL_RECORD":
                    raw_answer = "No"
                elif canonical_field == "CONFLICT_OF_INTEREST":
                    raw_answer = "No"
                elif canonical_field == "PRIVACY_ACK":
                    raw_answer = "Yes"
                elif canonical_field == "GENDER":
                    raw_answer = str(self.profile.get_field("gender") or "")
                elif canonical_field == "TRANSGENDER_STATUS":
                    raw_answer = str(self.profile.get_field("transgender_status") or "No")
                elif canonical_field == "VETERAN_STATUS":
                    raw_answer = str(self.profile.get_field("veteran_status") or "")
                elif canonical_field == "DISABILITY_STATUS":
                    raw_answer = str(self.profile.get_field("disability_status") or "")
                elif canonical_field == "RACE":
                    raw_answer = str(self.profile.get_field("race") or "Decline to Self Identify")
                elif canonical_field == "HISPANIC_LATINO":
                    raw_answer = str(self.profile.get_field("hispanic_latino") or "")
                elif canonical_field == "FULL_NAME":
                    raw_answer = f"{self.profile.get_field('first_name') or ''} {self.profile.get_field('last_name') or ''}".strip()
                elif canonical_field == "FIRST_NAME":
                    raw_answer = str(self.profile.get_field("first_name") or "")
                elif canonical_field == "LAST_NAME":
                    raw_answer = str(self.profile.get_field("last_name") or "")
                elif canonical_field == "PREFERRED_NAME":
                    # No separate profile field for this; the first name is the
                    # honest answer rather than inventing a nickname.
                    raw_answer = str(self.profile.get_field("first_name") or "")
                elif canonical_field == "MIDDLE_NAME":
                    # Genuinely absent from the profile. Answering "N/A" is
                    # correct here (the candidate has no middle name recorded)
                    # and is not a guess about an unknown fact.
                    raw_answer = str(self.profile.get_field("middle_name") or "N/A")
                elif canonical_field == "PORTFOLIO":
                    raw_answer = str(self.profile.get_field("portfolio")
                                     or self.profile.get_field("website")
                                     or self.profile.get_field("github") or "")
                elif canonical_field == "LINKEDIN":
                    raw_answer = str(self.profile.get_field("linkedin"))
                elif canonical_field == "GITHUB":
                    raw_answer = str(self.profile.get_field("github"))
                elif canonical_field == "PHONE":
                    raw_answer = str(self.profile.get_field("phone"))
                elif canonical_field == "EMAIL":
                    raw_answer = str(self.profile.get_field("email"))
                elif canonical_field == "LANGUAGE":
                    if "hindi" in q_lower: raw_answer = "Native"
                    elif "english" in q_lower: raw_answer = "Professional"
                    else: raw_answer = "None"
                elif canonical_field == "START_DATE":
                    # "Immediate" is the right answer for a free-text box but
                    # not for a date widget — Ashby renders this question as
                    # an input with a "Pick date..." placeholder, where the
                    # word "Immediate" normalises to nothing and blocked the
                    # whole (required) submission. Emit a concrete date when
                    # the field is asking for one.
                    is_date_widget = (
                        field_type in ("date", "datetime")
                        or "date" in (placeholder or "").lower()
                        or "dd" in (placeholder or "").lower()
                        or "yyyy" in (placeholder or "").lower()
                    )
                    if is_date_widget:
                        # Two weeks out: consistent with the profile's stored
                        # 15-day notice period, and safely in the future
                        # regardless of how long this application sits.
                        start = datetime.now() + timedelta(days=15)
                        raw_answer = start.strftime("%Y-%m-%d")
                    else:
                        raw_answer = "Immediate"
                elif canonical_field == "GRADUATION_DATE":
                    raw_answer = "May 2026"
                
        # If it's a PROFILE_FACT but failed deterministic mapping, DO NOT SEND TO LLM
        if not raw_answer and classification == "PROFILE_FACT":
            logger.info(f"  -> [Warning] PROFILE_FACT missing deterministic mapping. Bypassing LLM.")
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
            logger.info(f"\n[Essay Debug] Question: {question}")
            for i, item in enumerate(retrieved_items):
                score = item.get("score", 0)
                text = item.get("text", "")
                if score > max_score: max_score = score
                chunk_texts.append(text)
                title = text.split("\n")[0] if "\n" in text else text[:50]
                logger.info(f"  -> Retrieved Chunk {i+1}: {title} (Score: {score:.2f})")
                
            # If retrieval confidence is low, fallback to REVIEW_REQUIRED
            # Assuming a BM25 base score + tag boost, a score < 1.0 means practically no matching terms.
            if max_score < 1.0 and classification in ["TECHNICAL", "BEHAVIORAL"]:
                logger.info(f"  -> [Warning] Low retrieval confidence ({max_score:.2f}). Triggering REVIEW_REQUIRED.")
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
                    logger.info(f"  -> Final LLM Answer: {raw_answer}")
                    
                    # Metric Validation
                    import re
                    chunk_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', chunk_text))
                    if options:
                        options_text = " ".join([str(o) for o in options])
                        chunk_nums.update(re.findall(r'\b\d+(?:\.\d+)?\b', options_text))
                    
                    gen_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', raw_answer))
                    unsupported = gen_nums - chunk_nums
                    
                    logger.info(f"  [Metric Grounding] Numbers in Context: {chunk_nums}")
                    logger.info(f"  [Metric Grounding] Numbers Generated: {gen_nums}")
                    
                    if unsupported:
                        logger.info(f"  [Metric Grounding] Validation FAILED! Unsupported Numbers: {unsupported}")
                        logger.info(f"  [Metric Grounding] Replacing with fallback.")
                        raw_answer = "I focused on building the system and validating the workflow. I do not have production metrics available for this project."
                    else:
                        logger.info(f"  [Metric Grounding] Validation Passed.")

                    approx_tokens = (len(SYSTEM_PROMPT) + len(current_prompt) + len(raw_answer)) // 4
                    dom_meta["llm_tokens_used"] = approx_tokens
                    confidence = 90
                except Exception as e:
                    logger.info(f"QuestionEngine LLM Error: {e}")
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
        logger.info(f"\n[Classification]: {classification} -> {question}")
        if options:
            logger.info(f"[Dropdown Debug]")
            logger.info(f"  -> Question: {question}")
            logger.info(f"  -> Detected Type: {classification}")
            logger.info(f"  -> Mapped Value (Raw): {raw_answer}")
            logger.info(f"  -> Available Options: {options}")
            logger.info(f"  -> Selected Option (Normalized): {normalized}")
            
        dom_meta["confidence"] = confidence
        dom_meta["label_text"] = label_text
        dom_meta["field_type"] = field_type
        dom_meta["placeholder"] = placeholder
        dom_meta["options"] = json.dumps(options) if options else ""
        dom_meta["required"] = required
        dom_meta["final_value"] = normalized
        
        self.log_decision(question, classification, source, raw_answer, normalized, metadata=dom_meta)
        return normalized
