from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import jobs, companies, applications, contacts, analytics, daemons, settings, activities

app = FastAPI(title="Career Automated API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Applications"])
app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["Contacts"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(daemons.router, prefix="/api/v1/daemons", tags=["Daemons"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(activities.router, prefix="/api/v1/activities", tags=["Activities"])

# Serve the Career Automated Web UI
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
