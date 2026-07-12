with open('src/discovery/run_cluster.py', 'r') as f:
    content = f.read()
    
content = content.replace("               OR ats_provider = 'smartrecruiters'\n                endpoints = cursor.fetchall()", "               OR ats_provider = 'smartrecruiters'\n        ''')\n        endpoints = cursor.fetchall()")

with open('src/discovery/run_cluster.py', 'w') as f:
    f.write(content)
