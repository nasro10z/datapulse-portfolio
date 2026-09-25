"""
Chargement et fusion des différentes sources d'alarmes.
Reprend les cellules 1-21 du notebook, transformées en fonctions pures :
chaque fonction prend un/des DataFrame(s) en entrée et retourne un DataFrame,
sans jamais lire ou écrire de fichier "en cachette" au milieu du traitement.
"""
import pandas as pd
import numpy as np

from app.ml.alarm_anomaly.config import CATEGORY_KEYWORDS


def categorize(message: str) -> str:
    """Catégorise une alarme selon des mots-clés dans son message."""
    msg = str(message).upper() if pd.notna(message) else ""
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in msg for k in keywords):
            return category
    return "OTHER"


def load_scada_logs(csv_path, excel_path) -> pd.DataFrame:
    """Charge et fusionne les logs CSV + Excel SCADA (cellules 1-3)."""
    logs = pd.read_csv(csv_path)

    df_logs = pd.read_excel(excel_path)
    df_msc10 = df_logs[df_logs["message"].str.contains("MSC 10", case=False, na=False)]
    df_msc10 = df_msc10.reset_index(drop=True)

    df_msc10_renamed = df_msc10.rename(columns={
        "time": "log_time",
        "send Time": "send_time",
    })[["state", "log_time", "message", "send_time"]]

    df_csv_aligned = logs[["state", "log_time", "message", "send_time"]]
    df_combined = pd.concat([df_csv_aligned, df_msc10_renamed], ignore_index=True)

    return df_combined


def merge_ups_source(df_combined: pd.DataFrame, ups_csv_path) -> pd.DataFrame:
    """Ajoute la source UPS additionnelle (cellules 19-20)."""
    df_ups_new = pd.read_csv(ups_csv_path)

    description = df_ups_new["description"].fillna("").astype(str)
    df_ups_new["state"] = np.where(
        description.str.contains("restored", case=False, na=False), "D", "A"
    )
    # Préfixe neutralisé : le nom réel du site vit avec les données brutes
    # (hors dépôt). Notre ingestion utilise `config.Settings.raw_ups_message_prefix`,
    # surchargeable par RAW_UPS_MESSAGE_PREFIX ; cette fonction livrée n'est pas
    # appelée par le pipeline DataPulse (cf. etl/ingest/sources.load_ups_events).
    df_ups_new["message"] = (
        r"\MSC-10\ UPS "
        + description.str.replace(" has been restored", "", case=False, regex=False).str.upper()
    )
    df_ups_new["log_time"] = pd.to_datetime(df_ups_new["ts"], errors="coerce")
    df_ups_new["send_time"] = df_ups_new["log_time"]

    df_ups_new_aligned = (
        df_ups_new[["state", "log_time", "message", "send_time"]]
        .dropna(subset=["log_time"])
    )

    if "log_time" not in df_combined.columns:
        df_combined = df_combined.reset_index()

    df_combined = pd.concat([df_combined, df_ups_new_aligned], ignore_index=True, sort=False)
    return df_combined


def clean_and_dedupe(df_combined: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage final : typage des dates, dédoublonnage, tri, catégorisation."""
    df_combined["log_time"] = pd.to_datetime(df_combined["log_time"], errors="coerce")
    df_combined["send_time"] = pd.to_datetime(df_combined["send_time"], errors="coerce")
    df_combined = df_combined.dropna(subset=["log_time", "message"])

    df_combined = (
        df_combined
        .drop_duplicates(subset=["log_time", "message"])
        .sort_values("log_time")
        .reset_index(drop=True)
    )

    df_combined["category"] = df_combined["message"].apply(categorize)
    return df_combined


def load_full_dataset(csv_path, excel_path, ups_csv_path) -> pd.DataFrame:
    """Pipeline complet de chargement, équivalent aux cellules 1-21 du notebook."""
    df = load_scada_logs(csv_path, excel_path)
    df = merge_ups_source(df, ups_csv_path)
    df = clean_and_dedupe(df)
    return df
