import re
from typing import Tuple, Optional
from urllib.parse import urlparse
from src.discovery.models import BoardIdentity, WorkdayBoardIdentity

class WorkdayParser:
    def parse(self, url: str) -> Tuple[Optional[BoardIdentity], float, Optional[str]]:
        """
        Returns (ParsedIdentity, Confidence, FailureReason)
        """
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return None, 0.0, "No hostname found"
            
        if 'myworkdayjobs.com' not in hostname and 'apply.workday.com' not in hostname:
            return None, 0.0, "Not a recognized Workday domain"
            
        path = parsed.path.strip('/')
        # Strip locales like en-US
        path = re.sub(r'^[a-z]{2}-[A-Z]{2}/', '', path)
        
        tenant = None
        site = None
        confidence = 0.0
        
        # Pattern A: tenant.wd[0-9].myworkdayjobs.com/site
        match_a = re.match(r'^([^.]+)\.wd\d+\.myworkdayjobs\.com$', hostname)
        if match_a:
            tenant = match_a.group(1)
            path_parts = [p for p in path.split('/') if p]
            if path_parts:
                if 'job' in path_parts or 'jobs' in path_parts:
                    if path_parts[0] not in ('job', 'jobs'):
                        site = path_parts[0]
                        confidence = 0.9
                    else:
                        site = "ExternalCareerSite"
                        confidence = 0.7
                else:
                    site = path_parts[0]
                    confidence = 0.95
            else:
                site = "ExternalCareerSite"
                confidence = 0.8
                
        # Pattern B: wd[0-9].myworkdayjobs.com/tenant/site
        if not tenant:
            match_b_recruiting = re.search(r'recruiting/([^/]+)/([^/?#]+)', parsed.path)
            if match_b_recruiting:
                tenant = match_b_recruiting.group(1)
                site = match_b_recruiting.group(2)
                confidence = 1.0

        if not tenant:
            # Pattern C: apply.workday.com/tenant/...
            if hostname == 'apply.workday.com':
                path_parts = [p for p in path.split('/') if p]
                if path_parts:
                    tenant = path_parts[0]
                    if len(path_parts) > 1:
                        site = path_parts[1]
                        confidence = 0.9
                    else:
                        site = "ExternalCareerSite"
                        confidence = 0.6

        if tenant and site:
            return WorkdayBoardIdentity(ats='workday', tenant=tenant, site=site), confidence, None
            
        return None, 0.0, "Could not extract tenant and site from URL"

class GreenhouseParser:
    def parse(self, url: str) -> Tuple[Optional[BoardIdentity], float, Optional[str]]:
        from src.discovery.models import GreenhouseBoardIdentity
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return None, 0.0, "No hostname found"
            
        if 'greenhouse.io' not in hostname:
            return None, 0.0, "Not a recognized Greenhouse domain"
            
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        
        if len(path_parts) > 0:
            board_token = path_parts[0]
            # Handle greenhouse.io/embed/job_board
            if board_token == 'embed' and len(path_parts) > 1 and path_parts[1] == 'job_board':
                return None, 0.0, "Embedded board without token in path"
            return GreenhouseBoardIdentity(ats='greenhouse', board_token=board_token), 1.0, None
            
        return None, 0.0, "Could not extract board token"

class LeverParser:
    def parse(self, url: str) -> Tuple[Optional[BoardIdentity], float, Optional[str]]:
        from src.discovery.models import LeverBoardIdentity
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return None, 0.0, "No hostname found"
            
        if 'lever.co' not in hostname:
            return None, 0.0, "Not a recognized Lever domain"
            
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        if len(path_parts) > 0:
            board_token = path_parts[0]
            return LeverBoardIdentity(ats='lever', board_token=board_token), 1.0, None
            
        return None, 0.0, "Could not extract board token"
