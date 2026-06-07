import pandas as pd
import re

# Load the data, skipping the first row since it seems to have (None, None)
# and then row 1 has the actual headers 'Email' and 'Company'
df = pd.read_excel('Gend phad HR data.xlsx', header=1)

print("Original shape:", df.shape)
print("Original columns:", df.columns.tolist())

# Rename columns to what main.py expects: company_name, hr_email
# Let's check what the columns actually are
if 'Email' in df.columns and 'Company' in df.columns:
    df = df.rename(columns={'Email': 'hr_email', 'Company': 'company_name'})

print("Renamed columns:", df.columns.tolist())

# 1. Clean data: Drop rows with missing email or company
df = df.dropna(subset=['hr_email', 'company_name'])
print("Shape after dropping NaNs:", df.shape)

# 2. Clean data: Strip whitespace
df['hr_email'] = df['hr_email'].astype(str).str.strip()
df['company_name'] = df['company_name'].astype(str).str.strip()

# 3. Clean data: Valid email format
email_pattern = re.compile(r'^[\w\.\+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+$')
valid_email_mask = df['hr_email'].apply(lambda x: bool(email_pattern.match(x)))
df = df[valid_email_mask]
print("Shape after removing invalid emails:", df.shape)

# 4. Clean data: Remove duplicates
df = df.drop_duplicates(subset=['hr_email'])
print("Shape after dropping duplicate emails:", df.shape)


# 5. Prioritize based on keywords related to ML, AI, Software, Tech, Data
# Yash's profile: Software Development, ML/AI, Data Engineering
tech_keywords = [
    'tech', 'software', 'ai', 'data', 'cloud', 'labs', 'systems',
    'solutions', 'analytics', 'networks', 'intelligence', 'info',
    'cyber', 'digital', 'app', 'web', 'machine', 'deep', 'brain', 'innovations'
]
# Use regex to match whole words or parts of words case-insensitively
pattern = '|'.join(tech_keywords)

# Create a boolean column for tech alignment
df['is_tech'] = df['company_name'].str.contains(pattern, case=False, na=False)

# Sort the dataframe so that tech companies are at the top
df = df.sort_values(by=['is_tech', 'company_name'], ascending=[False, True])

tech_count = df['is_tech'].sum()
print(f"Found {tech_count} high-priority tech companies.")

# Drop the helper column if we want, or keep it. Let's drop it to match expected schema.
df_final = df[['company_name', 'hr_email']]

# Check if there are any companies already processed in logs.csv
try:
    logs = pd.read_csv('logs.csv')
    processed_emails = logs['hr_email'].tolist()
    # Filter out already contacted emails
    initial_len = len(df_final)
    df_final = df_final[~df_final['hr_email'].isin(processed_emails)]
    print(f"Removed {initial_len - len(df_final)} already contacted emails.")
except Exception as e:
    print("Could not read logs.csv or process it:", e)

print("Final shape to save:", df_final.shape)

# Save to leads.xlsx
df_final.to_excel('leads_cleaned.xlsx', index=False)
print("Saved to leads_cleaned.xlsx")
