"""Export d'une base **gold seule**, destinée au déploiement.

La base analytique complète pèse ~39 Mo, dont 97 % de bronze et de silver que
l'API ne lit **jamais** : elle ne sert que le gold précalculé. Cet export en
extrait une copie réduite (~1 Mo), assez légère pour être versionnée et embarquée
dans un déploiement en lecture seule.

Ce n'est pas une base de travail : elle est figée, régénérée après chaque
exécution du pipeline. La source de vérité reste `datapulse_analytics.db`.

⚠️ **Réexporter avant de committer.** Lancer l'API en local en la pointant sur cet
export la repasse en journal WAL (le fichier est inscriptible sur un poste de dev,
donc le pragma s'applique) — et un fichier en WAL est illisible sur le disque en
lecture seule du déploiement. Le garde-fou est
`tests/test_storage.py::test_versioned_gold_export_is_not_in_wal_mode`.

    python -m app.etl.export_gold   (depuis backend/, PYTHONPATH=.)
"""
import shutil
import sqlite3
from pathlib import Path

from app.config import settings

# Tables lues par l'API — tout le reste est écarté de l'export.
GOLD_TABLES = {"anomaly_episode", "health_score_hourly", "health_score", "forecast_point"}

DEFAULT_OUTPUT = settings.analytics_db_path.parent / "datapulse_gold.db"


def export_gold(source: Path | None = None, output: Path | None = None) -> dict:
    """Copie la base analytique en n'y gardant que le gold, puis compacte.

    Le journal est repassé en mode `DELETE` : une base en WAL a besoin d'écrire ses
    fichiers annexes à l'ouverture, ce qu'un disque en lecture seule interdit —
    elle deviendrait illisible là même où on veut l'embarquer.
    """
    source = source or settings.analytics_db_path
    output = output or DEFAULT_OUTPUT
    if not source.exists():
        raise FileNotFoundError(
            f"Base analytique absente ({source}). Lancer `python -m app.etl.run --train` d'abord."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    shutil.copy(source, output)

    con = sqlite3.connect(output)
    try:
        tables = [t for (t,) in con.execute("select name from sqlite_master where type='table'")]
        dropped = [t for t in tables if t not in GOLD_TABLES]
        for table in dropped:
            con.execute(f'drop table if exists "{table}"')
        con.commit()
        con.execute("pragma journal_mode=DELETE")
        con.execute("vacuum")
        kept = {
            table: con.execute(f'select count(*) from "{table}"').fetchone()[0]
            for table in tables if table in GOLD_TABLES
        }
    finally:
        con.close()

    return {
        "output": str(output),
        "size_mb": round(output.stat().st_size / 1048576, 2),
        "source_size_mb": round(source.stat().st_size / 1048576, 2),
        "tables": kept,
        "dropped": sorted(dropped),
    }


if __name__ == "__main__":
    print(export_gold())
