# ADR-002: Screening Philosophy — Tri-State Evaluation & Progressive Profiling

**Status**: Accepted
**Date**: 2026-07-24

## Context

The legacy `HardRejectFilter` evaluated job descriptions with hardcoded thresholds and binary KEEP/REJECT outcomes. This had two fundamental drawbacks:

1. **Hardcoded Fresher Rules**: Hardcoded logic like "reject if experience < 5 years" broke multi-user scalability.
2. **Context Poisoning / Data Gaps**: When candidate facts (e.g. visa sponsorship status or salary expectation) were missing, the filter either rejected jobs prematurely or ignored constraints entirely.

## Decision

We establish the **Screening Philosophy**:

1. **Narrow Scope**: The screening layer exists *solely* to eliminate jobs that are confidently impossible or explicitly outside user-stated constraints. It does NOT evaluate fit or compute scores.
2. **Tri-State Rule Routing**:
   - `PASS`: Candidate explicitly satisfies or accepts the parameter.
   - `REJECT`: Unambiguous conflict with explicit candidate constraints.
   - `UNKNOWN`: Information is missing. Flagged as `MissingField` in `unknown`.
3. **`UNKNOWN` Always Continues**: Missing candidate/job facts generate `MissingField` entries for progressive profiling, but **NEVER** trigger an overall `REJECT`.
4. **Deterministic `overall` Output**:
   ```python
   overall: Literal["PASS", "REJECT"] = "REJECT" if conflicts else "PASS"
   ```

## Structure

```text
screening/
  models.py        # MissingField, RuleDecision (PASS, REJECT, UNKNOWN), ScreeningResult
  interfaces.py    # ScreeningRule protocol
  eligibility.py   # EligibilityChecker (citizenship, visa, security clearance)
  preferences.py   # PreferenceMatcher (work mode, location, salary)
  orchestrator.py  # ScreeningOrchestrator
```

## Consequences

### Positive
- **Progressive Profiling**: Missing user facts trigger clean `MissingField` prompts without breaking search pipelines.
- **Safety**: Unambiguous conflicts stop early; ambiguous or partial information passes through to the `ComparisonEngine`.
- **Determinism**: Zero non-deterministic LLM scoring in screening.

### Negative
- Unpopulated candidate profiles may pass more jobs through screening into the `ComparisonEngine`.
