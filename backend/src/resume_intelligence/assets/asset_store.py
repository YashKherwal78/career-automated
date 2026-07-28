"""
Resume Asset Store Subsystem (Refinement 4).

Centralized persistence for all candidate resume artifacts.
Artifacts stored:
- Original Uploads (PDF/DOCX)
- Parsed Profiles & Candidate Evidence
- Master Resumes & Tailored Resumes (v1, v2, v3)
- Compiled PDFs, DOCXs, HTMLs
- Job associations and lineage

Supports single-line retrieval: `best_resume(job_id)`
"""

import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from src.resume_intelligence.canonical.models import CanonicalCandidateProfile


class ResumeAsset(BaseModel):
    asset_id: str
    job_id: str = "master"
    company_name: str = "Canonical Master"
    version: str = "v1"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    html_path: Optional[str] = None
    tex_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResumeAssetStore:
    """Centralized persistence store for all resume assets."""

    def __init__(self, storage_dir: str = "data/resume_assets"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.index_path = os.path.join(storage_dir, "asset_index.json")
        self.assets: Dict[str, ResumeAsset] = self._load_index()

    def _load_index(self) -> Dict[str, ResumeAsset]:
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {k: ResumeAsset(**v) for k, v in data.items()}
            except Exception:
                return {}
        return {}

    def _save_index(self):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump({k: v.model_dump() for k, v in self.assets.items()}, f, indent=2)

    def register_asset(self, asset: ResumeAsset):
        self.assets[asset.asset_id] = asset
        self._save_index()

    def best_resume(self, job_id: str) -> Optional[ResumeAsset]:
        """Returns the best matching stored resume asset for a given job_id."""
        matching = [a for a in self.assets.values() if a.job_id == job_id]
        if matching:
            return sorted(matching, key=lambda a: a.created_at, reverse=True)[0]
        
        # Fallback to master
        masters = [a for a in self.assets.values() if a.job_id == "master"]
        if masters:
            return sorted(masters, key=lambda a: a.created_at, reverse=True)[0]
        return None
