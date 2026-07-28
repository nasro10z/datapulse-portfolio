"""Agrégations sur les épisodes d'anomalie — indépendantes de la source.

Ces fonctions opèrent sur une liste d'`AnomalyEpisode` quelle qu'en soit
l'origine (mock ou pipeline ML). La production des épisodes est spécifique à la
source (voir `app/providers.py`) ; le calcul des stats, de l'histogramme, la
surcharge de statut et le filtrage sont, eux, partagés.
"""
from datetime import date, datetime, timedelta

from app.mocks.equipment import SOCOMEC_UNITS, STULZ_UNITS, YANAN_UNITS
from app.models.anomalies import (
    AnomalyDimension,
    AnomalyEpisode,
    AnomalyHistogram,
    AnomalyStats,
    AnomalyStatus,
    AnomalyType,
    AnomalyWindow,
    Direction,
    HistogramBin,
    HistogramBucket,
    Severity,
    WindowStats,
)

_FAMILY_BY_UNIT = (
    {u: "stulz" for u in STULZ_UNITS}
    | {u: "socomec" for u in SOCOMEC_UNITS}
    | {u: "yanan" for u in YANAN_UNITS}
)
_WINDOW_HOURS = {AnomalyWindow.h24: 24, AnomalyWindow.d7: 24 * 7}


def family_of(equipment: str) -> str:
    """Famille d'équipement pour un identifiant brut. `SALLE_SWITCH` (granularité
    de détection environnementale, cf. `etl/detect.py`) est climatisée par les
    STULZ → rattachée à la famille `stulz`."""
    if equipment == "SALLE_SWITCH":
        return "stulz"
    return _FAMILY_BY_UNIT.get(equipment, "unknown")


def apply_overrides(
    episodes: list[AnomalyEpisode],
    overrides: dict[str, AnomalyStatus] | None,
) -> list[AnomalyEpisode]:
    """Surcharge le statut simulé/calculé par l'action de l'utilisateur."""
    if not overrides:
        return episodes
    return [
        e.model_copy(update={"status": overrides[e.id]}) if e.id in overrides else e
        for e in episodes
    ]


def filter_episodes(
    episodes: list[AnomalyEpisode],
    equipment: str | None = None,
    severity: Severity | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AnomalyEpisode]:
    out = episodes
    if equipment:
        out = [e for e in out if e.equipment == equipment]
    if severity:
        out = [e for e in out if e.severity == severity]
    if date_from:
        out = [e for e in out if e.start >= date_from]
    if date_to:
        out = [e for e in out if e.start <= date_to]
    return out


def _bucket_start(d: date, bucket: HistogramBucket) -> date:
    if bucket == HistogramBucket.day:
        return d
    if bucket == HistogramBucket.week:
        return d - timedelta(days=d.weekday())  # lundi de la semaine
    return d.replace(day=1)


def _next_bucket(d: date, bucket: HistogramBucket) -> date:
    if bucket == HistogramBucket.day:
        return d + timedelta(days=1)
    if bucket == HistogramBucket.week:
        return d + timedelta(days=7)
    return (d.replace(day=1) + timedelta(days=32)).replace(day=1)


def compute_histogram(episodes: list[AnomalyEpisode], bucket: HistogramBucket) -> AnomalyHistogram:
    """Comptes par période (jour/semaine/mois), bacs contigus — les périodes
    sans anomalie sont incluses avec un compte nul."""
    counts: dict[date, dict[Severity, int]] = {}
    for e in episodes:
        start = _bucket_start(e.start.date(), bucket)
        counts.setdefault(start, {s: 0 for s in Severity})[e.severity] += 1

    bins: list[HistogramBin] = []
    if counts:
        cur, last = min(counts), max(counts)
        while cur <= last:
            by_sev = counts.get(cur, {s: 0 for s in Severity})
            bins.append(HistogramBin(period_start=cur, total=sum(by_sev.values()), by_severity=by_sev))
            cur = _next_bucket(cur, bucket)
    return AnomalyHistogram(bucket=bucket, bins=bins)


def compute_stats(episodes: list[AnomalyEpisode], window_days: int) -> AnomalyStats:
    """`window_days` = fenêtre d'observation, pour le taux d'anomalies
    (part du temps passée en anomalie)."""
    by_equipment: dict[str, int] = {}
    for e in episodes:
        by_equipment[e.equipment] = by_equipment.get(e.equipment, 0) + 1
    top_equipment = max(by_equipment, key=by_equipment.get) if by_equipment else "—"

    starts = sorted(e.start for e in episodes)
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(starts, starts[1:])]
    mtba = sum(gaps) / len(gaps) if gaps else 0.0

    total_min = max(1, window_days * 24 * 60)
    anomalous_min = sum(e.duration_min for e in episodes)

    return AnomalyStats(
        total=len(episodes),
        anomaly_rate_pct=round(100 * anomalous_min / total_min, 2),
        mtba_hours=round(mtba, 1),
        by_type={t: sum(1 for e in episodes if e.type == t) for t in AnomalyType},
        by_severity={s: sum(1 for e in episodes if e.severity == s) for s in Severity},
        by_direction={d: sum(1 for e in episodes if e.direction == d) for d in Direction},
        by_status={st: sum(1 for e in episodes if e.status == st) for st in AnomalyStatus},
        top_equipment=top_equipment,
        top_equipment_count=by_equipment.get(top_equipment, 0),
    )


def _naive(dt: datetime) -> datetime:
    """Le mock produit des `start` timezone-aware (UTC) ; le gold live les
    stocke naïfs (UTC implicite, cf. `storage/repositories/gold_repo.py`).
    Normalise avant comparaison pour rester agnostique de la source."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def compute_window_stats(episodes: list[AnomalyEpisode], window: AnomalyWindow, now: datetime) -> WindowStats:
    """Total + tendance (vs période précédente de même durée) + taux + famille
    top + répartition par dimension, sur une fenêtre glissante se terminant à `now`.

    `now` est la **fin de la période observée**, fournie par la source (cf.
    `reference_now()`), pas l'heure de la requête : sur un export historique figé,
    une fenêtre calée sur l'horloge tombe des semaines après la dernière donnée et
    ne peut que renvoyer zéro.
    """
    now = _naive(now)
    hours = _WINDOW_HOURS[window]
    cur_start = now - timedelta(hours=hours)
    prev_start = cur_start - timedelta(hours=hours)

    current = [e for e in episodes if cur_start <= _naive(e.start) <= now]
    previous = [e for e in episodes if prev_start <= _naive(e.start) < cur_start]

    by_family: dict[str, int] = {}
    for e in current:
        fam = family_of(e.equipment)
        by_family[fam] = by_family.get(fam, 0) + 1
    top_family = max(by_family, key=by_family.get) if by_family else None

    window_minutes = hours * 60
    anomalous_minutes = sum(e.duration_min for e in current)

    return WindowStats(
        window=window,
        total=len(current),
        previous_total=len(previous),
        rate_pct=round(100 * anomalous_minutes / window_minutes, 2),
        top_family=top_family,
        top_family_count=by_family.get(top_family, 0) if top_family else 0,
        by_dimension={d: sum(1 for e in current if e.dimension == d) for d in AnomalyDimension},
        reference_at=now,
    )
