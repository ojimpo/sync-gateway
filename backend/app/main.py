import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import health, sources, runs, ingest, records

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="arigato-gateway",
    description="Middleware API for scraped data ingestion (bookmeter, filmarks, ...)",
    version="0.1.0",
)

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sources.router)
app.include_router(runs.router)
app.include_router(ingest.router)
app.include_router(records.router)
