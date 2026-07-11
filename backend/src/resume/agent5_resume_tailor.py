from src.system.logger import setup_logger
logger = setup_logger('agent5_resume_tailor')
import os
import re
import json
import subprocess
from pathlib import Path
from src.config.config import Config
from src.utils.llm_router import LLMRouter
from src.applications.rag import RAGClient

RESUME_WRITER_SYSTEM_PROMPT = """
You are the Resume Tailoring Engine for Yash Kherwal.

You have access to:
1. Retrieved Context (Truthful chunks from Candidate Intelligence Database)
2. Base Resume Template (LaTeX)
3. Job Description Keywords & Skills

==================================================
1. STRICT ANTI-HALLUCINATION RULES (CRITICAL)
==================================================
You are FORBIDDEN from inventing or hallucinating ANY facts.
You MUST NOT invent:
- New projects or internships
- New metrics, numbers, or percentages
- New skills, languages, or tools
- New responsibilities

You are ONLY ALLOWED to:
- Rewrite bullets to improve wording and match JD terminology (ONLY if factually correct).
- Reorder bullets to prioritize relevance.
- Shorten bullets.
- Expand bullets USING ONLY facts from the Retrieved Context.

==================================================
2. LLM SCOPE & LATEX STRUCTURE (STRUCTURE LOCK)
==================================================
- The base .tex template is authoritative.
- DO NOT modify the LaTeX structure (margins, font size, document class).
- DO NOT modify section structures, section names, or alignment.
- DO NOT add dates to projects. If the base template has a date like \resumeProjectHeading{...}{2025}, replace it with an empty string: \resumeProjectHeading{...}{}. NO PROJECT DATES.
- Preserve existing heading formatting and existing spacing exactly.
- DO NOT create new sections.
- Output ONLY valid, compilable LaTeX starting with \documentclass and ending with \end{document}.

==================================================
3. PROJECT & INTERNSHIP SELECTION (DIFFERENTIATION SCORE)
==================================================
- The context will specify Priority Projects and Internships. You MUST include them.
- Total projects should be 2 to 4. 
- Do not remove a highly unique, signature project (like CareerAutomated) simply because another project has slightly higher keyword overlap. Optimize for "Would this resume make a recruiter want to interview this candidate?", NOT just keyword density.

==================================================
4. PAGE UTILIZATION (90-95% TARGET)
==================================================
- The resume MUST fit on exactly 1 page.
- Do NOT leave excessive whitespace at the bottom.
- To fill space:
  1. Expand high-signal bullets using the Retrieved Context.
  2. Add one additional bullet to signature projects.
  3. Add an additional relevant project.
- Do NOT shrink margins or aggressively reduce spacing to force content.

==================================================
5. ORANGE LABS FRAMING (BUSINESS/PRODUCT ROLES)
==================================================
- If this is a Business/Product role, preserve Orange Labs' Product/Growth framing.
- Avoid generic PM buzzwords. Preserve points about Ownership, Problem Discovery, Product Decisions, User Understanding, and Experimentation.
- Do NOT revert Orange Labs back to an AI-heavy engineering description.
"""

def extract_numbers(text: str) -> set:
    """Extracts all integers and decimals from text."""
    numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
    return set(numbers)

def extract_projects_from_tex(tex: str) -> dict:
    """Extracts project blocks from LaTeX. Returns dict of {project_name: full_latex_block}."""
    projects = {}
    matches = re.finditer(r'\\resumeProjectHeading\s*\{\\textbf\{([^}]+)\}.*?\\resumeItemListStart(.*?)\\resumeItemListEnd', tex, re.DOTALL)
    for m in matches:
        proj_name = m.group(1).strip()
        full_block = m.group(0)
        projects[proj_name] = full_block
    return projects

