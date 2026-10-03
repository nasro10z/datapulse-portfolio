"""Import a gold-only SQLite snapshot into the configured PostgreSQL database."""
import argparse
from pathlib import Path

from sqlalchemy import URL, create_engine, delete, func, inspect, select

from app.config import BACKEND_ROOT
from app.storage import analytics_db
from app.storage.schema.gold import (
    AnomalyEpisodeRow,
    ForecastPointRow,
    GoldMetaRow,
    HealthScoreHourlyRow,
    HealthScoreRow,
)

GOLD_TABLES = [
    AnomalyEpisodeRow.__table__,
    ForecastPointRow.__table__,
    GoldMetaRow.__table__,
    HealthScoreHourlyRow.__table__,
    HealthScoreRow.__table__,
]
DEFAULT_SOURCE = BACKEND_ROOT / "data" / "datapulse_gold.db"


def import_gold_snapshot(
    source_path: Path = DEFAULT_SOURCE,
    *,
    replace_existing: bool = False,
) -> dict[str, int]:
    """Copy the five API-serving tables, preserving unrelated PostgreSQL data."""
    if not analytics_db.is_analytics_postgres():
        raise RuntimeError("Set ANALYTICS_DB_URL to a PostgreSQL URL before importing")
    if not source_path.is_file():
        raise FileNotFoundError(f"Gold snapshot not found: {source_path}")

    source_engine = create_engine(URL.create("sqlite", database=str(source_path)))
    try:
        with source_engine.connect() as source:
            source_tables = set(inspect(source).get_table_names())
            missing = [table.name for table in GOLD_TABLES if table.name not in source_tables]
            if missing:
                raise ValueError(f"Gold snapshot is missing tables: {', '.join(missing)}")
            rows_by_table = {
                table.name: source.execute(select(table)).mappings().all()
                for table in GOLD_TABLES
            }
    finally:
        source_engine.dispose()

    analytics_db.init_analytics_db()
    target_engine = analytics_db.get_analytics_engine()
    try:
        with target_engine.begin() as target:
            populated = {
                table.name: target.scalar(select(func.count()).select_from(table))
                for table in GOLD_TABLES
            }
            populated = {name: count for name, count in populated.items() if count}
            if populated and not replace_existing:
                names = ", ".join(sorted(populated))
                raise RuntimeError(
                    f"Target gold tables already contain data ({names}); "
                    "rerun with --replace-existing to replace them"
                )

            for table in reversed(GOLD_TABLES):
                target.execute(delete(table))
            for table in GOLD_TABLES:
                rows = rows_by_table[table.name]
                if rows:
                    target.execute(table.insert(), rows)
    finally:
        target_engine.dispose()

    return {name: len(rows) for name, rows in rows_by_table.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="replace rows in the five gold tables; leaves other PostgreSQL tables untouched",
    )
    args = parser.parse_args()
    try:
        counts = import_gold_snapshot(args.source, replace_existing=args.replace_existing)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    for table, count in counts.items():
        print(f"{table}: {count} rows imported")


if __name__ == "__main__":
    main()