from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import anomalies, health, maintenance, reminders
from app.config import settings
from app.db.app_db import get_sessionmaker, init_db
from app.mocks.maintenance import seed_demo_calendar


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    with get_sessionmaker()() as session:
        seed_demo_calendar(session)
    yield


app = FastAPI(
    title="DataPulse API",
    description="Couche d'aide à la décision — analytics et maintenance prédictive, "
                "site MSC-10. Ne prend aucune décision automatique.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(anomalies.router, prefix="/api")
app.include_router(maintenance.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"service": "DataPulse API", "docs": "/docs"}
