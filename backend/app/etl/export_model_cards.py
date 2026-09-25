"""Export des **model cards** vers le frontend — chiffres puisés dans les artefacts.

La page « Méthode » présente le travail ML : volumes du pipeline, modèles, métriques,
limites. Ces chiffres pourraient être recopiés à la main dans le frontend ; ils y
dériveraient au premier réentraînement, sans que rien ne le signale.

Ce script les lit donc **à la source** — les `metadata.json` livrés avec les
`.joblib`, les seuils de `thresholds.json`, et les volumes réels des couches
bronze / silver / gold — et écrit un JSON que le frontend importe au build. Aucun
modèle n'entre dans le bundle déployé : seulement ses métriques.

Séparation assumée : **les nombres viennent des artefacts, la prose est éditoriale**
et vit ici, dans `NARRATIVE`. Rien dans ce fichier n'invente une métrique, et rien
n'est affiché qui ne soit pas dans un artefact ou dans une base.

    python -m app.etl.export_model_cards        (depuis backend/, PYTHONPATH=.)
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import BACKEND_ROOT, settings

MODELS_DIR = BACKEND_ROOT / "app" / "ml" / "models"
OUTPUT = BACKEND_ROOT.parent / "frontend" / "src" / "data" / "model-cards.json"

# Prose éditoriale : ce que fait le modèle, pourquoi celui-là, ce qu'il ne fait pas.
# Les justifications détaillées vivent dans `docs/ml-decisions.md` ; on n'en garde
# ici que ce qu'une carte peut porter.
NARRATIVE = {
    "environmental": {
        "label": "Environnement — température / humidité",
        "task": "Détection d'anomalies contextuelles sur la salle",
        "algorithm": "Modèle de Markov caché gaussien",
        "why": "Une anomalie environnementale est contextuelle : 24 °C peut être normal "
               "ou anormal selon le régime de la salle et la dynamique qui précède. Un "
               "modèle à états latents apprend ces régimes et leurs transitions ; un "
               "détecteur sans mémoire ignorerait la séquence, qui porte le signal.",
        "status": "served",
        "status_label": "Branché — alimente la page Anomalies",
        "limits": "Le F1 provient du protocole du notebook, dont les labels sont des "
                  "proxys de seuils : ce n'est pas une validation contre des pannes réelles.",
    },
    "alarm_anomaly": {
        "label": "Alarmes SCADA / onduleurs",
        "task": "Détection d'événements d'alarme atypiques",
        "algorithm": "Isolation Forest",
        "why": "Aucun label, 720 événements seulement et des variables tabulaires "
               "hétérogènes : un régime où l'Isolation Forest est robuste, et où son "
               "unique paramètre fort — le taux de contamination — est une hypothèse "
               "explicite plutôt qu'un seuil implicite.",
        "status": "trained_not_wired",
        "status_label": "Entraîné, pas encore branché au gold",
        "limits": "Aucune anomalie affichée aujourd'hui n'en provient.",
    },
    "health_forecast": {
        "label": "Prévision du score de santé",
        "task": "Variation du score de santé à +6 h",
        "algorithm": "XGBoost sur le delta, sélection des N meilleures variables",
        "why": "Le score se comporte comme un AR(1) : prédire le niveau demande à des "
               "arbres d'extrapoler une tendance, ce qu'ils ne savent pas faire. Sur le "
               "delta, la persistance devient « delta = 0 » et le modèle n'apprend que "
               "l'écart.",
        "status": "served",
        "status_label": "Branché — alimente la page Prévision",
        "limits": "Validé à +6 h uniquement. Au-delà, la trajectoire est un déroulé "
                  "amorti à conditions inchangées — une projection, pas une prédiction.",
    },
}


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric(label: str, value, unit: str = "", note: str = "") -> dict:
    return {"label": label, "value": value, "unit": unit, "note": note}


def _environmental_card(meta: dict) -> dict:
    thresholds = _read(MODELS_DIR / "environmental" / "thresholds.json")["temperature"]
    anomalous = _read(MODELS_DIR / "environmental" / "anomalous_states.json")["anomalous_states"]
    return {
        "metrics": [
            _metric("F1 anomalie (test)", round(meta["test_f1_anomaly"], 3)),
            _metric("États du modèle", meta["n_states"],
                    note=f"dont {len(anomalous)} marqués anormaux"),
            _metric("Variables", len(meta["features"])),
        ],
        "params": {"n_states": meta["n_states"], "prop_cutoff": meta["prop_cutoff"]},
        "thresholds": {
            "mild_upper": thresholds["mild_upper"],
            "extreme_upper": thresholds["extreme_upper"],
            "method": "Tukey (IQR) sur la distribution observée, directionnels",
        },
        "features": meta["features"],
    }


def _alarm_anomaly_card(meta: dict) -> dict:
    params = meta["model_params"]
    return {
        "metrics": [
            _metric("Événements d'entraînement", meta["n_events_trained_on"]),
            _metric("Arbres", params["n_estimators"]),
            _metric("Contamination", params["contamination"], unit="",
                    note="hypothèse explicite sur le taux d'anomalies"),
            _metric("Variables", len(meta["features"])),
        ],
        "params": params,
        "features": meta["features"],
    }


def _health_forecast_card(meta: dict) -> dict:
    metrics = meta["metrics"]
    selected, persistence = metrics["selected"], metrics["persistence"]
    return {
        "metrics": [
            _metric("MAE test — modèle servi", round(selected["MAE"], 3),
                    note=selected["model"]),
            _metric("MAE test — persistance", round(persistence["MAE"], 3),
                    note="référence à battre : « le score reste où il est »"),
            _metric("Gain vs persistance", round(metrics["mae_improvement_vs_persistence"], 3),
                    note="le notebook obtient +0,97 sur ses propres données — "
                         "notre écart vient du jeu de test, pas de la méthode"),
            _metric("Variables retenues", meta["n_features"],
                    note="sur ~1 200 produites, N choisi sur la validation"),
            _metric("Horizon validé", meta["horizon_hours"], unit="h"),
        ],
        "params": {
            "target": meta["target"],
            "selected_model": meta["selected_model"],
            "residual_std": round(meta["residual_std"], 2),
        },
        "splits": meta["n_rows"],
        "validation_by_feature_count": metrics["validation_by_feature_count"],
        "features": meta["features"],
    }


BUILDERS = {
    "environmental": _environmental_card,
    "alarm_anomaly": _alarm_anomaly_card,
    "health_forecast": _health_forecast_card,
}


def _counts(path: Path, tables: dict[str, str]) -> dict:
    """Compte des lignes, en ignorant les tables absentes de cette base."""
    if not path.exists():
        return {}
    con = sqlite3.connect(path)
    try:
        out = {}
        for key, table in tables.items():
            try:
                out[key] = con.execute(f'select count(*) from "{table}"').fetchone()[0]
            except sqlite3.OperationalError:
                continue
        if "th_clean" in out:
            # Le nombre de segments continus ne se compte pas ligne à ligne : c'est
            # la segmentation du silver (cf. docs/ml-decisions.md §3.3).
            out["segments"] = con.execute(
                "select count(distinct segment_id) from th_clean").fetchone()[0]
        return out
    finally:
        con.close()


def pipeline_volumes() -> dict:
    """Volumes réels des trois couches.

    Bronze et silver ne vivent que dans la base analytique locale ; le gold est
    lisible dans l'export versionné. Une couche absente est omise plutôt
    qu'estimée — la page affichera ce qui existe.
    """
    analytics = _counts(settings.analytics_db_path, {
        "raw_temp_humidity": "raw_temp_humidity", "raw_scada_log": "raw_scada_log",
        "th_clean": "th_clean", "scada_clean": "scada_clean",
    })
    gold_source = settings.analytics_db_path if analytics else \
        settings.analytics_db_path.parent / "datapulse_gold.db"
    gold = _counts(gold_source, {
        "anomaly_episode": "anomaly_episode", "health_score_hourly": "health_score_hourly",
        "forecast_point": "forecast_point",
    })
    volumes = {}
    if analytics:
        volumes["bronze"] = {
            "temp_humidity": analytics.get("raw_temp_humidity"),
            "scada_log": analytics.get("raw_scada_log"),
        }
        volumes["silver"] = {
            "th_clean": analytics.get("th_clean"),
            "segments": analytics.get("segments"),
            "scada_clean": analytics.get("scada_clean"),
        }
    if gold:
        volumes["gold"] = {
            "anomaly_episode": gold.get("anomaly_episode"),
            "health_score_hourly": gold.get("health_score_hourly"),
            "forecast_point": gold.get("forecast_point"),
        }
    return volumes


def build() -> dict:
    cards = []
    for key, builder in BUILDERS.items():
        meta = _read(MODELS_DIR / key / "metadata.json")
        card = {"key": key, "trained_at": meta["trained_at"], **NARRATIVE[key], **builder(meta)}
        cards.append(card)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "metadata.json des artefacts livrés + volumes réels des couches",
        "pipeline": pipeline_volumes(),
        "models": cards,
    }


def export(output: Path | None = None) -> dict:
    output = output or OUTPUT
    payload = build()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return {"output": str(output), "models": [c["key"] for c in payload["models"]],
            "pipeline_layers": sorted(payload["pipeline"])}


if __name__ == "__main__":
    print(export())
