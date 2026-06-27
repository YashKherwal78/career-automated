import re
from datetime import datetime
from src.discovery.providers.base_provider import StandardJob

class MarkdownJobParser:
    """
    Parses Markdown tables to extract Job information.
    """
    def __init__(self):
        # A simple regex to parse a markdown table row
        self.row_pattern = re.compile(r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*(?:\[.*\]\(([^)]+)\)|([^|]+))\s*\|')

    def parse_file(self, file_path: str, source_name: str) -> list[StandardJob]:
        jobs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            in_table = False
            for line in lines:
                if line.strip().startswith('|---'):
                    in_table = True
                    continue
                    
                if in_table and line.strip().startswith('|'):
                    match = self.row_pattern.search(line)
                    if match:
                        company = match.group(1).strip()
                        role = match.group(2).strip()
                        location = match.group(3).strip()
                        url = match.group(4) or match.group(5)
                        if url: url = url.strip()
                        
                        jobs.append(StandardJob(
                            company=company,
                            role=role,
                            location=location,
                            remote_hybrid_onsite="Unknown",
                            experience_required="Unknown",
                            skills=[],
                            job_description="",
                            ats_type="unknown",
                            application_url=url,
                            source=source_name,
                            date_posted=datetime.utcnow().isoformat()
                        ))
                elif not line.strip():
                    in_table = False
                    
        except Exception as e:
            print(f"Error parsing markdown file {file_path}: {e}")
            
        return jobs
