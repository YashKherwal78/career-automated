import requests
import re
from bs4 import BeautifulSoup
from typing import Optional

class JDFetcher:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    def _strip_html(self, html_content: str) -> str:
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        # Preserve basic structure but strip tags
        for br in soup.find_all("br"):
            br.replace_with("\n")
        for li in soup.find_all("li"):
            li.insert(0, "- ")
            li.append("\n")
        for p in soup.find_all(["p", "div", "h1", "h2", "h3", "h4"]):
            p.append("\n\n")
            
        text = soup.get_text(separator=" ", strip=True)
        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()

    def fetch_greenhouse(self, slug: str, job_id: str) -> Optional[str]:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return self._strip_html(data.get("content", ""))
        except Exception as e:
            print(f"Greenhouse fetch error: {e}")
        return None

    def fetch_lever(self, slug: str, job_id: str) -> Optional[str]:
        try:
            url = f"https://api.lever.co/v0/postings/{slug}/{job_id}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                desc = data.get("descriptionPlain", "")
                lists = data.get("lists", [])
                list_texts = []
                for lst in lists:
                    list_texts.append(lst.get("text", ""))
                    list_texts.append(lst.get("content", ""))
                return desc + "\n\n" + "\n\n".join(list_texts)
        except Exception as e:
            print(f"Lever fetch error: {e}")
        return None

    def fetch_ashby(self, slug: str, job_id: str) -> Optional[str]:
        try:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for job in data.get("jobs", []):
                    if str(job.get("id")) == str(job_id):
                        return self._strip_html(job.get("descriptionHtml", ""))
        except Exception as e:
            print(f"Ashby fetch error: {e}")
        return None

    def fetch_workday(self, tenant: str, region: str, custom_site: str, ext_path: str) -> Optional[str]:
        try:
            api_job = f"https://{tenant}.{region}.myworkdayjobs.com/wday/cxs/{custom_site}{ext_path}"
            resp = requests.get(api_job, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                return self._strip_html(resp.json().get("jobPostingInfo", {}).get("jobDescription", ""))
            
            # fallback pattern
            api_job = f"https://{tenant}.{region}.myworkdayjobs.com/wday/cxs/{tenant}/{custom_site}{ext_path}"
            resp = requests.get(api_job, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                return self._strip_html(resp.json().get("jobPostingInfo", {}).get("jobDescription", ""))
        except Exception as e:
            print(f"Workday fetch error: {e}")
        return None

    def fetch_jd(self, provider: str, **kwargs) -> Optional[str]:
        if provider == "greenhouse":
            return self.fetch_greenhouse(kwargs.get("slug"), kwargs.get("job_id"))
        elif provider == "lever":
            return self.fetch_lever(kwargs.get("slug"), kwargs.get("job_id"))
        elif provider == "ashby":
            return self.fetch_ashby(kwargs.get("slug"), kwargs.get("job_id"))
        elif provider == "workday":
            return self.fetch_workday(kwargs.get("tenant"), kwargs.get("region"), kwargs.get("custom_site"), kwargs.get("ext_path"))
        return None
