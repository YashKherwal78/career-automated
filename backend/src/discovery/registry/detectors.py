import requests
from typing import Tuple, Optional
from abc import ABC, abstractmethod

class ATSDetector(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def version(self) -> str:
        pass
        
    @abstractmethod
    def detect(self, slug: str) -> Tuple[bool, Optional[str]]:
        """Returns (is_match, valid_slug)"""
        pass

class GreenhouseDetector(ATSDetector):
    @property
    def provider_name(self) -> str: return "greenhouse"
    @property
    def version(self) -> str: return "2.1"
    
    def detect(self, slug: str) -> Tuple[bool, Optional[str]]:
        try:
            r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}", timeout=3)
            if r.status_code == 200:
                return True, slug
        except: pass
        return False, None

class LeverDetector(ATSDetector):
    @property
    def provider_name(self) -> str: return "lever"
    @property
    def version(self) -> str: return "1.3"
    
    def detect(self, slug: str) -> Tuple[bool, Optional[str]]:
        try:
            r = requests.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=3)
            if r.status_code == 200:
                return True, slug
        except: pass
        return False, None

class AshbyDetector(ATSDetector):
    @property
    def provider_name(self) -> str: return "ashby"
    @property
    def version(self) -> str: return "1.1"
    
    def detect(self, slug: str) -> Tuple[bool, Optional[str]]:
        try:
            r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=3)
            if r.status_code == 200:
                return True, slug
        except: pass
        return False, None

class DetectorFactory:
    @staticmethod
    def get_all_detectors():
        return [GreenhouseDetector(), LeverDetector(), AshbyDetector()]
