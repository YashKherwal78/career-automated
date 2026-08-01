# ADR-005: Semantic Reasoning & Graph Traversal

**Status**: Accepted
**Date**: 2026-07-24

## Context

Previous matching components performed inline string matching or hardcoded dictionary comparisons, mixing ontology relationships with score calculation. This made it difficult to inspect graph relationships independently or discover prerequisites.

## Decision

We establish `SemanticReasoner` as a dedicated graph traversal component:

1. **Zero Scoring Logic**: `SemanticReasoner` performs graph operations, capability adjacency lookups, alias resolution, and prerequisite graph discovery. It **never** calculates or alters numerical match scores.
2. **Delegation Pattern**: `ComparisonEngine` delegates to `SemanticReasoner` for capability adjacencies, maintaining a clean separation between reasoning and scoring.
3. **Graph Operations**:
   - `resolve_aliases(capability)` -> canonical name
   - `is_equivalent(cap1, cap2)` -> boolean equivalence
   - `find_adjacencies(capability)` -> list of `SemanticAdjacency` edges
   - `discover_prerequisites(missing_capability)` -> list of prerequisite capability names

## Consequences

### Positive
- **Graph Reusability**: The graph can be traversed by `ComparisonEngine`, `LearningPlanner`, and `EvidenceBuilder` independently.
- **Pure Reasoning**: Zero risk of score drift or side effects during graph traversals.

## References
- `backend/src/career_intelligence/reasoning/models.py`
- `backend/src/career_intelligence/reasoning/semantic_reasoner.py`
