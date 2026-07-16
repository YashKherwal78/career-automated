import os
import json
from pathlib import Path
import re

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
ARTIFACTS_DIR = Path("/Users/yashkherwal/.gemini/antigravity-ide/brain/3397c432-b914-4863-8892-a136b7baf897/artifacts/postgres")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

DEFERRED_DIRS = [
    "analytics",
    "dashboard",
    "outreach",
    "crm",
    "experiments",
    "bootstrap",
    "tests",
    "scripts",
    "intelligence",
    "referrals",
    "resume",
]

def is_production(file_path: Path) -> bool:
    parts = file_path.relative_to(SRC_DIR).parts
    top_level = parts[0]
    
    if top_level in DEFERRED_DIRS:
        return False
    if top_level == "production" and "outreach" in str(file_path):
        return False
        
    return True

def audit():
    blockers = []
    deferred = []
    
    sqlite_pattern = re.compile(r'sqlite3\.connect\(')
    
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if not file.endswith(".py"):
                continue
                
            file_path = Path(root) / file
            
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    lines = f.readlines()
                except UnicodeDecodeError:
                    continue
                    
            prod = is_production(file_path)
            
            for i, line in enumerate(lines):
                if sqlite_pattern.search(line):
                    if "api/db.py" in str(file_path.relative_to(SRC_DIR).as_posix()):
                        continue
                        
                    entry = {
                        "file": file_path.relative_to(SRC_DIR).as_posix(),
                        "line": i + 1,
                        "code": line.strip(),
                        "reason": "Direct sqlite3.connect bypasses centralized connection layer",
                        "severity": "CRITICAL" if prod else "DEFERRED",
                        "replacement_repository": "src.api.db.get_connection"
                    }
                    
                    if prod:
                        blockers.append(entry)
                    else:
                        deferred.append(entry)
    
    report_md = [
        "# PostgreSQL Migration Preflight — Production Runtime Audit",
        "",
        "## 1. Production Blockers",
        ""
    ]
    
    if not blockers:
        report_md.append("✅ No production blockers found.")
    else:
        for b in blockers:
            report_md.append(f"- **File**: `{b['file']}:{b['line']}`")
            report_md.append(f"  - **Code**: `{b['code']}`")
            report_md.append(f"  - **Reason**: {b['reason']}")
            report_md.append(f"  - **Severity**: {b['severity']}")
            report_md.append("")
            
    report_md.extend([
        "## 2. Deferred Components",
        ""
    ])
    
    if not deferred:
        report_md.append("No deferred components found.")
    else:
        for d in deferred:
            report_md.append(f"- `{d['file']}:{d['line']}`")
            
    report_md.extend([
        "",
        "## 3. Readiness Score",
        "```text",
        f"Overall Readiness: {'100%' if not blockers else 'FAIL'}",
        "```"
    ])
    
    with open(ARTIFACTS_DIR / "postgres_readiness_report.md", "w") as f:
        f.write("\n".join(report_md))
        
    audit_json = {
        "production_blockers": blockers,
        "production_passed": len(blockers) == 0,
        "deferred_components": deferred,
        "remaining_sqlite_calls": len(blockers) + len(deferred),
        "postgres_ready": len(blockers) == 0
    }
    
    with open(ARTIFACTS_DIR / "production_runtime_audit.json", "w") as f:
        json.dump(audit_json, f, indent=2)
        
    graph_md = [
        "# Production Runtime Dependency Graph",
        "```mermaid",
        "graph TD",
        "  FastAPI --> MissionControl",
        "  MissionControl --> Scheduler",
        "  Scheduler --> Workers",
        "  Workers --> Repositories",
        "  Repositories --> DB[Central Database Layer (db.py)]",
        ""
    ]
    
    for b in blockers:
        graph_md.append(f"  {b['file'].split('/')[-1].replace('.py', '')} -.->|BYPASSES REPO| Sqlite[(SQLite Direct)]")
        
    graph_md.append("```")
    
    with open(ARTIFACTS_DIR / "runtime_graph.md", "w") as f:
        f.write("\n".join(graph_md))
        
    print(f"Audit complete. Found {len(blockers)} production blockers and {len(deferred)} deferred components.")

if __name__ == "__main__":
    audit()
