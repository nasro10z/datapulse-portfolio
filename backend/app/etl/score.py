"""Étape F1 — scoring de santé : silver → gold.

Déroule le **scoring validé** (`ml/health_score`, portage du notebook
`health_scores.ipynb`) sur tout le silver et écrit deux choses dans le gold :

  1. `health_score_hourly` — la table horaire complète (équivalent servi du
     `site_health_scores.csv` du notebook) : base de la page Santé du site, de
     l'historique, et jeu d'entraînement de la prévision ;
  2. `health_score` — l'instantané servi par l'aperçu : score global + trois
     sous-scores par **famille d'équipement**.

Correspondance domaine → clé `family` de l'API :

    environnement → stulz      énergie → socomec      batterie → yanan

Attention à ne pas la lire comme une attribution d'équipement : l'interface
n'affiche **jamais** « STULZ » / « SOCOMEC » / « YANAN » pour ces trois cartes,
elle les libelle par domaine (`FAMILY_DOMAIN_LABEL_KEY`, décision de la session
Prévision). `family` n'est donc ici qu'une **clé technique** portant les trois
domaines dans le contrat existant, et l'ordre ci-dessus est celui qu'attend le
frontend — d'où des libellés corrects à l'écran (Environnement / Énergie /
Batterie) sans toucher au frontend.

La granularité reste **la salle** et le **site** : aucun de ces scores ne mesure
l'état d'un STULZ ou d'un onduleur en particulier.

    python -m app.etl.score   (depuis backend/, PYTHONPATH=.)
"""
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.health_score import config as cfg
from app.ml.health_score.scoring import compute_health_scores
from app.mocks.equipment import SOCOMEC_UNITS, STULZ_UNITS, YANAN_UNITS
from app.models.health import EquipmentFamily, HealthStatus, Trend
from app.storage.analytics_db import get_analytics_sessionmaker, init_analytics_db
from app.storage.repositories import gold_repo, silver_repo

# Domaine du scoring → clé `family` du contrat API (cf. docstring du module).
DOMAIN_TO_FAMILY = {
    "environmental": EquipmentFamily.stulz,
    "energy": EquipmentFamily.socomec,
    "battery": EquipmentFamily.yanan,
}

# Libellés et notes décrivant le DOMAINE (ce que mesurent les données), pas une
# famille d'équipement — c'est le domaine que l'interface affiche.
DOMAIN_LABEL = {
    "environmental": "Environnement — température et humidité de salle",
    "energy": "Énergie — alimentation secteur, basculements et groupe",
    "battery": "Batterie — chaînes batterie des onduleurs",
}

DOMAIN_NOTE = {
    "environmental": f"Climatisation : {len(STULZ_UNITS)} STULZ ASD 522 AS — mesure au capteur de salle.",
    "energy": f"Secteur, {len(YANAN_UNITS)} groupes YANAN et basculements — journal SCADA.",
    "battery": f"Alarmes batterie des {len(SOCOMEC_UNITS)} onduleurs SOCOMEC 200 kVA.",
}

# Nombre d'unités concernées par le domaine (informatif).
DOMAIN_UNIT_COUNT = {
    "environmental": len(STULZ_UNITS),
    "energy": len(YANAN_UNITS),
    "battery": len(SOCOMEC_UNITS),
}

# Statut à 3 niveaux de l'API ← statut à 5 niveaux du scoring (bornes 90/75/60/40).
_STATUS_FROM_HEALTH = [(90, HealthStatus.healthy), (60, HealthStatus.watch)]
# Tendance : seuil de 5 points sur 24 h, celui qui sépare « stable » de
# « dégradation » dans le notebook.
_TREND_THRESHOLD = 5.0


def status_for(score: float) -> HealthStatus:
    for minimum, status in _STATUS_FROM_HEALTH:
        if score >= minimum:
            return status
    return HealthStatus.critical


def trend_for(change_24h: float | None) -> Trend:
    if change_24h is None or pd.isna(change_24h):
        return Trend.stable
    if change_24h >= _TREND_THRESHOLD:
        return Trend.up
    if change_24h <= -_TREND_THRESHOLD:
        return Trend.down
    return Trend.stable


def build_snapshot_rows(scores: pd.DataFrame) -> list[dict]:
    """Dernière heure scorée → lignes `health_score` (global + une par famille)."""
    last = scores.iloc[-1]
    # Statut déduit du score **arrondi** : sinon un 89,96 affiché « 90,0 » se
    # verrait attribuer un statut qui contredit la valeur montrée à l'écran.
    global_score = round(float(last["overall_site_health"]), 1)
    rows = [{
        "scope": "global",
        "family": None,
        "label": "Score de santé du site",
        "score": global_score,
        "status": status_for(global_score).value,
        "trend": trend_for(last.get("overall_site_health_trend_24h")).value,
        "unit_count": len(STULZ_UNITS) + len(SOCOMEC_UNITS) + len(YANAN_UNITS),
        "note": last.get("recommended_action"),
    }]
    for domain, family in DOMAIN_TO_FAMILY.items():
        score = round(float(last[f"{domain}_health_score"]), 1)
        rows.append({
            "scope": "family",
            "family": family.value,
            "label": DOMAIN_LABEL[domain],
            "score": score,
            "status": status_for(score).value,
            "trend": trend_for(last.get(f"{domain}_health_score_trend_24h")).value,
            "unit_count": DOMAIN_UNIT_COUNT[domain],
            "note": DOMAIN_NOTE[domain],
        })
    return rows


def score_site_health(session: Session) -> dict[str, int]:
    """silver (`th_clean` + `scada_clean`) → gold (`health_score_hourly`, `health_score`)."""
    env = silver_repo.read_th_clean(session)
    log = silver_repo.read_scada_clean(session)
    if env.empty or log.empty:
        raise ValueError(
            "Silver incomplet : lancer `python -m app.etl.ingest.backfill` puis "
            "`python -m app.etl.transform` avant le scoring."
        )

    scores = compute_health_scores(env[["ts", "temperature", "humidity"]], log)
    run_id = datetime.now(timezone.utc).strftime("score-%Y%m%d%H%M%S")

    return {
        "health_score_hourly": gold_repo.replace_health_hourly(session, scores),
        "health_score": gold_repo.replace_health_scores(session, run_id, build_snapshot_rows(scores)),
    }


def run_score() -> dict:
    init_analytics_db()
    with get_analytics_sessionmaker()() as session:
        result = score_site_health(session)
    return {**result, "weight_version": cfg.WEIGHT_VERSION, "score_version": cfg.SCORE_VERSION}


if __name__ == "__main__":
    print(run_score())
