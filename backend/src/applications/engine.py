from src.api.db import get_connection
from src.system.logger import setup_logger
logger = setup_logger('engine')
import os
import sqlite3
import datetime
from src.config.config import Config
from src.applications.app_queue import generate_daily_queue
from src.applications.executor import ApplicationExecutor
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient
from src.utils.llm_router import LLMRouter
from src.intelligence.intelligence import run_intelligence_engine

class AutoapplyEngine:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.max_daily_applications = 1
        self.conn = get_connection()
        self.conn.row_factory = sqlite3.Row
        
        # Instantiate dependencies once per batch
        self.rag_client = RAGClient()
        self.llm_client = LLMRouter()
        
    def _map_resume_to_profile(self, recommended_resume: str) -> tuple[str, str]:
        """
        Maps the recommended resume string from the DB to an absolute resume path
        and the correct profile_type for the ProfileManager.
        """
        if not recommended_resume:
            return ("", "AI_PROFILE") # Fallback
            
        resume_lower = recommended_resume.lower()
        
        # Explicit Mapping Table
        if "aiml" in resume_lower or "ai" in resume_lower:
            profile_type = "AI_PROFILE"
            filename = "yash_resume_aiml.tex"
        elif "pm" in resume_lower or "business" in resume_lower or "product" in resume_lower:
            profile_type = "BUSINESS_PROFILE"
            filename = "yash_resume_pm.tex"
        elif "sde" in resume_lower or "software" in resume_lower:
            profile_type = "SDE_PROFILE"
            filename = "yash_resume_sde.tex"
        else:
            profile_type = "AI_PROFILE" # Default fallback
            filename = "yash_resume_aiml.tex"
            
        # We need the PDF version for upload, not the TEX version
        pdf_filename = filename.replace(".tex", ".pdf")
        
        pdf_path = str(Config.DATA_DIR / pdf_filename)
        if not os.path.exists(pdf_path):
            if "pm" in filename:
                fallback_path = str(Config.DATA_DIR / "Yash_product.pdf")
            else:
                fallback_path = str(Config.DATA_DIR / "Resume_aiml.pdf")
                
            if os.path.exists(fallback_path):
                pdf_path = fallback_path
                
        return pdf_path, profile_type

    def run_daily_batch(self):
        logger.info("==================================================")
        logger.info("🚀 STARTING AUTOAPPLY ENGINE BATCH")
        logger.info(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("==================================================")
        
        # 1. Fill the queue
        generate_daily_queue()
        
        # 2. Fetch QUEUED jobs for today
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT q.*, j.location 
            FROM application_queue q
            JOIN jobs j ON q.job_id = j.id
            WHERE q.queue_status = 'QUEUED' 
            AND q.queue_date = ?
            ORDER BY q.ranking_score DESC
            LIMIT ?
        ''', (today, self.max_daily_applications))
        
        jobs_to_process = cursor.fetchall()
        
        if not jobs_to_process:
            logger.info("Autoapply Engine: No jobs queued for today. Exiting.")
            return
            
        logger.info(f"Autoapply Engine: Processing {len(jobs_to_process)} jobs...")
        
        for job in jobs_to_process:
            job_id = job["job_id"]
            company = job["company"]
            title = job["title"]
            ats_url = job["ats_url"]
            location = job["location"] or "Unknown"
            rec_resume = job["recommended_resume"]
            
            logger.info(f"\n--- Applying to Job {job_id}: {title} at {company} ---")
            
            # 3. Dynamic Routing & Pre-flight
            resume_path, profile_type = self._map_resume_to_profile(rec_resume)
            logger.info(f"Routing logic: Selected Profile '{profile_type}' with Resume '{resume_path}'")
            
            if not os.path.exists(resume_path):
                logger.info(f"[PRE-FLIGHT FAILED] Resume file not found at {resume_path}")
                self._update_queue_status(job_id, "FAILED", f"Resume missing: {resume_path}")
                continue
                
            # Fetch Company Intelligence
            try:
                intel_dict = run_intelligence_engine(company)
                company_context = f"Domain: {intel_dict.get('domain', 'Unknown')}, Employees: {intel_dict.get('employee_count', 'Unknown')}"
            except Exception:
                company_context = ""
                
            # Create Profile Manager for this specific profile
            profile_manager = ProfileManager(profile_type)
            
            # 4. Execute Application
            executor = ApplicationExecutor(
                job_id=job_id,
                url=ats_url,
                resume_path=resume_path,
                profile_type=profile_type,
                job_title=title,
                company_name=company,
                location=location,
                test_mode=self.dry_run,
                profile_manager=profile_manager,
                rag_client=self.rag_client,
                llm_client=self.llm_client,
                company_context=company_context
            )
            
            try:
                final_status = executor.execute()
                logger.info(f"Result for Job {job_id}: {final_status}")
                self._update_queue_status(job_id, final_status, "")
            except Exception as e:
                logger.info(f"Critical execution error for Job {job_id}: {e}")
                self._update_queue_status(job_id, "FAILED", str(e))
                
        logger.info("\n==================================================")
        logger.info("🏁 AUTOAPPLY BATCH COMPLETE")
        logger.info("==================================================")
        
    def _update_queue_status(self, job_id: int, status: str, notes: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE application_queue 
            SET queue_status = ?, application_notes = ? 
            WHERE job_id = ? AND queue_status = 'QUEUED'
        ''', (status, notes, job_id))
        self.conn.commit()

if __name__ == "__main__":
    engine = AutoapplyEngine(dry_run=True)
    engine.run_daily_batch()
