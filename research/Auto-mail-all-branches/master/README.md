# ✉️ Auto-Email — Job Application Reply Assistant

A Streamlit app that takes a recruiter's email, your resume, and a job description, uses **GPT-4o** to generate a tailored reply, lets you edit it, and sends it directly via Gmail SMTP.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure secrets
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `GMAIL_USER` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail [App Password](https://myaccount.google.com/apppasswords) (requires 2FA) |

> **Gmail App Password** — Go to Google Account → Security → 2-Step Verification → App Passwords. Generate one for "Mail".

### 3. Run the app
```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Usage

1. **Paste** the recruiter's email in the left panel
2. **Paste or upload** your resume (PDF or plain text)
3. **Paste** the job description
4. Click **Generate Reply** → AI crafts a tailored email
5. **Edit** the draft if needed
6. Confirm the **To** address and **Subject**, then click **Send Email**

## Project Structure
```
Auto-email/
├── app.py                 # Streamlit app (single entrypoint)
├── utils/
│   ├── llm.py             # OpenAI GPT-4o integration
│   ├── email_sender.py    # Gmail SMTP sending
│   ├── email_parser.py    # Extract email address from text
│   └── pdf_reader.py      # PDF → plain text (PyMuPDF)
├── requirements.txt
├── .env.example
└── README.md
```
