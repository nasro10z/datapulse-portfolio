"""Orchestration de l'ETL — l'ordre des étapes, en un seul point.

    bronze   ingest.backfill   fichiers bruts → raw_temp_humidity, raw_scada_log
    silver   transform         → th_clean (segmenté), scada_clean (catégorisé)
    gold     detect            → anomaly_episode      (HMM environnemental)
             score             → health_score_hourly, health_score
             forecast          → forecast_point       (24 h / 7 j / 30 j)

Chaque étape est idempotente (remplacement complet de sa cible) : relancer le
pipeline ne duplique rien. C'est ce qui permet de le rejouer sans état à nettoyer.

    python -m app.etl.run                  pipeline complet (modèles existants)
    python -m app.etl.run --train          idem + réentraînement de la prévision
    python -m app.etl.run --skip-ingest    repart du bronze déjà chargé
"""
import sys

from app.etl import detect, forecast, score, transform
from app.etl.ingest import backfill


def run_pipeline(skip_ingest: bool = False, train: bool = False) -> dict:
    result: dict = {}
    if not skip_ingest:
        result["bronze"] = backfill.backfill_all()
    result["silver"] = transform.run_transform()
    result["gold_anomalies"] = detect.run_detect()
    result["gold_scores"] = score.run_score()
    result["gold_forecast"] = forecast.run_forecast(train=train)
    return result


if __name__ == "__main__":
    print(run_pipeline(skip_ingest="--skip-ingest" in sys.argv, train="--train" in sys.argv))
