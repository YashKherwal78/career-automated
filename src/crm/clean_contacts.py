import pandas as pd
import re
import os
import sys

sys.path.append(os.getcwd())

from src.crm.database import get_all_contacted_emails
from src.config.config import Config

# Simple regex for email validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def clean_contacts(input_file: str):
    print(f"Loading {input_file}...")
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Error loading excel: {e}")
        return

    # Check for Email column
    email_col = next((c for c in df.columns if c.strip().lower() == 'email'), None)
    if not email_col:
        print("Could not find 'Email' column.")
        return

    total_rows_initial = len(df)
    
    # Clean email strings
    df[email_col] = df[email_col].astype(str).str.lower().str.strip()
    
    # 1. Blank removal
    df = df[df[email_col] != 'nan']
    df = df[df[email_col] != '']
    blank_removed = total_rows_initial - len(df)
    
    # 2. Duplicate internal
    len_before_dedup = len(df)
    df = df.drop_duplicates(subset=[email_col])
    internal_dupes_removed = len_before_dedup - len(df)
    
    # 3. Invalid syntax
    len_before_invalid = len(df)
    df = df[df[email_col].apply(lambda x: bool(EMAIL_REGEX.match(x)))]
    invalid_removed = len_before_invalid - len(df)
    
    # 4. Previously Contacted
    contacted_emails = get_all_contacted_emails()
    len_before_contacted = len(df)
    df = df[~df[email_col].isin(contacted_emails)]
    contacted_removed = len_before_contacted - len(df)
    
    final_rows = len(df)
    
    # Export
    output_path = Config.DATA_DIR / "clean_leads.xlsx"
    df.to_excel(output_path, index=False)
    print(f"Exported clean leads to {output_path}")
    
    # Sample rows for report
    sample_rows = df.head(5).to_dict(orient='records')
    
    # Generate Report
    report_content = f"""# Contact Cleaning Report

## Overview
- **Source File**: `{os.path.basename(input_file)}`
- **Output File**: `data/clean_leads.xlsx`

## Metrics
| Metric | Count |
|--------|-------|
| Total Initial Rows | {total_rows_initial} |
| Blank Emails Removed | {blank_removed} |
| Internal Duplicates Removed | {internal_dupes_removed} |
| Malformed Emails Removed | {invalid_removed} |
| **Historically Contacted Removed** | **{contacted_removed}** |
| **Final Clean Outreach Pool** | **{final_rows}** |

## Sample Clean Contacts
```json
{sample_rows}
```

## Capacity Check
At 400 emails per day, this clean dataset provides **{final_rows / 400:.1f} days** of outreach capacity.
"""
    
    report_path = "/Users/yashkherwal/.gemini/antigravity/brain/69382e21-3a98-4212-9cc9-d9130f0f25e8/contact_cleaning_report.md"
    with open(report_path, "w") as f:
        f.write(report_content)
        
    print(f"Generated report at {report_path}")

if __name__ == "__main__":
    clean_contacts("/Users/yashkherwal/Downloads/hrmailfiles/hr_data_wo_name (1).xlsx")
