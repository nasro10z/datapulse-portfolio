"""Export d'une base **gold seule**, destinée au déploiement.

La base analytique complète pèse ~39 Mo, dont 97 % de bronze et de silver que
l'API ne lit **jamais** : elle ne sert que le gold précalculé. Cet export en
extrait une copie réduite (~1 Mo), assez légère pour être versionnée et embarquée
dans un déploiement en lecture seule.

Ce n'est pas une base de travail : elle est figée, régénérée après chaque
exécution du pipeline. La source de vérité reste `datapulse_analytics.db`.

L'export fait trois choses que la simple copie ne ferait pas :

1. **il écrit `gold_meta`** — la fin de la couverture capteur et l'étendue
   d'observation, que l'API allait jusqu'ici chercher dans le *silver*. Le silver
   n'étant pas embarqué, sans ce méta la source live des anomalies interrogerait
   une table absente (500 en production) ;
2. **il peut recaler les données dans le temps** (`--shift-to-now`) — voir plus bas ;
3. **il recalcule les statuts d'épisode** contre la borne d'observation retenue.
   Sans recalage c'est un no-op (même borne que `etl/detect`) ; avec recalage,
   c'est ce qui évite d'afficher « résolu » sur un épisode vieux de 30 heures.

⚠️ **Réexporter avant de committer.** Lancer l'API en local en la pointant sur cet
export la repasse en journal WAL (le fichier est inscriptible sur un poste de dev,
donc le pragma s'applique) — et un fichier en WAL est illisible sur le disque en
lecture seule du déploiement. Le garde-fou est
`tests/test_storage.py::test_versioned_gold_export_is_not_in_wal_mode`.

    python -m app.etl.export_gold                 (depuis backend/, PYTHONPATH=.)
    python -m app.etl.export_gold --shift-to-now
"""
import argparse
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings
from app.etl.detect import status_for

# Tables lues par l'API — tout le reste est écarté de l'export.
GOLD_TABLES = {"anomaly_episode", "health_score_hourly", "health_score",
               "forecast_point", "gold_meta"}

# Colonnes temporelles, décalées ensemble : le recalage est une **translation
# unique**, donc tous les écarts entre séries sont conservés à la seconde près.
SHIFT_COLUMNS = {
    "anomaly_episode": ("start", "computed_at"),
    "health_score_hourly": ("timestamp", "computed_at"),
    "health_score": ("computed_at",),
    "forecast_point": ("timestamp",),
}

# Point d'ancrage du recalage : le dernier score horaire, c'est-à-dire la donnée
# la plus fraîche que l'application affiche (Aperçu, Santé du site). L'amener à
# « maintenant » place la prévision à partir de maintenant et les derniers
# épisodes à ~1 jour, au lieu d'une démo figée plusieurs mois en arrière.
ANCHOR_TABLE, ANCHOR_COLUMN = "health_score_hourly", "timestamp"

DEFAULT_OUTPUT = settings.analytics_db_path.parent / "datapulse_gold.db"

