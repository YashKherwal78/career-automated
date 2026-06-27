import yaml
from typing import List, Dict
from src.discovery.importers.repository_manager import RepositoryManager
from src.crm.database import get_connection

class SourceManager:
    """
    Orchestrates generic sync over multiple specific source managers (Git, CSV, etc.)
    and returns unparsed raw files for parsing.
    """
    def __init__(self, config_path: str = "src/config/data_sources.yaml"):
        self.config_path = config_path
        self.repo_manager = RepositoryManager()
        
    def _load_sources(self) -> List[Dict]:
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
        sources = data.get("sources", [])
        # Sort by priority descending
        sources.sort(key=lambda x: x.get('priority', 0), reverse=True)
        return sources
        
    def _update_sync_state(self, source: dict, sync_token: str, status: str, metadata: str = None):
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO data_source_sync_state 
            (source_id, source_type, source_name, sync_token, status, metadata, last_success)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_id) DO UPDATE SET 
            last_sync = CURRENT_TIMESTAMP,
            sync_token = ?,
            status = ?,
            metadata = ?,
            last_success = CURRENT_TIMESTAMP
        ''', (
            source['id'], source['type'], source['name'], sync_token, status, metadata,
            sync_token, status, metadata
        ))
        conn.commit()
        conn.close()

    def sync_all_sources(self) -> List[Dict]:
        """
        Runs sync across all sources and returns list of files that need parsing.
        """
        sources = self._load_sources()
        results = []
        
        for source in sources:
            if source['type'] == 'github_repo':
                try:
                    sync_data = self.repo_manager.sync(source['id'], source['url'])
                    results.append({
                        "source": source,
                        "files": sync_data["changed_files"],
                        "sync_token": sync_data["current_hash"]
                    })
                    # Update status
                    self._update_sync_state(source, sync_data["current_hash"], "SUCCESS")
                except Exception as e:
                    print(f"Error syncing {source['name']}: {e}")
                    # Update failure state in DB if fully implemented
            else:
                print(f"Source type {source['type']} not yet implemented.")
                
        return results
