from src.system.logger import setup_logger
logger = setup_logger('mission_control')
import json
import sqlite3
from typing import List, Dict
from datetime import datetime
from src.config.config import Config
from groq import Groq
from src.crm.database import get_all_uncontacted_scored_leads, get_daily_stats, add_or_update_lead, get_lead
from src.jobs.discovery import ingest_jobs
from src.jobs.matching import run_job_matching

class MissionControl:
    def __init__(self):
        self.groq_client = Groq(api_key=Config.GROQ_API_KEY)
        self.max_daily_emails = Config.MAX_DAILY_EMAILS
        self.max_bounce_rate = Config.MAX_BOUNCE_RATE

    def _get_role_priority_score(self, job_title: str) -> int:
        """
        1. Full-Time Entry-Level Roles (score 4)
        2. Graduate Programs (score 3)
        3. Associate Roles (score 2)
        4. Internships (score 1)
        """
        title_lower = job_title.lower()
        if "entry" in title_lower or "fresher" in title_lower or "new grad" in title_lower:
            return 4
        if "graduate" in title_lower:
            return 3
        if "associate" in title_lower:
            return 2
        if "intern" in title_lower:
            return 1
        return 0

    def prioritize_opportunities(self, leads: List[Dict]) -> List[Dict]:
        """Sorts opportunities based on defined rules."""
        def sort_key(lead):
            # Parse agent_metadata to get interview_probability and contact_confidence if available
            metadata = {}
            try:
                if lead.get("agent_metadata"):
                    metadata = json.loads(lead["agent_metadata"])
            except:
                pass
            
            # Since interview_probability isn't a direct column but might be in agent_metadata from matching
            job_matching_meta = metadata.get("job_matching", {})
            interview_prob = lead.get("interview_probability", 0) # Fallback to DB column if we add it
            if not interview_prob and "interview_probability" in job_matching_meta:
                interview_prob = job_matching_meta["interview_probability"]
                
            contact_conf = lead.get("contact_confidence", 0)
            
            role_priority = self._get_role_priority_score(lead.get("job_title", ""))
            
            # Sort order:
            # 1. Role priority (desc)
            # 2. Interview Probability (desc)
            # 3. Contact Confidence (desc)
            # 4. Freshness (asc days_old)
            days_old = lead.get("days_old", 999)
            
            return (role_priority, interview_prob, contact_conf, -days_old)
            
        return sorted(leads, key=sort_key, reverse=True)

    def validate_rules(self, lead: Dict) -> str:
        """Returns PROCEED, SKIP, or REVIEW based on deterministic rules."""
        stats = get_daily_stats()
        emails_sent = stats["emails_sent"]
        bounces = stats["bounces"]
        
        # Check Daily Limits
        if emails_sent >= self.max_daily_emails:
            logger.info(f"[Mission Control] Daily email limit reached ({emails_sent}/{self.max_daily_emails}).")
            return "SKIP_DAILY_LIMIT"
            
        # Check Bounce Rate
        if emails_sent > 10:
            bounce_rate = bounces / emails_sent
            if bounce_rate > self.max_bounce_rate:
                logger.info(f"[Mission Control] CRITICAL: Bounce rate {bounce_rate*100:.1f}% exceeds limit. Pausing outreach.")
                return "SKIP_BOUNCE_LIMIT"

        # Check job matching metadata
        metadata = {}
        try:
            if lead.get("agent_metadata"):
                metadata = json.loads(lead["agent_metadata"])
        except:
            pass
            
        job_matching = metadata.get("job_matching", {})
        interview_prob = lead.get("interview_probability", job_matching.get("interview_probability", 0))
        agent_conf = job_matching.get("confidence", 1.0)
        
        if interview_prob < Config.MIN_INTERVIEW_PROBABILITY:
            logger.info(f"[Mission Control] Rejecting {lead['company_name']} - Interview Probability too low ({interview_prob}%).")
            return "SKIP_LOW_PROB"
            
        contact_conf = lead.get("contact_confidence", 0)
        if contact_conf < Config.CONTACT_CONFIDENCE_THRESHOLD:
            return "LLM_REVIEW" # Ambiguous contact
            
        if agent_conf < Config.CONTACT_CONFIDENCE_THRESHOLD:
            return "LLM_REVIEW" # Low confidence from matching agent

        return "PROCEED"

    def llm_validation(self, lead: Dict) -> Dict:
        logger.info(f"[Mission Control] Running LLM Executive Review for {lead['company_name']} due to ambiguity/low confidence...")
        prompt = f"""
        You are the Mission Control Executive Agent.
        Review the following opportunity and decide if we should PROCEED, SKIP, or REVIEW manually.
        Optimize for actual interviews, not email volume.
        
        Company: {lead.get('company_name')}
        Job Title: {lead.get('job_title')}
        Match Score: {lead.get('job_match_score')}
        Agent Metadata: {lead.get('agent_metadata')}
        
        Return ONLY valid JSON:
        {{
            "decision": "PROCEED",
            "confidence": 0.9,
            "reasoning": "Despite lower contact confidence, the interview probability is very high..."
        }}
        """
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.info(f"Mission Control LLM Error: {e}")
            return {"decision": "SKIP", "confidence": 0.0, "reasoning": "Error in LLM review."}

    def generate_daily_briefing(self):
        stats = get_daily_stats()
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Jobs Found
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE posting_date LIKE ?", (f"{datetime.now().isoformat().split('T')[0]}%",))
        jobs_found = cursor.fetchone()[0]
        
        # Jobs Qualified (Scored >= MIN_INTERVIEW_PROBABILITY)
        cursor.execute("SELECT COUNT(*) FROM leads WHERE interview_probability >= ?", (Config.MIN_INTERVIEW_PROBABILITY,))
        jobs_qualified = cursor.fetchone()[0]
        
        # Full-Time Opportunities
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE employment_type LIKE '%Full-time%'")
        full_time_opps = cursor.fetchone()[0]
        
        # Recommended Applications
        cursor.execute("SELECT COUNT(*) FROM leads WHERE status IN ('HR Contacted', 'Enriched', 'Resume Tailored')")
        recommended_apps = cursor.fetchone()[0]
        
        # Interviews
        cursor.execute("SELECT COUNT(*) FROM leads WHERE interview_scheduled = 1")
        interviews = cursor.fetchone()[0]
        
        # Positive Replies (assuming a column or parsing exists, we'll fake it from hr_replied for now as placeholder)
        cursor.execute("SELECT COUNT(*) FROM leads WHERE hr_replied = 1")
        positive_replies = cursor.fetchone()[0]
        
        conn.close()
        
        briefing = f"""
==================================================
MISSION CONTROL: DAILY BRIEFING
==================================================
Jobs Found: {jobs_found}
Jobs Qualified: {jobs_qualified}
Full-Time Opportunities: {full_time_opps}
Recommended Applications: {recommended_apps}
Emails Sent: {stats['emails_sent']}
Replies: {stats['replies']}
Positive Replies: {positive_replies}
Interviews: {interviews}
Bounces: {stats['bounces']}
API Credits Used: Not tracked yet
==================================================
        """
        logger.info(briefing)
        return briefing

        # Removed run_daily_operations as orchestrator.py will handle the batch logic.
