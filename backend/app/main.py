"""RiskSure API entry point. Run locally: uvicorn app.main:app --reload (from backend/)."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RiskSure API", version="0.1.0")

# The frontend lives on a different domain (Vercel), so the browser needs CORS permission.
# ALLOWED_ORIGINS is a comma-separated list; defaults to the local Vite dev server.
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Used by the frontend and by Render to check the service is up."""
    return {"status": "ok", "service": "risksure-api", "version": app.version}
