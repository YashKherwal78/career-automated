import re
from pathlib import Path
from src.config.config import Config

class ProfileParser:
    def __init__(self):
        self.profile_path = Config.DATA_DIR / "context" / "yash_master_profile.md"
        self.content = ""
        self._load_profile()

    def _load_profile(self):
        if self.profile_path.exists():
            with open(self.profile_path, "r", encoding="utf-8") as f:
                self.content = f.read()

    def extract_section(self, section_prefix: str) -> str:
        """
        Extracts content starting from `section_prefix` until the next `## SECTION` or EOF.
        Example section_prefix: "## SECTION 1: IDENTITY SNAPSHOT"
        """
        if not self.content:
            return ""

        pattern = rf"({re.escape(section_prefix)}.*?)(?=## SECTION |\Z)"
        match = re.search(pattern, self.content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def extract_project(self, project_keyword: str) -> str:
        """
        Extracts a specific project block from Section 4 based on a keyword.
        Example project_keyword: "YAAR", "SC-MFC", "Data Analyst Agent"
        """
        section_4 = self.extract_section("## SECTION 4: PROJECT INTELLIGENCE")
        if not section_4:
            return ""

        # Find all project blocks in Section 4
        # Projects start with "### Project " and end at the next "### Project " or "---" or EOF
        project_pattern = r"(### Project .*?(?=(?:### Project |---|\Z)))"
        projects = re.findall(project_pattern, section_4, re.DOTALL)

        # Match the closest project name
        keyword_lower = project_keyword.lower()
        for p in projects:
            if keyword_lower in p.lower():
                return p.strip()
                
        # Fallback if specific project name doesn't precisely match
        return ""

    def get_tailored_context(self, project_keyword: str) -> str:
        """
        Builds the minimal context for template generation.
        Includes ONLY the Specific Project details to save tokens.
        """
        project_content = self.extract_project(project_keyword)

        tailored = f"""
## SELECTED PROJECT
{project_content if project_content else f"Focus on general software/AI skills (Project '{project_keyword}' not explicitly found)."}
"""
        return tailored.strip()
