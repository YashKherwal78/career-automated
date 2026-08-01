# Junie AI

AI-powered job outreach automation. Scrape job postings, discover recruiter contacts, generate personalized emails, and send them — all from one unified pipeline.

## Architecture

- **Frontend**: React + Vite + Tailwind CSS (Neo-Geo design system)
- **Backend**: FastAPI + Groq LLM + Gmail API
- **Auth**: Google OAuth 2.0 with Gmail send scope

## Setup

### 1. Install dependencies

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Configure environment

**Backend** — create `backend/.env`:
```bash
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# Groq API keys — supports round-robin rotation on rate limits
# Use numbered keys for cascading fallback (GROQ_API_1, GROQ_API_2, ...)
# or a single GROQ_API_KEY as fallback
GROQ_API_1=your_first_groq_key
GROQ_API_2=your_second_groq_key
GROQ_API_3=your_third_groq_key
# GROQ_API_KEY=single_key_fallback

HUNTER_API_KEY=your_hunter_key
GETPROSPECT_API_KEY=your_getprospect_key
```

**Frontend** — create `frontend/.env`:
```bash
VITE_GOOGLE_CLIENT_ID=your_client_id
```

### 3. Run

```bash
bash start.sh
```

Or manually:
```bash
# Terminal 1 — Backend
cd backend && source .venv/bin/activate && uvicorn main:app --port 8002 --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

## Project Structure

```
├── backend/
│   ├── main.py                # FastAPI app + OAuth endpoints
│   ├── requirements.txt
│   └── utils/
│       ├── scraper.py         # Job URL parser + company research
│       ├── email_finder.py    # Cascading email lookup (JD → Hunter → GetProspect)
│       ├── email_sender.py    # SMTP + Gmail API send
│       ├── llm.py             # Groq LLM email generation
│       └── pdf_reader.py      # PDF text extraction
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # React Router (/, /dashboard, /auth/callback)
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx
│   │   │   └── Dashboard.tsx
│   │   └── lib/
│   │       └── auth.ts        # Google OAuth helpers
│   ├── tailwind.config.js     # Neo-Geo design tokens
│   └── index.html
└── start.sh                   # Start both servers
```

## Routes

| URL | Page |
|-----|------|
| `/` | Landing page (login) |
| `/dashboard` | Pipeline dashboard (protected) |
| `/auth/callback` | OAuth callback handler |
