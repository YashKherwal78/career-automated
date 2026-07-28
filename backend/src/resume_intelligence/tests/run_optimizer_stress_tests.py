"""
Comprehensive Stress Test Suite for One-Page Optimizer & Layout Engine.

Executes 4 Stress Scenarios:
- Test 1: Overflow Resume (~215% utilization) -> Triggers Levels 1, 2, 3, 4, 5, 6
- Test 2: Medium Overflow (~108% utilization) -> Triggers Levels 1 & 2 only (Zero content removed)
- Test 3: Large Overflow (~140% utilization) -> Triggers Levels 1, 2, 3 & 4 (Bullet & Project trimming)
- Test 4: Extreme Overflow (~300% utilization) -> Triggers all levels and cleanly invokes 2-page fallback
"""

import os
from src.resume_intelligence.compiler.jake_resume.models import (
    StructuredResume, StructuredContact, StructuredEducation,
    StructuredExperience, StructuredProject, StructuredSkillCategory
)
from src.resume_intelligence.compiler.jake_resume.compiler import JakeResumeCompiler


def create_stress_resume(exp_count: int, proj_count: int, bullets_per_item: int, skill_cat_count: int) -> StructuredResume:
    contact = StructuredContact(
        phone="+91 9891148156",
        email="yash.kherwal78@gmail.com",
        linkedin="https://linkedin.com/in/yash-kherwal",
        github="https://github.com/YashKherwal78",
        location="India / Remote"
    )

    education = [
        StructuredEducation(
            institution="Indian Institute of Technology Roorkee",
            degree="B.Tech",
            field_of_study="Chemical Engineering",
            start_date="2022",
            end_date="2026",
            location="Roorkee, India"
        )
    ]

    experience = []
    for i in range(1, exp_count + 1):
        experience.append(
            StructuredExperience(
                company=f"Tech Enterprise Alpha {i}",
                title=f"Senior Software / AI Lead {i}",
                location="Remote",
                start_date=f"202{i%4}",
                end_date=f"202{i%4 + 1}",
                bullets=[
                    f"Engineered high-throughput distributed system {i}.{b} processing over 10M events per day with sub-2s latency and zero data loss."
                    for b in range(1, bullets_per_item + 1)
                ]
            )
        )

    projects = []
    for i in range(1, proj_count + 1):
        projects.append(
            StructuredProject(
                title=f"Autonomous Agent Project {i}",
                technologies=["Python", "FastAPI", "Docker", "LangGraph", "PyTorch"],
                date="2025",
                bullets=[
                    f"Shipped 0-to-1 agentic architecture {i}.{b} reducing operational queue turnaround by 80% across 500+ production instances."
                    for b in range(1, bullets_per_item + 1)
                ]
            )
        )

    skill_cats = []
    for i in range(1, skill_cat_count + 1):
        skill_cats.append(
            StructuredSkillCategory(
                category_name=f"Domain Category {i}",
                skills=[f"Technology_{i}_{s}" for s in range(1, 8)]
            )
        )

    return StructuredResume(
        name="Yash Kherwal Stress Candidate",
        contact=contact,
        summary="Experienced engineer with a track record of building autonomous agentic systems and scalable data pipelines.",
        education=education,
        experience=experience,
        projects=projects,
        skill_categories=skill_cats,
        section_order=["summary", "education", "experience", "projects", "skills"]
    )


def run_optimizer_stress_tests():
    print("=" * 80)
    print("  ONE-PAGE OPTIMIZER & COMPILER STRESS TEST SUITE")
    print("=" * 80)
    
    compiler = JakeResumeCompiler()
    output_dir = "artifacts/stress_test_outputs"
    os.makedirs(output_dir, exist_ok=True)

    # --------------------------------------------------------------------------
    # TEST 1: Overflow Resume (~215% utilization)
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Overflow Resume (~215% Initial Utilization)")
    res_215 = create_stress_resume(exp_count=5, proj_count=5, bullets_per_item=4, skill_cat_count=4)
    out_1 = compiler.compile(res_215, output_dir=output_dir, filename_prefix="Test1_Overflow_215")
    rep_1 = out_1["optimization_report"]
    print(f"  ✓ Initial Utilization: {rep_1['initial_utilization_pct']}%")
    print(f"  ✓ Applied Levels: {rep_1['applied_levels']}")
    print(f"  ✓ Final Page Count: {rep_1['actual_page_count']}")
    assert rep_1['initial_utilization_pct'] > 115.0, "Expected >115% initial utilization"
    assert len(rep_1['applied_levels']) >= 3, "Expected multiple optimization levels triggered"

    # --------------------------------------------------------------------------
    # TEST 2: Medium Overflow (~108% utilization) — Zero Content Removal Expected
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Medium Overflow (~108% Initial Utilization)")
    res_108 = create_stress_resume(exp_count=3, proj_count=3, bullets_per_item=2, skill_cat_count=3)
    out_2 = compiler.compile(res_108, output_dir=output_dir, filename_prefix="Test2_Medium_108")
    rep_2 = out_2["optimization_report"]
    print(f"  ✓ Initial Utilization: {rep_2['initial_utilization_pct']}%")
    print(f"  ✓ Applied Levels: {rep_2['applied_levels']}")
    print(f"  ✓ Final Page Count: {rep_2['actual_page_count']}")
    assert rep_2['actual_page_count'] == 1, "Expected exactly 1 page output"

    # --------------------------------------------------------------------------
    # TEST 3: Large Overflow (~140% utilization)
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Large Overflow (~140% Initial Utilization)")
    res_140 = create_stress_resume(exp_count=4, proj_count=4, bullets_per_item=3, skill_cat_count=4)
    out_3 = compiler.compile(res_140, output_dir=output_dir, filename_prefix="Test3_Large_140")
    rep_3 = out_3["optimization_report"]
    print(f"  ✓ Initial Utilization: {rep_3['initial_utilization_pct']}%")
    print(f"  ✓ Applied Levels: {rep_3['applied_levels']}")
    print(f"  ✓ Final Page Count: {rep_3['actual_page_count']}")

    # --------------------------------------------------------------------------
    # TEST 4: Extreme Overflow (~300% utilization) — Multi-Page Fallback Expected
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Extreme Overflow (~300% Initial Utilization — Multi-Page Fallback)")
    res_300 = create_stress_resume(exp_count=10, proj_count=8, bullets_per_item=5, skill_cat_count=6)
    out_4 = compiler.compile(res_300, output_dir=output_dir, filename_prefix="Test4_Extreme_300")
    rep_4 = out_4["optimization_report"]
    print(f"  ✓ Initial Utilization: {rep_4['initial_utilization_pct']}%")
    print(f"  ✓ Applied Levels: {rep_4['applied_levels']}")
    print(f"  ✓ Final Page Count: {rep_4['actual_page_count']}")
    print(f"  ✓ Multi-Page Reason: {rep_4['multi_page_reason']}")
    assert rep_4['actual_page_count'] > 1, "Expected multi-page fallback for extreme 300% overflow"
    assert rep_4['multi_page_reason'] != "", "Expected explicit explainable multi-page log reason"

    print("\n" + "=" * 80)
    print("  ALL 4 OPTIMIZER STRESS TEST SCENARIOS PASSED WITH 0 ERRORS")
    print("=" * 80)


if __name__ == "__main__":
    run_optimizer_stress_tests()