def parse_jd(llm_router: LLMRouter, job_title: str, job_description: str) -> dict:
    """Agentic extraction of JD elements."""
    prompt = f"""
    Analyze the following Job Title and Description.
    Title: {job_title}
    Description: {job_description}
    
    Extract and return ONLY a JSON object with the following keys:
    - "role_type": Categorize as "AI", "PRODUCT", "BUSINESS", or "SDE".
    - "domain": The industry or domain (e.g. "Fintech", "Healthcare").
    - "skills": List of top 10 required hard skills.
    - "keywords": List of 5-10 core terminology/methodology keywords (e.g. "Growth Loops", "Microservices").
    
    JSON Output ONLY:
    """
    try:
        messages = [{"role": "user", "content": prompt}]
        response = llm_router.chat_completion(messages, temperature=0.1, response_format={"type": "json_object"}, intent="utility")
        content = response.choices[0].message.content
        # basic json cleaning
        cleaned = content.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.info(f"JD Parser warning: {e}")
        # Deterministic fallback
        title_lower = job_title.lower()
        role_type = "SDE"
        if any(w in title_lower for w in ["ai", "machine learning", "ml", "data scientist"]): role_type = "AI"
        elif any(w in title_lower for w in ["product", "growth"]): role_type = "PRODUCT"
        elif any(w in title_lower for w in ["business", "analyst"]): role_type = "BUSINESS"
        
        return {
            "role_type": role_type,
            "domain": "Software",
            "skills": ["Python", "SQL", "APIs"],
            "keywords": ["Agile", "Cross-functional"]
        }

def compile_and_count_pages(tex_path, out_dir_path):
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(out_dir_path), str(tex_path)],
            check=False,
            capture_output=True,
            text=True
        )
        match = re.search(r'\((\d+) pages?', result.stdout)
        if match: return int(match.group(1))
        return 1
    except Exception as e:
        logger.info(f"Agent 5: pdflatex compilation failed. Error: {e}")
        return -1

