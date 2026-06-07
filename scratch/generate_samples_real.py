from groq import Groq
from src.config.config import Config
from src.resume.agent5_resume_tailor import tailor_resume
import csv

def main():
    client = Groq(api_key=Config.GROQ_API_KEY)
    
    output_directory = str(Config.DATA_DIR / "linkedin_resumes")
    base_resume = str(Config.DATA_DIR / "yash_resume_aiml.tex")
    
    print(f"Generating real JD sample into: {output_directory}")
    
    # Read the first job from jobs.csv
    csv_path = Config.DATA_DIR / "jobs.csv"
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        jobs = list(reader)
        
    if not jobs:
        print("No jobs found in jobs.csv")
        return
        
    target_job = jobs[0]
    company = target_job["company_name"]
    title = target_job["job_title"]
    desc = target_job["job_description"]
    
    print(f"\n--- Generating for {title} at {company} ---")
    print(f"JD Snippet: {desc[:100]}...")
    
    pdf_path, _ = tailor_resume(client, base_resume, company, title, desc, output_dir=output_directory)
    print(f"Saved real JD PDF to: {pdf_path}")

if __name__ == "__main__":
    main()
