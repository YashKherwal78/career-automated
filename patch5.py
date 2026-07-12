with open('src/discovery/tests/contract/test_adapter_contract.py', 'r') as f:
    content = f.read()

imports = """import src.discovery.workers.workday_adapter
import src.discovery.workers.smartrecruiters_adapter
import src.discovery.workers.greenhouse_adapter
import src.discovery.workers.lever_adapter
import src.discovery.workers.ashby_adapter"""

content = content.replace("import src.discovery.workers.workday_adapter\nimport src.discovery.workers.smartrecruiters_adapter", imports)

with open('src/discovery/tests/contract/test_adapter_contract.py', 'w') as f:
    f.write(content)
print("Patched imports")
