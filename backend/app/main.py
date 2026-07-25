from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import anomalies, health, maintenance, reminders
from app.config import settings

app = FastAPI(
    title="DataPulse API",
    description="Couche d'aide à la décision — analytics et maintenance prédictive, "
                "site MSC-10. Ne prend aucune décision automatique.",
    version="0.1.0",
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
