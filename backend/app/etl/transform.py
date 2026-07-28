"""Transform bronze → silver.

Réutilise le préprocessing **validé** (`app/ml`) — jamais réimplémenté :
`dedupe_and_index` (déduplication par timestamp) puis `add_segments` (gaps >125s =
discontinuité, segments continus). La fidélité de la sortie est adossée au golden
test d'ingestion (`tests/test_ingestion_fidelity.py`).

    python -m app.etl.transform   (depuis backend/, PYTHONPATH=.)
"""
from app.ml.environmental.preprocessing import add_segments, dedupe_and_index
from app.storage.analytics_db import get_analytics_sessionmaker, init_analytics_db
from app.storage.repositories import bronze_repo, silver_repo
from sqlalchemy.orm import Session


def transform_environmental(session: Session) -> int:
    """bronze `raw_temp_humidity` → silver `th_clean` (dédupliqué + segmenté)."""
    raw = bronze_repo.read_temp_humidity(session)
    clean = dedupe_and_index(raw)   # LEUR déduplication (source de vérité)
    seg = add_segments(clean)       # LEUR segmentation (seuil 125 s)
    return silver_repo.replace_th_clean(session, seg)


def run_transform() -> dict[str, int]:
    init_analytics_db()
    with get_analytics_sessionmaker()() as session:
        n = transform_environmental(session)
    return {"th_clean": n}


if __name__ == "__main__":
    print(run_transform())
