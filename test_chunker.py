import os

def extract_between(text, start, end):
    try:
        return text.split(start)[1].split(end)[0]
    except Exception as e:
        return ""

def test_extract():
    with open("data/context/yash_master_profile.md", "r", encoding="utf-8") as f:
        content = f.read()
        
    chunks = []
    
    exp_section = extract_between(content, "## SECTION 3: EXPERIENCE INTELLIGENCE", "## SECTION 4")
    if exp_section:
        experiences = exp_section.split("### Experience")
        for exp in experiences[1:]:
            chunk_text = "### Experience" + exp.strip().split("---")[0].strip()
            chunks.append({"type": "internship", "text": chunk_text})

    proj_section = extract_between(content, "## SECTION 4: PROJECT INTELLIGENCE", "## SECTION 5")
    if proj_section:
        projects = proj_section.split("### Project")
        for proj in projects[1:]:
            chunk_text = "### Project" + proj.strip().split("---")[0].strip()
            chunks.append({"type": "project", "text": chunk_text})

    skills_section = extract_between(content, "## SECTION 5: PERSONAL PROFILE", "## SECTION 6")
    if skills_section:
        skills = skills_section.split("### ")
        for skill_block in skills[1:]:
            clean_block = skill_block.strip().split("---")[0].strip()
            if "Strengths" in clean_block or "Skills" in clean_block:
                chunks.append({"type": "skill", "text": "### " + clean_block})
            if "Ownership" in clean_block or "Working Style" in clean_block:
                chunks.append({"type": "behavioral", "text": "### " + clean_block})

    interview_section = extract_between(content, "## SECTION 8: INTERVIEW INTELLIGENCE", "## SECTION 9")
    if interview_section:
        stories = interview_section.split("**On ")
        for story in stories[1:]:
            clean_story = story.strip().split("---")[0].strip()
            chunks.append({"type": "behavioral", "text": "**On " + clean_story})

    print(f"Extracted {len(chunks)} total chunks.")
    for c in chunks:
        print(f"[{c['type'].upper()}] {c['text'][:50]}...")
        
if __name__ == "__main__":
    test_extract()
