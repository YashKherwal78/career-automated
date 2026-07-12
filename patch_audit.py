with open("scratch/audit_discovery.py", "r") as f:
    content = f.read()

content = content.replace("adapter = registry.detect_provider(url)", "adapter = SourceRegistry.find_adapter_for_url(url)")
content = content.replace("registry = SourceRegistry()", "") # It's all classmethods

with open("scratch/audit_discovery.py", "w") as f:
    f.write(content)
