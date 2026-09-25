"""Model cards : les chiffres affichés viennent bien des artefacts.

La page « Méthode » est une vitrine : si ses métriques dérivaient de ce que
portent réellement les `.joblib`, elle deviendrait une affirmation invérifiable —
exactement ce que le projet s'interdit (cf. CLAUDE.md §7). Ces tests comparent
donc la carte exportée aux `metadata.json`, plutôt que de figer des valeurs
attendues qu'il faudrait mettre à jour à la main.
"""
import json

from app.config import BACKEND_ROOT
from app.etl.export_model_cards import MODELS_DIR, NARRATIVE, build, export


def _meta(key: str) -> dict:
    return json.loads((MODELS_DIR / key / "metadata.json").read_text(encoding="utf-8"))


def _value(card: dict, label: str):
    return next(m["value"] for m in card["metrics"] if m["label"] == label)


def _card(payload: dict, key: str) -> dict:
    return next(c for c in payload["models"] if c["key"] == key)


def test_every_model_has_a_card_with_prose_and_figures():
    payload = build()
    assert {c["key"] for c in payload["models"]} == set(NARRATIVE)
    for card in payload["models"]:
        assert card["label"] and card["why"] and card["limits"]
        assert card["metrics"], card["key"]
        assert all(m["value"] is not None for m in card["metrics"])


def test_figures_match_the_delivered_artefacts():
    payload = build()

    env, forecast = _card(payload, "environmental"), _card(payload, "health_forecast")
    alarm = _card(payload, "alarm_anomaly")

    assert _value(env, "F1 anomalie (test)") == round(_meta("environmental")["test_f1_anomaly"], 3)
    assert _value(env, "États du modèle") == _meta("environmental")["n_states"]

    params = _meta("alarm_anomaly")["model_params"]
    assert _value(alarm, "Arbres") == params["n_estimators"]
    assert _value(alarm, "Contamination") == params["contamination"]

    metrics = _meta("health_forecast")["metrics"]
    assert _value(forecast, "MAE test — modèle servi") == round(metrics["selected"]["MAE"], 3)
    assert _value(forecast, "MAE test — persistance") == round(metrics["persistence"]["MAE"], 3)


def test_the_unwired_model_says_so():
    """`alarm_anomaly` est entraîné mais ne produit aucune anomalie affichée : la
    carte doit le dire, sans quoi la vitrine promet une capacité inexistante."""
    card = _card(build(), "alarm_anomaly")
    assert card["status"] == "trained_not_wired"
    assert "pas encore" in card["status_label"].lower()


def test_export_writes_json_the_frontend_can_import(tmp_path):
    output = tmp_path / "model-cards.json"
    result = export(output=output)
    assert result["output"] == str(output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["models"] and payload["generated_at"]


def test_versioned_cards_are_in_sync_with_the_artefacts():
    """Garde-fou : le JSON committé doit refléter les artefacts committés.

    Réparer : `python -m app.etl.export_model_cards`.
    """
    versioned = BACKEND_ROOT.parent / "frontend" / "src" / "data" / "model-cards.json"
    if not versioned.exists():
        return
    published = json.loads(versioned.read_text(encoding="utf-8"))
    for card in build()["models"]:
        assert _card(published, card["key"])["metrics"] == card["metrics"], (
            f"model-cards.json est périmé pour « {card['key']} » — relancer "
            "`python -m app.etl.export_model_cards`."
        )