_SQLITE_FMT = "%Y-%m-%d %H:%M:%S.%f"


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in (_SQLITE_FMT, "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _silver_bounds(con: sqlite3.Connection) -> tuple[datetime | None, int]:
    """Bornes d'observation, lues dans le silver **avant** qu'il ne soit écarté."""
    try:
        lo, hi = con.execute("select min(ts), max(ts) from th_clean").fetchone()
    except sqlite3.OperationalError:
        return None, 1
    first, last = _parse(lo), _parse(hi)
    span = max((last - first).days, 1) if first and last else 1
    return last, span


def _shift_all(con: sqlite3.Connection, delta: timedelta) -> None:
    """Applique la même translation à toutes les colonnes temporelles du gold."""
    seconds = f"{delta.total_seconds():+.3f} seconds"
    for table, columns in SHIFT_COLUMNS.items():
        for column in columns:
            # strftime plutôt que datetime() : ce dernier tronque les fractions de
            # seconde, que SQLAlchemy relit ensuite comme un format inattendu.
            con.execute(
                f'update "{table}" set "{column}" = '
                f"strftime('%Y-%m-%d %H:%M:%f', \"{column}\", ?) "
                f'where "{column}" is not null',
                (seconds,),
            )


def _refresh_statuses(con: sqlite3.Connection, reference: datetime | None) -> None:
    """Recalcule `status` par ancienneté contre la borne d'observation retenue."""
    if reference is None:
        return
    rows = con.execute("select id, start from anomaly_episode").fetchall()
    for episode_id, start in rows:
        started = _parse(start)
        if started is None:
            continue
        con.execute("update anomaly_episode set status = ? where id = ?",
                    (status_for(started, reference).value, episode_id))


def export_gold(source: Path | None = None, output: Path | None = None,
                shift_to_now: bool = False) -> dict:
    """Copie la base analytique en n'y gardant que le gold, puis compacte.

    Le journal est repassé en mode `DELETE` : une base en WAL a besoin d'écrire ses
    fichiers annexes à l'ouverture, ce qu'un disque en lecture seule interdit —
    elle deviendrait illisible là même où on veut l'embarquer.

    `shift_to_now` translate toutes les dates pour que le dernier score horaire
    tombe à l'heure courante. La fin de couverture capteur, elle, est **bornée à
    l'instant de l'export** : elle suit le dernier score de plus de huit jours et
    se retrouverait sinon dans le futur, ce qui donnerait des fenêtres glissantes
    ouvertes sur des dates qui n'existent pas encore.
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
        silver_last, silver_span = _silver_bounds(con)

        dropped = [t for t in tables if t not in GOLD_TABLES]
        for table in dropped:
            con.execute(f'drop table if exists "{table}"')

        exported_at = datetime.now().replace(microsecond=0)
        delta = timedelta(0)
        if shift_to_now:
            anchor = _parse(
                con.execute(f'select max("{ANCHOR_COLUMN}") from "{ANCHOR_TABLE}"').fetchone()[0]
            )
            if anchor is None:
                raise ValueError(
                    f"Recalage impossible : {ANCHOR_TABLE}.{ANCHOR_COLUMN} est vide "
                    "(le pipeline de scoring n'a pas tourné)."
                )
            delta = exported_at.replace(minute=0, second=0, microsecond=0) - anchor
            _shift_all(con, delta)
            if silver_last is not None:
                silver_last = min(silver_last + delta, exported_at)

        _refresh_statuses(con, silver_last)

        con.execute("""create table if not exists gold_meta (
            id integer primary key, silver_last_ts datetime, silver_span_days integer,
            shift_days float, exported_at datetime)""")
        con.execute("delete from gold_meta")
        con.execute(
            "insert into gold_meta (id, silver_last_ts, silver_span_days, shift_days, exported_at)"
            " values (1, ?, ?, ?, ?)",
            (silver_last.strftime(_SQLITE_FMT) if silver_last else None,
             silver_span, round(delta.total_seconds() / 86400, 3),
             exported_at.strftime(_SQLITE_FMT)),
        )
        con.commit()

        con.execute("pragma journal_mode=DELETE")
        con.execute("vacuum")
        kept = {
            table: con.execute(f'select count(*) from "{table}"').fetchone()[0]
            for table in GOLD_TABLES if table in tables or table == "gold_meta"
        }
        statuses = dict(con.execute(
            "select status, count(*) from anomaly_episode group by status").fetchall())
    finally:
        con.close()

    return {
        "output": str(output),
        "size_mb": round(output.stat().st_size / 1048576, 2),
        "source_size_mb": round(source.stat().st_size / 1048576, 2),
        "tables": kept,
        "dropped": sorted(dropped),
        "shift_days": round(delta.total_seconds() / 86400, 2),
        "observation_end": silver_last.isoformat(sep=" ") if silver_last else None,
        "episode_status": statuses,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--shift-to-now", action="store_true",
        help="recale toutes les dates pour que le dernier score horaire tombe maintenant "
             "(démo : la donnée est historique et figée, le décalage est enregistré dans gold_meta)",
    )
    args = parser.parse_args()
    print(export_gold(shift_to_now=args.shift_to_now))
