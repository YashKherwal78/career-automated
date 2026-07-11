import os
import subprocess
from datetime import datetime
from src.crm.database import get_connection

class RepositoryManager:
    """
    Handles cloning, pulling, and incremental sync of Git repositories.
    """
    def __init__(self, data_dir: str = "data/repos"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def _run_git(self, cmd: list, cwd: str) -> str:
        result = subprocess.run(["git"] + cmd, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Git command failed: {result.stderr}")
        return result.stdout.strip()

    def sync(self, source_id: str, url: str) -> dict:
        repo_path = os.path.join(self.data_dir, source_id)
        
        # Clone or Pull
        if not os.path.exists(repo_path):
            subprocess.run(["git", "clone", url, repo_path], check=True)
        else:
            self._run_git(["pull"], cwd=repo_path)
            
        current_hash = self._run_git(["rev-parse", "HEAD"], cwd=repo_path)
        
        # Get sync state
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT sync_token FROM data_source_sync_state WHERE source_id = ?", (source_id,))
        row = c.fetchone()
        last_hash = row[0] if row else None
        conn.close()
        
        changed_files = []
        if last_hash and last_hash != current_hash:
            # We have a previous sync point, get diff
            diff = self._run_git(["diff", "--name-only", last_hash, current_hash], cwd=repo_path)
            changed_files = [os.path.join(repo_path, f) for f in diff.split("\n") if f.strip()]
        else:
            # Initial sync or no changes
            for root, _, files in os.walk(repo_path):
                for file in files:
                    if file.endswith(".md") or file.endswith(".csv"):
                        changed_files.append(os.path.join(root, file))
                        
        return {
            "current_hash": current_hash,
            "changed_files": changed_files,
            "is_incremental": last_hash is not None and last_hash != current_hash
        }
