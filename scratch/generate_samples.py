from groq import Groq
from src.config.config import Config
from src.resume.agent5_resume_tailor import tailor_resume

def main():
    client = Groq(api_key=Config.GROQ_API_KEY)
    
    output_directory = str(Config.DATA_DIR / "linkedin_resumes")
    base_resume = str(Config.DATA_DIR / "yash_resume_aiml.tex")
    
    print(f"Generating samples into: {output_directory}")
    
    # 1. Product Role
    pm_company = "OpenAI"
    pm_title = "Product Manager"
    pm_desc = "Looking for a Product Manager to lead our API platform, manage technical trade-offs, and define product metrics."
    print(f"\n--- Generating for {pm_title} at {pm_company} ---")
    pm_pdf, _ = tailor_resume(client, base_resume, pm_company, pm_title, pm_desc, output_dir=output_directory)
    print(f"Saved PM PDF to: {pm_pdf}")
    
    # 2. Software Role
    swe_company = "Google"
    swe_title = "Software Engineer"
    swe_desc = "Seeking a Software Engineer with strong background in distributed systems, reliability, concurrency, and scalable architecture."
    print(f"\n--- Generating for {swe_title} at {swe_company} ---")
    swe_pdf, _ = tailor_resume(client, base_resume, swe_company, swe_title, swe_desc, output_dir=output_directory)
    print(f"Saved SWE PDF to: {swe_pdf}")

if __name__ == "__main__":
    main()
