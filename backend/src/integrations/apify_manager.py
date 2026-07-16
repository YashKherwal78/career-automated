from src.api.db import get_connection
from src.system.logger import setup_logger
logger = setup_logger('apify_manager')
import sqlite3
import datetime
from apify_client import ApifyClient
from src.config.config import Config

class ApifyManager:
    def __init__(self):
        self.conn = get_connection()
        self.conn.row_factory = sqlite3.Row
        
    def register_credential_ids(self, credential_ids: list):
        """Registers credential IDs into SQLite."""
        cursor = self.conn.cursor()
        for c_id in credential_ids:
            cursor.execute("SELECT id FROM apify_keys WHERE env_var_name = ?", (c_id,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO apify_keys (env_var_name, status) VALUES (?, 'ACTIVE')", 
                    (c_id,)
                )
        self.conn.commit()
        
    def get_total_spend(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(credits_used) FROM apify_keys")
        res = cursor.fetchone()[0]
        return res if res else 0.0

    def get_active_credential_id(self):
        """
        Returns (db_id, credential_id) of the least used active credential.
        """
        total_spend = self.get_total_spend()
        
        if total_spend >= Config.APIFY_HARD_LIMIT:
            logger.info(f"ApifyManager: HARD LIMIT REACHED. Rejecting usage.")
            return None, None
            
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, env_var_name FROM apify_keys 
            WHERE status = 'ACTIVE' 
            ORDER BY credits_used ASC 
            LIMIT 1
        """)
        key_record = cursor.fetchone()
        
        if not key_record:
            logger.info("ApifyManager: No ACTIVE keys available!")
            return None, None
            
        return key_record["id"], key_record["env_var_name"]

    def get_client(self, tier: int = 1, category: str = "default"):
        """
        Returns (ApifyClient, key_id) for the least-used active credential.
        tier and category are accepted for compatibility with caller code but
        currently used only for logging.
        Returns (None, None) if no keys are available or budget exceeded.
        """
        import os
        key_id, env_var_name = self.get_active_credential_id()
        if not key_id:
            logger.warning(f"ApifyManager.get_client: no active key available (tier={tier}, category={category})")
            return None, None
        api_key = os.environ.get(env_var_name)
        if not api_key:
            logger.warning(f"ApifyManager.get_client: env var {env_var_name} is empty")
            return None, None
        client = ApifyClient(api_key)
        logger.debug(f"ApifyManager.get_client: using key {env_var_name} (id={key_id}) for category={category}")
        return client, key_id

    def disable_credential(self, key_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE apify_keys SET status = 'AUTH_FAILURE' WHERE id = ?", (key_id,))
        self.conn.commit()

    def record_usage(self, key_id: int, category: str, credits: float, useful_results: int, success: bool = True):
        now = datetime.datetime.now().isoformat()
        cursor = self.conn.cursor()
        
        # Update key stats
        if success:
            cursor.execute("""
                UPDATE apify_keys 
                SET credits_used = credits_used + ?, 
                    runs_executed = runs_executed + 1, 
                    last_used = ?, 
                    last_success = ? 
                WHERE id = ?
            """, (credits, now, now, key_id))
        else:
            cursor.execute("""
                UPDATE apify_keys 
                SET runs_executed = runs_executed + 1, 
                    success_rate = success_rate * 0.95,
                    last_used = ? 
                WHERE id = ?
            """, (now, key_id))
            
            cursor.execute("SELECT success_rate FROM apify_keys WHERE id = ?", (key_id,))
            sr = cursor.fetchone()[0]
            if sr < 50.0:
                cursor.execute("UPDATE apify_keys SET status = 'RATE_LIMITED' WHERE id = ?", (key_id,))
                
        cursor.execute("""
            INSERT INTO apify_analytics (category, runs, credits_consumed, useful_results) 
            VALUES (?, 1, ?, ?)
            ON CONFLICT(category) DO UPDATE SET 
                runs = runs + 1,
                credits_consumed = credits_consumed + excluded.credits_consumed,
                useful_results = useful_results + excluded.useful_results
        """, (category, credits, useful_results))
        
        self.conn.commit()

    def get_analytics_report(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM apify_keys")
        keys = cursor.fetchall()
        
        cursor.execute("SELECT * FROM apify_analytics")
        analytics = cursor.fetchall()
        
        return {
            "total_spend": self.get_total_spend(),
            "keys": [dict(k) for k in keys],
            "analytics": [dict(a) for a in analytics]
        }
