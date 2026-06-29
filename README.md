# agent-platform

An AI receptionist/booking agent platform. Separate project from the companion
app — its own repo, its own database, its own deploys.

**Live:** https://agent-platform-mivq.onrender.com
(`/health` · `/docs` · `/businesses` · `POST /chat`) — backend on Render,
database on Supabase Postgres. Render auto-redeploys on every push to `main`.

## Backend — run it (Part 1: the server breathes)

From `backend/`:

```powershell
# 1. Create an isolated Python sandbox for this project's libraries
python -m venv .venv

# 2. Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1
#    (Git Bash instead:  source .venv/Scripts/activate)

# 3. Install the dependencies
pip install -r requirements.txt

# 4. Run the server (auto-reloads when you edit a file)
uvicorn app.main:app --reload
```

Then open:
- http://localhost:8000/health  → `{"status":"ok", ...}`
- http://localhost:8000/docs    → auto-generated interactive API page

## Layout
```
backend/
  app/
    config.py   settings read from environment / .env
    main.py     the FastAPI app + routes
  requirements.txt
```
