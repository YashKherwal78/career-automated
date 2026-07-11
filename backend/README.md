# Backend

The Python service is self-contained in this directory. Run all backend commands
from here so the existing `src/`, `config/`, `data/`, and `benchmark/` relative
paths continue to resolve unchanged.

```bash
cd backend
python3 run_pipeline.py
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Build the backend image from the repository root:

```bash
docker build -t career-automated-backend ./backend
docker run --rm -p 8000:8000 -v "$(pwd)/backend/data:/app/data" career-automated-backend
```

`data/` is deliberately excluded from the image. Mount it as a volume in
deployment so the SQLite database, resumes, reports, and runtime state persist.
The React application is deployed separately from `../frontend`.
