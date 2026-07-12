with open("src/discovery/pipeline/sync_session.py", "r") as f:
    text = f.read()
text = text.replace("self.stats[\"error_message\"] = str(e)", "self.stats[\"error_message\"] = str(e)\\n            import traceback\\n            traceback.print_exc()")
with open("src/discovery/pipeline/sync_session.py", "w") as f:
    f.write(text)
