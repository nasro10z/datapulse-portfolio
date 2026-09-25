"""Export gold de déploiement : contenu, recalage temporel, lecture sans silver.

Trois propriétés y sont vérifiées, chacune adossée à un incident possible en
production :

- l'export ne garde que le gold **et** écrit `gold_meta` — sans ce méta, la source
  live des anomalies interroge le silver, absent de l'export (500 en production) ;
- le recalage est une **translation unique** : si une série se décalait
  différemment d'une autre, la démo afficherait des relations fausses (une
  prévision qui démarre avant le dernier point d'historique, par exemple) ;
- la fin de couverture est **bornée à l'instant de l'export** : elle suit le
  dernier score de plus de huit jours et se retrouverait sinon dans le futur.
"""
from datetime import datetime, timedelta

import sqlite3

from sqlalchemy import URL, create_engine

from app.etl.export_gold import export_gold
from app.storage.schema import Base

# Repères de la base de test, calqués sur la forme des données réelles : la
# couverture capteur se termine après le dernier score horaire, et le dernier
# épisode précède ce score.
LAST_SCORE = datetime(2026, 5, 10, 10, 0, 0)
LAST_SENSOR = LAST_SCORE + timedelta(days=8, hours=9)
FIRST_SENSOR = LAST_SCORE - timedelta(days=60)


def _source_db(tmp_path):
    """Base analytique miniature : silver + gold, comme après une exécution d'ETL."""
    path = tmp_path / "analytics.db"
    Base.metadata.create_all(create_engine(URL.create(drivername="sqlite", database=str(path))))

    con = sqlite3.connect(path)
    fmt = "%Y-%m-%d %H:%M:%S.%f"
    computed = LAST_SCORE.strftime(fmt)

    for i, ts in enumerate((FIRST_SENSOR, LAST_SENSOR)):
        con.execute(
            "insert into th_clean (ts, temperature, humidity, segment_id, segment_position,"
            " is_discontinuity, sensor, computed_at) values (?, 24.0, 38.0, 0, ?, 0, ?, ?)",
            (ts.strftime(fmt), i, "SITE01_SALLE_SWITCH", computed),
        )

    # Trois épisodes d'âges différents : à la borne, 2 jours avant, 20 jours avant.
    for n, age_days in enumerate((0.1, 2.0, 20.0), start=1):
        start = LAST_SCORE - timedelta(days=age_days)
        con.execute(
            "insert into anomaly_episode (id, equipment, type, severity, direction, start,"
            " duration_min, peak_value, status, computed_at, dimension)"
            " values (?, 'SALLE_SWITCH', 'collective', 'alert', 'high', ?, 12.0, 27.1,"
            " 'resolved', ?, 'environment')",
            (f"EP-{n:04d}", start.strftime(fmt), computed),
        )

    for h in range(3):
        ts = LAST_SCORE - timedelta(hours=h)
        con.execute(
            "insert into health_score_hourly (timestamp, environmental_health_score,"
            " energy_health_score, battery_health_score, overall_site_health,"
            " environmental_risk_score, energy_risk_score, battery_risk_score,"
            " weight_version, score_version, computed_at)"
            " values (?, 80, 70, 60, 70, 20, 30, 40, 'v1.0', 'health_score_v1.0', ?)",
            (ts.strftime(fmt), computed),
        )

    for h in (-1, 6):  # un point d'historique, un point de prévision
        ts = LAST_SCORE + timedelta(hours=h)
        con.execute(
            "insert into forecast_point (run_id, horizon, timestamp, value, lower, upper,"
            " is_forecast) values ('run-1', '24h', ?, 70.0, 60.0, 80.0, ?)",
            (ts.strftime(fmt), 1 if h > 0 else 0),
        )
    con.commit()
    con.close()
    return path


def _timestamps(path, table, column):
    con = sqlite3.connect(path)
    try:
        return [r[0] for r in con.execute(f'select "{column}" from "{table}" order by rowid')]
    finally:
        con.close()


def _meta(path) -> dict:
    con = sqlite3.connect(path)
    try:
        row = con.execute(
            "select silver_last_ts, silver_span_days, shift_days, exported_at from gold_meta"
        ).fetchone()
    finally:
        con.close()
    return dict(zip(("silver_last_ts", "silver_span_days", "shift_days", "exported_at"), row))


def test_export_keeps_only_gold_and_carries_the_observation_bounds(tmp_path):
    source = _source_db(tmp_path)
    result = export_gold(source=source, output=tmp_path / "gold.db")

    assert set(result["tables"]) == {
        "anomaly_episode", "health_score_hourly", "health_score", "forecast_point", "gold_meta",
    }
    assert "th_clean" in result["dropped"]

    # Les bornes viennent du silver, lu avant qu'il ne soit écarté : c'est tout
    # l'objet de `gold_meta`, puisque l'API ne pourra plus les y chercher.
    meta = _meta(tmp_path / "gold.db")
    assert meta["silver_last_ts"].startswith(LAST_SENSOR.strftime("%Y-%m-%d %H:%M"))
    assert meta["silver_span_days"] == (LAST_SENSOR - FIRST_SENSOR).days
    assert meta["shift_days"] == 0.0


