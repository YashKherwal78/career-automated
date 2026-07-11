import sqlite3
import time
import json
from typing import Optional
from dataclasses import dataclass
from src.discovery.pipeline.repositories.base import BaseRepository

@dataclass
class DiscoveryCandidate:
    company: str
    provider: str
    url: str
    stage: str
    confidence: float
    verified: bool
    attempt_id: str
    created_at: float = 0.0

class DiscoveryCandidateRepository(BaseRepository):
    def _init_db(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discovery_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    url TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    verified BOOLEAN NOT NULL,
                    attempt_id TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def add(self, candidate: DiscoveryCandidate):
        candidate.created_at = candidate.created_at or time.time()
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO discovery_candidates 
                (company, provider, url, stage, confidence, verified, attempt_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate.company,
                candidate.provider,
                candidate.url,
                candidate.stage,
                candidate.confidence,
                candidate.verified,
                candidate.attempt_id,
                candidate.created_at
            ))
            conn.commit()
