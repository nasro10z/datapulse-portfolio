"""Backfill de l'historique : fichiers bruts → couche bronze.

Job **one-shot**, idempotent (remplacement complet). À lancer manuellement — les
données sont volumineuses (≈140k lignes temp/hum), pas au démarrage de l'API.

    python -m app.etl.ingest.backfill   (depuis backend/, PYTHONPATH=.)
"""
from app.etl.ingest import sources
from app.storage.analytics_db import get_analytics_sessionmaker, init_analytics_db
from app.storage.repositories import bronze_repo


def backfill_all(batch_id: str = "backfill") -> dict[str, int]:
    """Charge temp/humidité + SCADA (logs 2026 + UPS) dans le bronze."""
    init_analytics_db()
    with get_analytics_sessionmaker()() as session:
        n_th = bronze_repo.replace_temp_humidity(session, sources.load_temp_humidity(), batch_id)
        n_scada = bronze_repo.replace_scada_log(session, sources.load_scada_raw(), batch_id)
    return {"raw_temp_humidity": n_th, "raw_scada_log": n_scada}


if __name__ == "__main__":
    print(backfill_all())