def test_shift_translates_every_series_by_the_same_delta(tmp_path):
    source = _source_db(tmp_path)
    plain, shifted = tmp_path / "plain.db", tmp_path / "shifted.db"
    export_gold(source=source, output=plain)
    result = export_gold(source=source, output=shifted, shift_to_now=True)

    assert result["shift_days"] > 0

    parse = lambda s: datetime.strptime(s[:23], "%Y-%m-%d %H:%M:%S.%f")  # noqa: E731
    # Décalage mesuré sur la série d'ancrage, pas reconstruit depuis `shift_days`,
    # qui est arrondi pour l'affichage (±864 s) : c'est l'**uniformité** qu'on teste.
    delta = (parse(_timestamps(shifted, "health_score_hourly", "timestamp")[0])
             - parse(_timestamps(plain, "health_score_hourly", "timestamp")[0]))

    for table, column in (("anomaly_episode", "start"),
                          ("health_score_hourly", "timestamp"),
                          ("forecast_point", "timestamp")):
        before = [parse(v) for v in _timestamps(plain, table, column)]
        after = [parse(v) for v in _timestamps(shifted, table, column)]
        assert len(before) == len(after)
        # Même écart pour chaque ligne de chaque table, à la seconde près : une
        # translation unique, donc aucune relation temporelle n'est déformée.
        for b, a in zip(before, after):
            assert abs((a - b) - delta) < timedelta(seconds=1), f"{table}.{column}"


def test_shift_puts_the_last_scored_hour_at_the_current_hour(tmp_path):
    source = _source_db(tmp_path)
    output = tmp_path / "gold.db"
    export_gold(source=source, output=output, shift_to_now=True)

    last = max(datetime.strptime(v[:23], "%Y-%m-%d %H:%M:%S.%f")
               for v in _timestamps(output, "health_score_hourly", "timestamp"))
    assert last == datetime.now().replace(minute=0, second=0, microsecond=0)


def test_shift_clamps_the_observation_end_to_the_export_time(tmp_path):
    """La couverture capteur dépasse le dernier score de 8 jours dans la source.

    Recalée telle quelle, elle tomberait dans le futur et les fenêtres glissantes
    s'ouvriraient sur des dates qui n'existent pas encore.
    """
    source = _source_db(tmp_path)
    output = tmp_path / "gold.db"
    export_gold(source=source, output=output, shift_to_now=True)

    meta = _meta(output)
    observation_end = datetime.strptime(meta["silver_last_ts"][:23], "%Y-%m-%d %H:%M:%S.%f")
    assert observation_end <= datetime.now()


def test_statuses_follow_the_retained_observation_bound(tmp_path):
    source = _source_db(tmp_path)
    plain, shifted = tmp_path / "plain.db", tmp_path / "shifted.db"

    # Sans recalage : la borne reste la fin de couverture, comme au moment de la
    # détection — le recalcul est un no-op, les statuts d'origine sont conservés.
    assert export_gold(source=source, output=plain)["episode_status"] == {"resolved": 3}

    # Avec recalage, la borne devient l'instant de l'export : l'épisode le plus
    # récent n'a plus que quelques heures et cesse d'être annoncé « résolu ».
    assert export_gold(source=source, output=shifted,
                       shift_to_now=True)["episode_status"] != {"resolved": 3}


def test_gold_only_export_serves_windows_without_any_silver(tmp_path, monkeypatch):
    """Le correctif : l'API borne ses fenêtres sans jamais toucher au silver.

    Avant `gold_meta`, `window_days()` et `reference_now()` interrogeaient
    `th_clean` — présent en local, absent de l'export de déploiement. La bascule
    des anomalies en live aurait donc produit un 500 en production, et seulement
    là.
    """
    source = _source_db(tmp_path)
    output = tmp_path / "gold.db"
    export_gold(source=source, output=output)

    from app.config import settings
    from app.storage import analytics_db

    monkeypatch.setattr(settings, "analytics_db_path", output)
    analytics_db.get_analytics_engine.cache_clear()
    analytics_db.get_analytics_sessionmaker.cache_clear()
    try:
        from app.ml import anomalies

        assert anomalies.window_days() == (LAST_SENSOR - FIRST_SENSOR).days
        assert anomalies.reference_now().date() == LAST_SENSOR.date()
        assert len(anomalies.raw_episodes()) == 3
    finally:
        analytics_db.get_analytics_engine.cache_clear()
        analytics_db.get_analytics_sessionmaker.cache_clear()
