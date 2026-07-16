from src.api.db import get_connection
import sqlite3
import json
import os
from typing import List
from src.discovery.models import Board, BoardIdentity, StandardBoardIdentity, WorkdayBoardIdentity

class BoardRegistry:
    def __init__(self, db_path: str = "boards.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS boards (
                    id TEXT PRIMARY KEY,
                    company_name TEXT,
                    provider TEXT,
                    identity_json TEXT,
                    endpoint TEXT,
                    discovered_by TEXT,
                    discovered_at REAL,
                    last_verified_at REAL,
                    last_crawled_at REAL,
                    status TEXT,
                    active BOOLEAN,
                    etag TEXT,
                    last_modified TEXT,
                    metadata_json TEXT
                )
            """)
            conn.commit()
            
    def _generate_id(self, company_name: str, identity: BoardIdentity) -> str:
        import hashlib
        # create a deterministic hash for the board
        if isinstance(identity, StandardBoardIdentity):
            key = f"{company_name}_{identity.ats}_{identity.board_token}"
        elif isinstance(identity, WorkdayBoardIdentity):
            key = f"{company_name}_{identity.ats}_{identity.tenant}_{identity.site}_{identity.locale}"
        else:
            key = f"{company_name}_{identity.ats}"
        return hashlib.md5(key.encode()).hexdigest()
        
    def upsert_board(self, company_name: str, board: Board):
        board_id = self._generate_id(company_name, board.identity)
        
        identity_dict = board.identity.__dict__
        identity_dict['ats'] = board.identity.ats
        
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO boards (
                    id, company_name, provider, identity_json, endpoint,
                    discovered_by, discovered_at, last_verified_at,
                    status, active, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    last_verified_at=excluded.last_verified_at,
                    endpoint=excluded.endpoint,
                    status='verified',
                    active=1
            """, (
                board_id, company_name, board.provider, json.dumps(identity_dict), board.endpoint,
                board.discovered_by, board.discovered_at, board.last_verified_at,
                'verified', True, json.dumps(board.metadata)
            ))
            conn.commit()
            
    def get_active_boards(self) -> List[dict]:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM boards WHERE active = 1")
            return [dict(row) for row in cursor.fetchall()]
