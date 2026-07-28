"""Transform bronze → silver.

Réutilise le préprocessing **validé** (`app/ml`) — jamais réimplémenté :
  - environnemental : `dedupe_and_index` (déduplication par timestamp) puis
    `add_segments` (gaps >125 s = discontinuité, segments continus) ;
  - SCADA : `clean_and_dedupe` (typage des dates, dédup `(log_time, message)`,
    tri, catégorisation) — la fonction même qui a produit le fichier de référence
    `msc10_combined_ups.csv` utilisé par le notebook de scoring.

La fidélité de la sortie est adossée au golden test d'ingestion
(`tests/test_ingestion_fidelity.py`).

    python -m app.etl.transform   (depuis backend/, PYTHONPATH=.)
"""
from sqlalchemy.orm import Session

from app.ml.alarm_anomaly.data_loading import clean_and_dedupe
from app.ml.environmental.preprocessing import add_segments, dedupe_and_index
from app.storage.analytics_db import get_analytics_sessionmaker, init_analytics_db
from app.storage.repositories import bronze_repo, silver_repo


def transform_environmental(session: Session) -> int:
    """bronze `raw_temp_humidity` → silver `th_clean` (dédupliqué + segmenté)."""
    raw = bronze_repo.read_temp_humidity(session)
    clean = dedupe_and_index(raw)   # LEUR déduplication (source de vérité)
    seg = add_segments(clean)       # LEUR segmentation (seuil 125 s)
    return silver_repo.replace_th_clean(session, seg)


def transform_scada(session: Session) -> int:
    """bronze `raw_scada_log` → silver `scada_clean` (dédupliqué + catégorisé)."""
    raw = bronze_repo.read_scada_log(session)
    clean = clean_and_dedupe(raw)   # LEUR nettoyage (identique à l'entraînement)
    return silver_repo.replace_scada_clean(session, clean)


def run_transform() -> dict[str, int]:
    init_analytics_db()
    with get_analytics_sessionmaker()() as session:
        return {
            "th_clean": transform_environmental(session),
            "scada_clean": transform_scada(session),
        }


if __name__ == "__main__":
    print(run_transform())
