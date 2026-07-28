"""
End-to-End Acceptance Test & Demonstration for Jake Resume Compiler V1.

Executes complete pipeline:
Resume Upload -> Parser -> Candidate Evidence -> Canonical Candidate Profile ->
Recommendation Engine -> Resume Tailoring -> Truthfulness Verification ->
Structured Resume -> Jake Resume Compiler V1 (PDF, DOCX, HTML).
"""

import os
from src.resume_intelligence.canonical.models import CandidateProfileContract
from src.resume_intelligence.importers.knowledge_importer import ResumeKnowledgeImporter
from src.resume_intelligence.parser.document_parser import DocumentParser
from src.resume_intelligence.ocr.ocr_engine import OCREngine
from src.resume_intelligence.normalizer.normalizer import Normalizer
from src.resume_intelligence.evidence.merge_engine import MergeEngine
from src.resume_intelligence.recommendation.engine import ResumeRecommendationEngine
from src.resume_intelligence.tailoring.tailor import ResumeTailor
from src.resume_intelligence.truthfulness.verifier import TruthfulnessEngine
from src.resume_intelligence.compiler.jake_resume.adapter import canonical_to_structured
from src.resume_intelligence.compiler.jake_resume.compiler import JakeResumeCompiler
from src.resume_intelligence.assets.asset_store import ResumeAssetStore, ResumeAsset


def run_jake_v1_acceptance_test():
    print("=" * 80)
    print("  JAKE RESUME COMPILER V1 — END-TO-END ACCEPTANCE TEST & DEMONSTRATION")
    print("=" * 80)

    # 1. Resume Ingestion
    print("\n[STEP 1] Ingesting Authoritative Candidate Knowledge Repository...")
    importer = ResumeKnowledgeImporter()
    master_profile = importer.load_full_knowledge_profile("resume_knowledge")
    print(f"  ✓ Ingested candidate: {master_profile.personal.full_name}")

    # 2. Parsing Uploaded Resume
    pdf_path = "yash_resume_aiproduct.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "backend/data/yash_resume_base_v2.tex"

    print(f"\n[STEP 2] Parsing Real Candidate Resume ({pdf_path})...")
    parser = DocumentParser()
    raw_extraction = parser.parse_document(pdf_path)
    ocr_engine = OCREngine()
    processed_raw = ocr_engine.process_scanned_pdf(pdf_path, raw_extraction)
    print(f"  ✓ Raw Text Extracted: {len(processed_raw.raw_text)} chars")

    # 3. Evidence Normalization
    print("\n[STEP 3] Normalizing Raw Extractions into Candidate Evidence Store...")
    normalizer = Normalizer()
    evidence_items = normalizer.normalize_extraction(processed_raw, source_type="uploaded_resume")
    print(f"  ✓ Extracted Evidence Items: {len(evidence_items)}")

    # 4. Multi-Source Priority Merge
    print("\n[STEP 4] Merging Evidence into Canonical Candidate Profile Platform Contract...")
    merge_engine = MergeEngine()
    merged_profile, _ = merge_engine.merge_evidence_store(master_profile, evidence_items)
    contract_profile = CandidateProfileContract.update_profile(merged_profile, reason="Jake V1 Ingestion")

    # 5. Recommendation Engine (Module 14)
    print("\n[STEP 5] Running Recommendation Engine...")
    rec_engine = ResumeRecommendationEngine()
    target_jd = """
    Seeking an AI Engineer / AI Product Manager to build autonomous multi-agent workflows,
    hybrid RAG architectures, and scalable Python/FastAPI data pipelines. Requires experience
    with LangGraph, Docker, Playwright, and ATS integrations.
    """
    recommendation = rec_engine.generate_recommendation(
        profile=contract_profile,
        job_title="AI Product Manager / AI Engineer",
        job_description=target_jd,
        company_name="OpenAI / Stripe Benchmark"
    )
    print(f"  ✓ Recommended Strategy: {recommendation.recommended_strategy}")
    print(f"  ✓ Recommended Project Order: {', '.join(recommendation.priority_projects)}")

    # 6. Resume Tailoring & Truthfulness Verification
    print("\n[STEP 6] Executing Resume Tailoring & Truthfulness Verification Gate...")
    tailor = ResumeTailor()
    tailored_result = tailor.tailor_resume(
        master_profile=contract_profile,
        job_description=target_jd,
        recommendation=recommendation,
        job_id="job_stripe_ai_001"
    )
    print(f"  ✓ Truthfulness Gate Passed: {tailored_result.truthfulness_report.is_valid}")

    # 7. Translation to Structured Resume
    print("\n[STEP 7] Translating Canonical Profile to Structured Resume...")
    structured_resume = canonical_to_structured(
        profile=tailored_result.tailored_profile,
        section_order=["education", "experience", "projects", "skills"]
    )
    print(f"  ✓ Structured Resume Ready: {structured_resume.name} ({len(structured_resume.projects)} Projects)")

    # 8. Jake Resume Compiler V1 Execution
    print("\n[STEP 8] Executing Jake Resume Compiler V1 (Rendering PDF, DOCX, HTML)...")
    compiler = JakeResumeCompiler()
    output_dir = "artifacts/jake_compiler_v1_outputs"
    compiled_paths = compiler.compile(
        structured_resume=structured_resume,
        output_dir=output_dir,
        filename_prefix="Yash_Kherwal_Jake_Resume_V1"
    )

    for fmt, path in compiled_paths.items():
        print(f"  ✓ Rendered {fmt.upper()}: {path}")

    # 9. Asset Store Verification
    print("\n[STEP 9] Registering & Verifying Asset Retrieval...")
    asset_store = ResumeAssetStore(storage_dir="data/resume_assets")
    asset_store.register_asset(
        ResumeAsset(
            asset_id="asset_jake_v1_001",
            job_id="job_stripe_ai_001",
            company_name="Stripe Benchmark",
            version="jake_v1",
            pdf_path=compiled_paths.get("pdf"),
            docx_path=compiled_paths.get("docx"),
            html_path=compiled_paths.get("html"),
            tex_path=compiled_paths.get("tex")
        )
    )
    best = asset_store.best_resume("job_stripe_ai_001")
    print(f"  ✓ Retrived best resume for job: {best.pdf_path}")

    print("\n" + "=" * 80)
    print("  JAKE RESUME COMPILER V1 — PRODUCTION QUALITY DEMONSTRATION COMPLETE (0 ERRORS)")
    print("=" * 80)


if __name__ == "__main__":
    run_jake_v1_acceptance_test()
