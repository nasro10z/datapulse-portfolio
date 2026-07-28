from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import anomalies, health, maintenance, reminders
from app.config import settings
from app.db.app_db import get_sessionmaker, init_db
from app.mocks.maintenance import seed_demo_calendar
from app.storage.analytics_db import init_analytics_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    # Crée les tables de la base analytique (bronze/silver/gold) si absentes.
    # Non-cassant : la base reste vide tant que l'ETL ne l'alimente pas.
    init_analytics_db()
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


@app.exception_handler(NotImplementedError)
async def not_implemented_handler(request: Request, exc: NotImplementedError) -> JSONResponse:
    # DATA_SOURCE=live avant branchement du pipeline → 501 explicite plutôt qu'un 500 opaque
    return JSONResponse(status_code=501, content={"detail": str(exc)})

app.include_router(health.router, prefix="/api")
app.include_router(anomalies.router, prefix="/api")
app.include_router(maintenance.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"service": "DataPulse API", "docs": "/docs"}
