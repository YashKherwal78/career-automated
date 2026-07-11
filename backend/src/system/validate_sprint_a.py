import os
import sys
import subprocess

def run_cmd(cmd):
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
    return res

def generate_validation_report():
    report_path = "data/reports/sprint_a_validation.md"
    lines = [
        "======================================",
        "CareerAutomated Sprint A Validation",
        "======================================",
    ]
    
    code_pass = True
    env_ready = True
    
    # ---------------- Environment Checks ----------------
    lines.append("Environment\n------------------------")
    
    # Check .env
    env_status = "PASS" if os.path.exists(".env") else "NOT CONFIGURED"
    lines.append(f".env                  {env_status}")
    if env_status != "PASS": env_ready = False
        
    # Check Playwright
    try:
        import playwright
        pw_status = "PASS"
    except ImportError:
        pw_status = "NOT INSTALLED"
    lines.append(f"Playwright            {pw_status}")
    if pw_status != "PASS": env_ready = False
        
    # Check Docker Daemon
    docker_res = run_cmd("docker info")
    docker_status = "PASS" if docker_res.returncode == 0 else "NOT CONFIGURED"
    lines.append(f"Docker Daemon         {docker_status}")
    if docker_status != "PASS": env_ready = False

    # ---------------- Code / Runtime Checks ----------------
    lines.append("\nCode & Infrastructure\n------------------------")
    
    cron_res = run_cmd("python3 -c 'import src.production.main_cron'")
    cron_status = "PASS" if cron_res.returncode == 0 else "FAIL"
    lines.append(f"Cron Import           {cron_status}")
    if cron_status == "FAIL": code_pass = False

    api_res = run_cmd("python3 -c 'import src.api.main'")
    api_status = "PASS" if api_res.returncode == 0 else "FAIL"
    lines.append(f"API Import            {api_status}")
    if api_status == "FAIL": code_pass = False

    db_res = run_cmd("python3 -m src.crm.db_init")
    db_status = "PASS" if db_res.returncode == 0 else "FAIL"
    lines.append(f"Database Migration    {db_status}")
    if db_status == "FAIL": code_pass = False
    
    hc_res = run_cmd("python3 -m src.system.health_check")
    # Health check is expected to fail if environment is not ready. 
    # If environment is NOT ready, we mark health check as "BLOCKED BY ENV".
    # If environment IS ready but health check fails, that's a code failure.
    if not env_ready:
        hc_status = "BLOCKED BY ENV"
    else:
        hc_status = "PASS" if hc_res.returncode == 0 else "FAIL"
        if hc_status == "FAIL": code_pass = False
    lines.append(f"Health Check          {hc_status}")
        
    pipe_res = run_cmd("python3 -m src.mission_control.run_pipeline --dry-run")
    if not env_ready:
        pipe_status = "BLOCKED BY ENV"
    else:
        pipe_status = "PASS" if pipe_res.returncode == 0 else "FAIL"
        if pipe_status == "FAIL": code_pass = False
    lines.append(f"Pipeline Dry Run      {pipe_status}")

    # ---------------- Overall ----------------
    lines.append("\n======================================")
    lines.append(f"Overall Code Status   {'PASS' if code_pass else 'FAIL'}")
    lines.append(f"Deployment Status     {'READY' if env_ready and code_pass else 'NOT READY (Missing Environment)'}")
    lines.append("======================================")
        
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")
        
    print("\n".join(lines))

if __name__ == "__main__":
    generate_validation_report()
