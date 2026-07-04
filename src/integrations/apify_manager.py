import sqlite3
import datetime
from apify_client import ApifyClient
from src.config.config import Config

class ApifyManager:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DATABASE_PATH)
        self.conn.row_factory = sqlite3.Row
        self._register_keys()
        
    def _register_keys(self):
        """Registers keys from Config into SQLite on startup to track them across runs."""
        cursor = self.conn.cursor()
        for i, key_val in enumerate(Config.APIFY_KEYS, 1):
            env_var_name = f"APIFY_KEY_{i}"
            cursor.execute("SELECT id FROM apify_keys WHERE env_var_name = ?", (env_var_name,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO apify_keys (env_var_name, status) VALUES (?, 'ACTIVE')", 
                    (env_var_name,)
                )
        self.conn.commit()
        
    def get_total_spend(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(credits_used) FROM apify_keys")
        res = cursor.fetchone()[0]
        return res if res else 0.0
        
    def get_client(self, tier: int, category: str):
        """
        Tier 1: Recruiter, Hiring Manager, Referral Discovery
        Tier 2: Product Discovery, People Search
        Tier 3: Company Intel
        Tier 4: Bulk Job Discovery
        """
        total_spend = self.get_total_spend()
        
        # Hard Limit
        if total_spend >= Config.APIFY_HARD_LIMIT:
            print(f"ApifyManager: HARD LIMIT REACHED (${total_spend:.2f} >= ${Config.APIFY_HARD_LIMIT:.2f}). Rejecting {category}.")
            return None, None
            
        # Soft Limit
        if total_spend >= Config.APIFY_SOFT_LIMIT and tier > 2:
            print(f"ApifyManager: SOFT LIMIT REACHED (${total_spend:.2f} >= ${Config.APIFY_SOFT_LIMIT:.2f}). Rejecting Tier {tier} {category}.")
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
            print("ApifyManager: No ACTIVE keys available!")
            return None, None
            
        key_id = key_record["id"]
        env_var_name = key_record["env_var_name"]
        
        # Find the actual key value from config
        key_index = int(env_var_name.split("_")[-1]) - 1
        if key_index < 0 or key_index >= len(Config.APIFY_KEYS):
            print(f"ApifyManager Error: {env_var_name} mapped in DB but missing in .env")
            return None, None
            
        actual_key_val = Config.APIFY_KEYS[key_index]
        
        print(f"ApifyManager: Routing {category} (Tier {tier}) to {env_var_name}")
        return ApifyClient(actual_key_val), key_id

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
            # We degrade success rate slightly on failure
            cursor.execute("""
                UPDATE apify_keys 
                SET runs_executed = runs_executed + 1, 
                    success_rate = success_rate * 0.95,
                    last_used = ? 
                WHERE id = ?
            """, (now, key_id))
            
            # If success rate drops below 50, rate limit or disable
            cursor.execute("SELECT success_rate FROM apify_keys WHERE id = ?", (key_id,))
            sr = cursor.fetchone()[0]
            if sr < 50.0:
                cursor.execute("UPDATE apify_keys SET status = 'RATE_LIMITED' WHERE id = ?", (key_id,))
                print(f"ApifyManager: Key {key_id} degraded to RATE_LIMITED")
                
        # Update global analytics
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
