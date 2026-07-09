import sqlite3
import json
import time
from typing import Optional, Dict, Any, List

class NegativeCache:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS negative_cache (
                key TEXT PRIMARY KEY,
                reason TEXT,
                timestamp REAL
            )''')
            
    def get(self, key: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT reason, timestamp FROM negative_cache WHERE key = ?", (key,))
            row = cur.fetchone()
            if row:
                reason, timestamp = row
                if time.time() - timestamp < 7 * 86400: # 7 days TTL
                    return reason
        return None
        
    def set(self, key: str, reason: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO negative_cache (key, reason, timestamp) VALUES (?, ?, ?)",
                         (key, reason, time.time()))

class SearchCache:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS search_cache (
                query TEXT PRIMARY KEY,
                url TEXT,
                timestamp REAL
            )''')
            
    def get(self, query: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT url FROM search_cache WHERE query = ?", (query,))
            row = cur.fetchone()
            return row[0] if row else None
            
    def set(self, query: str, url: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO search_cache (query, url, timestamp) VALUES (?, ?, ?)",
                         (query, url, time.time()))

class ReplayCache:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS replay_cache (
                url TEXT PRIMARY KEY,
                method TEXT,
                final_url TEXT,
                status_code INTEGER,
                request_headers TEXT,
                response_headers TEXT,
                payload BLOB,
                redirect_chain TEXT,
                pipeline_version TEXT,
                parser_version TEXT,
                timestamp REAL
            )''')
            
    def get(self, url: str, method: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT final_url, status_code, request_headers, response_headers, payload, redirect_chain, timestamp FROM replay_cache WHERE url = ? AND method = ?", (url, method))
            row = cur.fetchone()
            if row:
                final_url, status_code, req_hdrs, res_hdrs, payload, redirect_chain, timestamp = row
                if time.time() - timestamp < 7 * 86400: # 7 days TTL
                    return {
                        "final_url": final_url,
                        "status_code": status_code,
                        "request_headers": json.loads(req_hdrs),
                        "response_headers": json.loads(res_hdrs),
                        "payload": payload,
                        "redirect_chain": json.loads(redirect_chain)
                    }
        return None
        
    def set(self, url: str, method: str, final_url: str, status_code: int, request_headers: Dict[str, str], response_headers: Dict[str, str], payload: bytes, redirect_chain: List[str], pipeline_version: str = "v1", parser_version: str = "v1"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''INSERT OR REPLACE INTO replay_cache 
                (url, method, final_url, status_code, request_headers, response_headers, payload, redirect_chain, pipeline_version, parser_version, timestamp) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (url, method, final_url, status_code, json.dumps(request_headers), json.dumps(response_headers), payload, json.dumps(redirect_chain), pipeline_version, parser_version, time.time()))