def tailor_resume(llm_router: LLMRouter, base_resume_path: str, company_name: str, job_title: str, job_description: str, job_id: int, output_dir: str = None, mode: str = "application") -> tuple[str, str]:
    logger.info(f"Agent 5: Tailoring resume for Job {job_id} ({job_title} at {company_name}) | Mode: {mode.upper()}...")
    
    if not output_dir:
        output_dir = str(Config.DATA_DIR)
    out_dir_path = Path(output_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    
    if not os.path.exists(base_resume_path):
        raise FileNotFoundError(f"CRITICAL: Cannot find base resume at {base_resume_path}. Agent 5 is strictly forbidden from generating resumes from scratch.")
        
    with open(base_resume_path, "r") as f:
        base_template = f.read()
        
    # 1. JD Parsing
    logger.info("Agent 5: Parsing Job Description...")
    jd_intel = parse_jd(llm_router, job_title, job_description)
    role_type = jd_intel["role_type"]
    
    # 2. Role Routing (Priority Projects)
    priority_projects = []
    if role_type == "AI":
        priority_projects = ["CareerAutomated", "AI Data Analyst Agent", "Semantic Search Engine", "RAG"]
    elif role_type == "PRODUCT":
        priority_projects = ["YAAR", "CareerAutomated", "Orange Labs", "User Behaviour Systems"]
    elif role_type == "BUSINESS":
        priority_projects = ["YAAR", "CareerAutomated", "Orange Labs", "ScoreMe"]
    else: # SDE
        priority_projects = ["CareerAutomated", "AI Data Analyst Agent", "Backend Systems"]
        
    # 3. RAG Retrieval
    logger.info(f"Agent 5: Retrieving context for Role Type: {role_type}...")
    rag = RAGClient()
    search_query = f"{job_title} {job_description[:500]} {' '.join(jd_intel['skills'])} {' '.join(priority_projects)}"
    retrieved_chunks = rag.retrieve(search_query, top_k_initial=15, top_k_final=5)
    
    context_text = "\n".join([f"[{c['type'].upper()}] {c['text']}" for c in retrieved_chunks])
    
    # Gather allowed numbers for Metric Grounding
    allowed_numbers = extract_numbers(context_text) | extract_numbers(base_template)
    
    user_prompt = f"""
    COMPANY NAME: {company_name}
    JOB TITLE: {job_title}
    
    TARGET DOMAIN: {jd_intel['domain']}
    REQUIRED SKILLS: {', '.join(jd_intel['skills'])}
    JD KEYWORDS: {', '.join(jd_intel['keywords'])}
    
    ROLE TYPE ROUTING: {role_type}
    PRIORITY PROJECTS/INTERNSHIPS TO INCLUDE: {', '.join(priority_projects)}
    
    RETRIEVED CANDIDATE CONTEXT (Single Source of Truth):
    {context_text}
    
    BASE RESUME TEMPLATE (Modify this):
    {base_template}
    """
    
    logger.info("Agent 5: Generating tailored LaTeX...")
    messages = [
        {"role": "system", "content": RESUME_WRITER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    response = llm_router.chat_completion(messages, temperature=0.3, intent="reasoning")
    tailored_tex = response.choices[0].message.content
    
    # Extract only the LaTeX block
    tex_match = re.search(r'\\documentclass.*\\end\{document\}', tailored_tex, re.DOTALL)
    if tex_match:
        tailored_tex = tex_match.group(0)
    else:
        tailored_tex = tailored_tex.replace("```latex", "").replace("```", "").strip()
    
    # 4. Validation Gate & Metric Grounding
    logger.info("Agent 5: Validating Output and Metric Grounding...")
    
    base_projects = extract_projects_from_tex(base_template)
    tailored_projects = extract_projects_from_tex(tailored_tex)
    
    # Check for hallucinated metrics in each project block
    for proj_name, proj_block in tailored_projects.items():
        # Only check the actual text inside \resumeItem{}
        bullets = re.findall(r'\\resumeItem\{(.*?)\}', proj_block, re.DOTALL)
        bullet_text = " ".join(bullets)
        
        proj_numbers = extract_numbers(bullet_text)
        unsupported = proj_numbers - allowed_numbers
        if unsupported:
            logger.info(f"  [Metric Grounding] Violation in Project '{proj_name}': {unsupported}. Restoring original bullet block.")
            # Find closest match in base resume
            closest_base_proj = None
            for bp_name, bp_block in base_projects.items():
                if bp_name.lower() in proj_name.lower() or proj_name.lower() in bp_name.lower():
                    closest_base_proj = bp_block
                    break
            
            if closest_base_proj:
                tailored_tex = tailored_tex.replace(proj_block, closest_base_proj)
            else:
                # If we can't find original, we might have to delete it, but user said DO NOT DELETE.
                # So we just fallback to base template entirely if it's too mangled.
                logger.info(f"  [Metric Grounding] Could not find original for '{proj_name}'.")

    # 5. Telemetry & Scoring
    logger.info(f"--- TELEMETRY FOR JOB {job_id} ---")
    logger.info(f"Selected Template: {os.path.basename(base_resume_path)}")
    logger.info(f"Role Type: {role_type}")
    logger.info(f"Retrieved Chunks: {len(retrieved_chunks)}")
    logger.info(f"JD Skills Found: {len(jd_intel['skills'])}")
    logger.info("-----------------------------------")
    
    # 6. Compilation
    tex_path = out_dir_path / f"tailored_resume_{job_id}.tex"
    pdf_path = out_dir_path / f"tailored_resume_{job_id}.pdf"
    
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(tailored_tex)
        
    logger.info("Agent 5: Compiling PDF...")
    pages = compile_and_count_pages(tex_path, out_dir_path)
    
    if pages > 1:
        logger.info("Agent 5 Warning: Resume exceeds 1 page! Using base resume as safe fallback.")
        return base_resume_path, "Base Resume (Fallback)"
        
    if not os.path.exists(pdf_path):
        logger.info("Agent 5 Error: PDF compilation failed. Using base resume.")
        return base_resume_path, "Base Resume (Fallback)"
        
    return str(pdf_path), priority_projects[0] if priority_projects else "Dynamic Tailored"
