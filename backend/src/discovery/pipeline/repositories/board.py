import json
import sqlite3
from typing import List, Optional
from src.discovery.models import Board, StandardBoardIdentity, WorkdayBoardIdentity, BoardIdentity
from src.discovery.pipeline.repositories.base import BaseRepository

class BoardRepository(BaseRepository):
    def _init_db(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS boards (
                    id TEXT PRIMARY KEY,
                    provider TEXT,
                    endpoint TEXT,
                    identity_json TEXT,
                    metadata_json TEXT,
                    discovered_by TEXT,
                    discovered_at REAL,
                    last_verified_at REAL,
                    last_sync_at REAL,
                    next_sync_at REAL,
                    sync_priority INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'ACTIVE'
                )
            """)
            conn.commit()

    def add(self, board: Board):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO boards 
                (id, provider, endpoint, identity_json, metadata_json, discovered_by, discovered_at, last_verified_at, last_sync_at, next_sync_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                board.identity.get_hash() if hasattr(board.identity, 'get_hash') else getattr(board.identity, 'board_token', board.endpoint),
                board.provider,
                board.endpoint,
                json.dumps(board.identity.__dict__),
                json.dumps(board.metadata),
                board.discovered_by,
                board.discovered_at,
                board.last_verified_at,
                getattr(board, 'last_sync_at', 0.0),
                getattr(board, 'next_sync_at', 0.0),
                getattr(board, 'status', 'ACTIVE')
            ))
            conn.commit()

    def get_due_boards(self, current_time: float, limit: int = 100) -> List[Board]:
        boards = []
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM boards 
                WHERE status = 'ACTIVE' AND next_sync_at <= ?
                ORDER BY sync_priority DESC, next_sync_at ASC
                LIMIT ?
            """, (current_time, limit))
            
            for row in cursor.fetchall():
                identity_dict = json.loads(row['identity_json'])
                provider = row['provider']
                
                if provider == 'workday':
                    identity = WorkdayBoardIdentity(**identity_dict)
                elif provider in ['greenhouse', 'lever', 'ashby', 'smartrecruiters']:
                    identity = StandardBoardIdentity(**identity_dict)
                else:
                    identity = BoardIdentity(**identity_dict)
                    
                board = Board(
                    identity=identity,
                    endpoint=row['endpoint'],
                    provider=provider,
                    discovered_by=row['discovered_by'],
                    discovered_at=row['discovered_at'],
                    last_verified_at=row['last_verified_at'],
                    metadata=json.loads(row['metadata_json'])
                )
                board.last_sync_at = row['last_sync_at']
                board.next_sync_at = row['next_sync_at']
                board.status = row['status']
                boards.append(board)
        return boards

    def update_sync_status(self, board_id: str, last_sync_at: float, next_sync_at: float, new_metadata: dict):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE boards 
                SET last_sync_at = ?, next_sync_at = ?, metadata_json = ?
                WHERE id = ?
            """, (last_sync_at, next_sync_at, json.dumps(new_metadata), board_id))
            conn.commit()
