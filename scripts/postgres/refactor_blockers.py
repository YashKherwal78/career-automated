import os
import json
from pathlib import Path
import re

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
ARTIFACTS_DIR = Path("/Users/yashkherwal/.gemini/antigravity-ide/brain/3397c432-b914-4863-8892-a136b7baf897/artifacts/postgres")

def refactor():
    with open(ARTIFACTS_DIR / "production_runtime_audit.json", "r") as f:
        data = json.load(f)
        
    blockers = data.get("production_blockers", [])
    
    # Group by file
    files_to_refactor = {}
    for b in blockers:
        files_to_refactor.setdefault(b["file"], []).append(b)
        
    for rel_path, items in files_to_refactor.items():
        file_path = SRC_DIR / rel_path
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        needs_import = True
        for line in lines:
            if "from src.api.db import get_connection" in line:
                needs_import = False
                break
                
        # Simple replacement
        # Find sqlite3.connect(...) and replace with get_connection()
        for i, line in enumerate(lines):
            # Just do a naive replace for now since it's mostly straightforward
            if "sqlite3.connect(" in line:
                # We want to replace `sqlite3.connect(...)` with `get_connection()`
                # Handle `with sqlite3.connect(...) as conn:` -> `with get_connection() as conn:`
                # Handle `conn = sqlite3.connect(...)` -> `conn = get_connection()`
                # Handle `self.conn = sqlite3.connect(...)` -> `self.conn = get_connection()`
                
                new_line = re.sub(r'sqlite3\.connect\([^)]*\)', 'get_connection()', line)
                lines[i] = new_line
                
        if needs_import:
            # Add import near top, after standard library or __future__
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    lines.insert(i, "from src.api.db import get_connection\n")
                    break
                    
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
    print(f"Refactored {len(files_to_refactor)} files.")

if __name__ == "__main__":
    refactor()
