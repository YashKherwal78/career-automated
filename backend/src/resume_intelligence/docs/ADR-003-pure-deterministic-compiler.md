"""
Architecture Decision Record 003: Pure Deterministic Compiler (Zero-LLM Rendering).
"""

# ADR-003: Pure Deterministic Compiler (Zero-LLM Rendering)

## Status
Accepted

## Context
Previous resume compilation attempts relied on LLM calls to format LaTeX or HTML markup, introducing syntax errors, missing brackets, and compilation timeouts.

## Decision
Build a **Pure Deterministic Compiler** (`PureResumeCompiler`) that renders PDF, DOCX, and HTML outputs using standard Jinja2 templates, ReportLab, and `python-docx`. The compiler NEVER makes an LLM call.

## Consequences
- 100% reliable resume rendering.
- Sub-second document compilation speeds.
- Complete separation of AI content generation from visual template compilation.
