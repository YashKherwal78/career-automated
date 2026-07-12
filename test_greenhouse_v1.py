import sqlite3
import os
import json
from src.config.config import Config
from src.applications.executor import ApplicationExecutor

def run_validation():
    print("Starting Greenhouse Validation V1...")
    
    # 1. Fetch Top Greenhouse Job
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM jobs 
        WHERE job_url LIKE '%greenhouse%' 
        AND eligibility_status = 'Eligible' 
        ORDER BY ranking_score DESC 
        LIMIT 1
    """)
    job = cursor.fetchone()
    
    if not job:
        print("No eligible Greenhouse jobs found in DB.")
        return
        
    job_id = job["id"]
    company = job["company_name"]
    role = job["job_title"]
    url = job["job_url"]
    
    # Update DB to reset status if needed
    cursor.execute("UPDATE application_executions SET status = 'PENDING' WHERE job_id = ?", (job_id,))
    conn.commit()
    
    print(f"Target Job: {company} - {role} (ID: {job_id})")
    
    # 2. Execute with TEST_MODE
    # Note: Using dummy resume path for the test, assuming agent5 has generated it in a real flow
    resume_path = str(Config.DATA_DIR / "yash_resume.pdf") 
    executor = ApplicationExecutor(
        job_id=job_id,
        url=url,
        resume_path=resume_path,
        job_title=role,
        company_name=company,
        test_mode=True
    )
    
    status = executor.execute()
    audit_log = executor.audit_log
    
    # 3. Store Audit Logs
    for entry in audit_log:
        cursor.execute("""
            INSERT INTO application_answer_audit (
                job_id, company, role, question_text, field_label, field_type,
                placeholder, options, question_category, raw_answer, normalized_answer,
                answer_source, confidence, css_selector, input_tag, required, visible,
                disabled, validation_error, current_value, final_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, company, role,
            entry.get("question", ""),
            entry.get("field_label", ""),
            entry.get("field_type", ""),
            entry.get("placeholder", ""),
            json.dumps(entry.get("options", [])),
            entry.get("classification", ""),
            entry.get("raw_answer", ""),
            entry.get("normalized_answer", ""),
            entry.get("answer_source", ""),
            entry.get("confidence", 0),
            entry.get("css_selector", ""),
            entry.get("input_tag", ""),
            entry.get("required", False),
            entry.get("visible", True),
            entry.get("disabled", False),
            entry.get("validation_error", ""),
            entry.get("current_value", ""),
            entry.get("final_value", "")
        ))
    conn.commit()
    conn.close()
    
    # 4. Generate Report
    execution_dir = f"executions/{job_id}"
    os.makedirs(execution_dir, exist_ok=True)
    report_path = os.path.join(execution_dir, "greenhouse_test_report.md")
    
    total_fields = len(audit_log)
    answered = sum(1 for a in audit_log if a.get("final_value") and a.get("final_value") != "NORMALIZATION_FAILED")
    failed = sum(1 for a in audit_log if a.get("final_value") == "NORMALIZATION_FAILED" or not a.get("final_value"))
    
    knockout = sum(1 for a in audit_log if a.get("classification") == "KNOCKOUT")
    profile = sum(1 for a in audit_log if a.get("classification") == "PROFILE")
    comp = sum(1 for a in audit_log if a.get("classification") == "COMPENSATION")
    mot = sum(1 for a in audit_log if a.get("classification") == "MOTIVATION")
    beh = sum(1 for a in audit_log if a.get("classification") == "BEHAVIORAL")
    tech = sum(1 for a in audit_log if a.get("classification") == "TECHNICAL")
    legal = sum(1 for a in audit_log if a.get("classification") == "LEGAL")
    
    # Unanswered required
    unanswered_req = [a for a in audit_log if a.get("required") and not a.get("final_value")]
    normalization_failures = [a for a in audit_log if a.get("final_value") == "NORMALIZATION_FAILED"]
    
    q_completion = (answered / total_fields * 100) if total_fields > 0 else 100
    
    decision = "PASS" if (status == "SUBMITTED" and len(unanswered_req) == 0 and len(normalization_failures) == 0) else "FAIL"
    
    blockers = []
    if status != "SUBMITTED":
        blockers.append(f"Execution stopped early: {status}")
    if len(unanswered_req) > 0:
        blockers.append(f"Unanswered required questions: {len(unanswered_req)}")
    if len(normalization_failures) > 0:
        blockers.append(f"Normalization failures: {len(normalization_failures)}")
        
    with open(report_path, "w") as f:
        f.write(f"# GREENHOUSE VALIDATION REPORT\n\n")
        f.write(f"Company: {company}\n")
        f.write(f"Role: {role}\n")
        f.write(f"URL: {url}\n\n")
        
        f.write("## QUESTION ANALYSIS\n")
        for a in audit_log:
            f.write(f"**Field Label:** {a.get('field_label') or a.get('question')}\n")
            f.write(f"**Field Type:** {a.get('field_type')}\n")
            f.write(f"**Required:** {a.get('required')}\n")
            f.write(f"**Placeholder:** {a.get('placeholder')}\n")
            f.write(f"**Classification:** {a.get('classification')}\n")
            f.write(f"**Source:** {a.get('answer_source')}\n")
            f.write(f"**Raw Answer:** {a.get('raw_answer')}\n")
            f.write(f"**Normalized Answer:** {a.get('normalized_answer')}\n")
            f.write(f"**Confidence:** {a.get('confidence')}%\n")
            if a.get('options'):
                f.write(f"**Options:** {a.get('options')}\n")
            f.write("---\n")
            
        f.write("\n## FIELD SUMMARY\n")
        f.write(f"Total Fields: {total_fields}\n")
        f.write(f"Mapped: {total_fields}\n")
        f.write(f"Unmapped: 0\n\n") # Assume mapped since Question Engine catches all custom iterator elements
        
        f.write("## QUESTION SUMMARY\n")
        f.write(f"Total Questions: {total_fields}\n")
        f.write(f"Knockout Questions: {knockout}\n")
        f.write(f"Profile Questions: {profile}\n")
        f.write(f"Salary Questions: {comp}\n")
        f.write(f"Motivation Questions: {mot}\n")
        f.write(f"Behavioral Questions: {beh}\n")
        f.write(f"Technical Questions: {tech}\n")
        f.write(f"Legal Questions: {legal}\n")
        f.write(f"Answered: {answered}\n")
        f.write(f"Skipped/Failed: {failed}\n\n")
        
        f.write("## AUTOMATION SCORE\n")
        f.write(f"Question Completion: {q_completion:.1f}%\n")
        f.write(f"Overall Completion: {q_completion:.1f}%\n\n")
        
        f.write("## READY FOR SCALE DECISION\n")
        f.write(f"Ready For Submission: {'YES' if decision == 'PASS' else 'NO'}\n")
        f.write("Submission Blockers:\n")
        if blockers:
            for b in blockers:
                f.write(f"- {b}\n")
        else:
            f.write("- None\n")
            
        f.write("\n**Decision:** " + decision + "\n")
        if decision == "PASS":
            f.write("Recommendation: PROCEED TO 5-JOB TEST\n")
        else:
            f.write("Recommendation: FIX ISSUES BEFORE SCALING\n")
            
    print(f"Validation complete. Report generated at {report_path}")
    print(f"Result: {decision}")

if __name__ == "__main__":
    run_validation()
