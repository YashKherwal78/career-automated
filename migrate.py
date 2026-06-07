import pandas as pd
from database import init_db, add_or_update_lead

init_db()

try:
    df = pd.read_excel("leads.xlsx")
    for _, row in df.iterrows():
        company = str(row.get('company_name', '')).strip()
        email = str(row.get('hr_email', '')).strip()
        if company and email:
            add_or_update_lead(company, {'hr_email': email, 'status': 'New'})
    print(f"Migrated {len(df)} leads.")
except Exception as e:
    print(f"Error migrating: {e}")
