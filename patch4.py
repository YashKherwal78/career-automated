import re

with open('src/discovery/tests/contract/test_adapter_contract.py', 'r') as f:
    content = f.read()

new_req = '        required_fields = {"title", "location", "url", "employment_type", "provider_job_id", "updated_at", "provider"}'
content = re.sub(r'        required_fields = \{"title", "location", "url"\} .*', new_req, content)

with open('src/discovery/tests/contract/test_adapter_contract.py', 'w') as f:
    f.write(content)
