import glob, os

files = glob.glob("src/discovery/connectors/*.py")
for file in files:
    with open(file, "r") as f:
        content = f.read()
    
    # We want to replace "yield RawJob(" with "yield RawJob(company_id=board.company_id, " 
    # ONLY if it doesn't already have company_id
    lines = content.split('\n')
    changed = False
    for i, line in enumerate(lines):
        if "yield RawJob(" in line and "company_id" not in line:
            lines[i] = line.replace("yield RawJob(", "yield RawJob(company_id=board.company_id, ")
            changed = True
            
    if changed:
        with open(file, "w") as f:
            f.write('\n'.join(lines))
        print(f"Fixed {file}")

