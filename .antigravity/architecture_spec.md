# Antigravity Intelligence Core Specification

This document compiles the entire architectural blueprint you have designed today. You can edit this file directly to tweak the rules, APIs, or plugin structures before we build them.

## 1. The Golden Rule
Before writing any code, Antigravity must:
1. Query the Abstract GraphBackend (Graphiti default).
2. Traverse the dependency graph to calculate the blast radius.
3. Search semantically (FAISS/BM25).
4. Search symbolically (Code Index / LSP).
5. Search Git history (GitPython).
6. Only then generate code.

## 2. Directory Structure & Plugins
```text
.antigravity/
├── mcp_server.py (The 12-Step Pipeline Orchestrator)
├── capabilities.yaml (The Capability Registry)
├── routing.yaml (Executor Policy Routing)
├── executor_registry.py (Native, Aider, OpenHands)
├── plugins/
│   ├── planner/ (planner.py, dependency_planner.py, execution_dag.py)
│   ├── guardian/ (rules.yaml, checks.py)
│   ├── duplicate/ (finder.py, merge_suggestions.py)
│   ├── impact/ (blast_radius.py)
│   ├── code_index/ (Tree-sitter + Pyright + GraphBackend)
│   ├── semantic/ (faiss, bm25)
│   ├── runtime/ (cpu.py, memory.py, logs.py, tracing.py)
│   ├── migration/ (schema_diff.py, rollback.py, validate.py)
│   ├── benchmark/ (cost.py, complexity.py, latency.py)
│   ├── knowledge/ (architecture_builder.py, decision_log.py)
│   ├── review/ (Auto PR review)
│   ├── memory/ (Persistent engineering memory)
│   └── tests/ (pytest, mypy, ruff, black)
├── meta/
│   ├── architecture_memory.yaml
│   ├── decision_memory.yaml
│   ├── task_memory.yaml
│   └── ownership_map.yaml
├── reports/ (dependency_graph.svg, hotspots.md, dead_code.md)
└── workflows/
    ├── architecture.yaml, bugfix.yaml, feature.yaml, refactor.yaml
    ├── migration.yaml, incident.yaml, release.yaml
```

## 3. The 12-Step Pre-Flight Pipeline (mcp_server.py)
Every task strictly follows this execution sequence:
1. **Request**: E.g., "Implement Universal Auto Apply"
2. **Planner**: Breaks task into a dependency DAG and execution order.
3. **Capabilities Registry**: Checks `capabilities.yaml` to prevent duplication.
4. **Architecture Guardian**: Validates proposed changes against `guardian/rules.yaml`.
5. **Duplicate Detector**: Scans Graph + AST + Embeddings for similar existing code.
6. **Blast Radius**: Calculates affected downstream components.
7. **Context Builder**: Pre-fetches related files, DB schemas, and docs.
8. **Executor Registry**: Routes to the correct executor based on policy.
9. **Code Review**: Multi-perspective review (architecture, performance, security).
10. **Tests**: Auto-run pytest, mypy, etc.
11. **Memory Update**: Strictly read-only until this step. Updates `meta/` YAMLs.
12. **Execution Report**: Generates a summary (time taken, tests passed, etc.).

## 4. Capability-Based API (Tool Agnostic)
The MCP Server must not hardcode tool names. It exposes:
- `mcp.execute_capability("planning", task)`
- `mcp.execute_capability("architecture_validation", context)`
- `mcp.execute_capability("semantic_search", query)`

## 5. Policy-Driven Executor Routing
Executors are mapped based on task intent in `routing.yaml`:
- `refactor` -> **AiderExecutor**
- `feature` -> **NativeExecutor**
- `autonomous` -> **OpenHandsExecutor**
- `bugfix` -> **NativeExecutor**
- `large_scale` -> **AiderExecutor**

## 6. Required Dependencies (.antigravity/requirements.txt)
- `graphiti`
- `tree-sitter` & `tree-sitter-python`
- `pyright`
- `faiss-cpu`
- `gitpython`
- `sqlite-utils`
- `psutil` & `watchdog`
- `networkx`
- `aider-chat`
- `openhands-ai`

## 7. Repository Score
A weekly/post-task markdown report outputting:
- Architecture: 97
- Duplication: 99
- Coverage: 91
- Dead Code: 96
- Complexity: 88
- Documentation: 94
- Performance: 90
- Overall: 93/100
