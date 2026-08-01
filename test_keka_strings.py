import re
import json

with open("/Users/yashkherwal/Downloads/hrmailfiles/keka_app.js", "r") as f:
    content = f.read()

# Find all string literals in JS using regex
strings = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', content)
# Flatten the tuples returned by findall
strings = [s[0] or s[1] for s in strings]

api_paths = [s for s in strings if 'api/' in s or 'jobs' in s.lower() or 'careers' in s.lower()]

print("Found API Paths:")
for path in set(api_paths):
    print(path)
