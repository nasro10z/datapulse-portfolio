"""Tests « golden » de fidélité de l'ingestion.

Preuve automatisée que l'ingestion des données brutes, suivie du préprocessing
validé (`app/ml`), reproduit les fichiers de référence livrés par l'équipe data
science. C'est le garde-fou contre le *train/serve skew* : toute dérive future
(erreur d'ingestion, montée de version d'une lib) fait échouer ces tests.

Les données sources et de référence sont fournies manuellement dans
`app/ml/data/raw/` (gitignoré) → les tests sont **skippés** si elles sont absentes
(ex. en CI sans les données), jamais faux-positifs.
"""
import pandas as pd
import pytest

from app.etl.ingest.sources import (
    DATA_RAW,
    load_scada_combined,
    load_temp_humidity,
)
from app.ml.environmental.preprocessing import dedupe_and_index

REF = DATA_RAW / "reference"
TH_RAW = DATA_RAW / "temp_humid_msc10.csv"
TH_REF = REF / "temp_humid_last.csv"
SCADA_REF = REF / "msc10_combined_ups.csv"

_have_env = TH_RAW.exists() and TH_REF.exists()
_have_scada = SCADA_REF.exists() and (DATA_RAW / "logs_msc10.xlsx").exists()


@pytest.mark.skipif(not _have_env, reason="données environnementales brutes/référence absentes")
def test_temp_humidity_reproduces_reference():
    """Ingestion temp/hum + LEUR dédup ≈ `temp_humid_last.csv` (≥ 99.5 %).

    Le résidu (~0.1–0.3 %) provient du millésime de l'export brut (timestamps en
    plus, résolution des doublons), pas de la logique de transformation — celle-ci
    est identique puisque `dedupe_and_index` est LEUR fonction.
    """
    ours = dedupe_and_index(load_temp_humidity())
    ref = pd.read_csv(TH_REF)
    ref["ts"] = pd.to_datetime(ref["ts"], errors="coerce")
    ref = dedupe_and_index(ref.dropna(subset=["ts"]))

    common = ours.index.intersection(ref.index)
    assert len(common) > 100_000, f"trop peu de timestamps communs : {len(common)}"

    eq_t = (ours.loc[common, "temperature"].round(3) == ref.loc[common, "temperature"].round(3)).mean()
    eq_h = (ours.loc[common, "humidity"].round(3) == ref.loc[common, "humidity"].round(3)).mean()
    assert eq_t >= 0.995, f"température seulement {eq_t:.4%} identique"
    assert eq_h >= 0.995, f"humidité seulement {eq_h:.4%} identique"


@pytest.mark.skipif(not _have_scada, reason="données SCADA brutes/référence absentes")
def test_scada_combined_reproduces_reference():
    """Ingestion SCADA (logs 2026 + UPS) + LEUR `clean_and_dedupe` == `msc10_combined_ups.csv`.

    Reproduction **exacte** attendue : même nombre de lignes, mêmes paires
    (log_time, message), catégories identiques.
    """
    ours = load_scada_combined()
    ref = pd.read_csv(SCADA_REF)
    ours["log_time"] = pd.to_datetime(ours["log_time"], errors="coerce")
    ref["log_time"] = pd.to_datetime(ref["log_time"], errors="coerce")

    assert len(ours) == len(ref), f"nombre de lignes : nous={len(ours)} ref={len(ref)}"

    pairs_ours = set(zip(ours["log_time"], ours["message"]))
    pairs_ref = set(zip(ref["log_time"], ref["message"]))
    assert pairs_ours == pairs_ref, (
        f"en trop={len(pairs_ours - pairs_ref)} manquantes={len(pairs_ref - pairs_ours)}"
    )

    # catégorie reproduite à 100 % (colonnes suffixées par le merge)
    m = ours.merge(ref[["log_time", "message", "category"]], on=["log_time", "message"],
                   suffixes=("_ours", "_ref"))
    assert (m["category_ours"] == m["category_ref"]).mean() == 1.0, "catégories divergentes"
