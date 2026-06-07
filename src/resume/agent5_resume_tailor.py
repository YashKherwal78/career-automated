import os
import subprocess
from pathlib import Path
from src.config.config import Config
from groq import Groq

RESUME_WRITER_SYSTEM_PROMPT = """
You are the Resume Generation Agent for Yash Kherwal.

You have access to:
1. Candidate Intelligence Database
2. Job Description
3. Resume Template

Your objective is NOT ATS optimization.
Your objective is maximizing interview probability.

==================================================
PRIMARY PRINCIPLES
==================================================
A recruiter spends approximately 10-20 seconds on a resume.
The resume must answer:
Why this candidate?
Why this role?
Why now?
Every bullet must earn its place.

==================================================
PROJECT SELECTION
==================================================
Do NOT blindly keyword match.
Use the Candidate Intelligence Database.
Select projects based on:
- Demonstrated ownership
- Relevant problem solving
- Technical depth
- Product thinking
- Company relevance

Maximum: 4 Projects
Prefer: 1 flagship project + 2 supporting projects + 1 optional project

==================================================
ROLE STRATEGIES
==================================================
AI / ML ENGINEER
Prioritize:
1. Autonomous Data Analysis Agent
2. Semantic Document Search
3. YAAR (technical framing)
4. SC-MFC Thesis
Focus on: Architecture, Technical decisions, Failure modes, Production deployment

PRODUCT MANAGER
Prioritize:
1. YAAR
2. Recruiting Intelligence Platform
3. Semantic Search
4. Custom domain project
Focus on: User problem, Product decisions, Tradeoffs, Metrics, Ownership

SOFTWARE ENGINEER
Prioritize:
1. Autonomous Data Analysis Agent
2. Recruiting Intelligence Platform
3. Semantic Search
4. BEL Experience
Focus on: Reliability, Scalability, Concurrency, Architecture

DATA SCIENCE
Prioritize:
1. SC-MFC Thesis
2. ScoreMe
3. Autonomous Data Analysis Agent
4. Semantic Search
Focus on: Quantitative outcomes, Modeling, Evaluation, Business impact

==================================================
BULLET WRITING RULES
==================================================
Good Bullet: Action + Decision + Result
Example: Built a hybrid retrieval system combining BGE-M3 embeddings and BM25 scoring to improve semantic search quality across 500+ documents while preserving exact-match retrieval performance.

Bad Bullet: Developed a search engine using Python.

==================================================
FORBIDDEN
==================================================
Never write: Responsible for, Worked on, Helped with, Assisted in, Passionate about, Strong understanding of, Excellent communication skills

==================================================
TRUTH POLICY
==================================================
Never invent metrics, users, revenue, accuracy, scale, or technologies.
Only use facts contained in the Candidate Intelligence Database.

==================================================
PROJECTS SECTION RULES
==================================================
Do not include the year, months, or dates in the Projects section. 

==================================================
OUTPUT
==================================================
Generate only valid LaTeX content.
The output must compile directly using the provided resume template.
Do not include explanations. Do not include markdown. Do not include commentary.
Return only the completed LaTeX resume.
"""

def tailor_resume(groq_client: Groq, base_resume_path: str, company_name: str, job_title: str, job_description: str, output_dir: str = None) -> tuple[str, str]:
    """Agent 5: LLM-tailors the LaTeX resume based on role and compiles to PDF."""
    print(f"Agent 5: Tailoring resume for {job_title} at {company_name}...")
    
    if not output_dir:
        output_dir = str(Config.DATA_DIR)
        
    out_dir_path = Path(output_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    
    if not os.path.exists(base_resume_path):
        print(f"Cannot find base resume at {base_resume_path}")
        return "", ""
        
    with open(base_resume_path, "r") as f:
        template = f.read()
        
    db_path = Config.DATA_DIR / "context" / "yash_candidate_intelligence_db.txt"
    try:
        with open(str(db_path), "r") as f:
            intelligence_db = f.read()
    except Exception as e:
        print(f"Could not load intelligence DB: {e}")
        intelligence_db = ""
        
    user_prompt = f"""
    COMPANY NAME:
    {company_name}

    JOB TITLE:
    {job_title}

    JOB DESCRIPTION:
    {job_description}
    
    CANDIDATE INTELLIGENCE DATABASE:
    {intelligence_db}
    
    RESUME TEMPLATE (Use this structure exactly):
    {template}
    """
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": RESUME_WRITER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=2500
        )
        latex_content = response.choices[0].message.content.strip()
        
        # Extract LaTeX only (from \documentclass to \end{document})
        import re
        match = re.search(r'(\\documentclass.*?\\end\{document\})', latex_content, re.DOTALL)
        if match:
            latex_content = match.group(1)
        else:
            print("Agent 5 Warning: Could not find \documentclass or \end{document} in the response.")
                
    except Exception as e:
        print(f"Agent 5 LLM Error: {e}")
        return base_resume_path, "Fallback (Error)"
        
    # Write tailored tex
    sanitized_role = "".join([c if c.isalnum() else "_" for c in job_title])[:30]
    tex_path = out_dir_path / f"tailored_resume_{sanitized_role}.tex"
    
    with open(str(tex_path), "w") as f:
        f.write(latex_content)
        
    # Compile to PDF
    print(f"Agent 5: Compiling {tex_path.name} with pdflatex...")
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(out_dir_path), str(tex_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        pdf_path = out_dir_path / f"tailored_resume_{sanitized_role}.pdf"
        if pdf_path.exists():
            print(f"Agent 5: Successfully generated PDF: {pdf_path.name}")
            return str(pdf_path), "Dynamic Tailored Project"
    except subprocess.CalledProcessError as e:
        print(f"Agent 5: pdflatex compilation failed. Using base resume. Error: {e}")
        
    return base_resume_path, "Fallback (Compilation Error)"

if __name__ == "__main__":
    client = Groq(api_key=Config.GROQ_API_KEY)
    tailor_resume(client, str(Config.DATA_DIR / "yash_resume_aiml.tex"), "SaaS Enterprise Software Company")
