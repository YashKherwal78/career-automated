with open("validate_phase1.py", "r") as f:
    text = f.read()

text = text.replace(
    'success &= await test_provider("Ubisoft", "smartrecruiters", "ubisoft", "https://jobs.smartrecruiters.com/ubisoft")',
    'success &= await test_provider("Visa", "smartrecruiters", "Visa", "https://jobs.smartrecruiters.com/Visa")'
)

with open("validate_phase1.py", "w") as f:
    f.write(text)
