"""RiskSure API entry point. Run locally: uvicorn app.main:app --reload (from backend/)."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (registers the tables)
from app.db import Base, engine
from app.lifecycle import InvalidTransition
from app.routes import router
from app.services import RequestError
from engine.rating import ApplicantError
from engine.rules import RuleError


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)   # simple for a demo; a real system would use migrations
    yield


app = FastAPI(title="RiskSure API", version="0.2.0", lifespan=lifespan,
              description="Config-driven P&C quoting, rating and underwriting (synthetic, illustrative).")

# The frontend lives on a different domain (Vercel), so the browser needs CORS permission.
# ALLOWED_ORIGINS is a comma-separated list; defaults to the local Vite dev server.
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApplicantError)
async def applicant_error(_: Request, e: ApplicantError):
    """Bad form data: list every problem so the UI can highlight each field."""
    return JSONResponse(status_code=422, content={"detail": "Invalid applicant data", "errors": e.errors})


@app.exception_handler(InvalidTransition)
async def invalid_transition(_: Request, e: InvalidTransition):
    """E.g. binding a referred quote: the request conflicts with the quote's state."""
    return JSONResponse(status_code=409, content={"detail": str(e)})


@app.exception_handler(RuleError)
async def rule_error(_: Request, e: RuleError):
    """An invalid rule (from YAML, the assistant or the browser): list every problem."""
    return JSONResponse(status_code=422, content={"detail": "Invalid rule", "errors": e.errors})


@app.exception_handler(RequestError)
async def request_error(_: Request, e: RequestError):
    return JSONResponse(status_code=422, content={"detail": str(e)})


app.include_router(router)


@app.get("/health")
def health():
    """Used by the frontend and by Render to check the service is up."""
    return {"status": "ok", "service": "risksure-api", "version": app.version}
