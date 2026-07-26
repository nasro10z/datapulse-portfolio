"""Mocks anomalies — ~30 épisodes sur 60 jours, cohérents avec le pipeline
validé (27-36 épisodes après hystérésis, seuils Tukey directionnels).

Les épisodes sont en lecture seule. Le statut effectif = statut simulé, surchargé
par l'action éventuelle de l'utilisateur (`overrides`, injecté par la route depuis
la base applicative — voir `services/anomalies.py`)."""
import random
from datetime import date, datetime, timedelta, timezone

from app.mocks.equipment import EXTREME_UPPER, MILD_UPPER, STULZ_UNITS, SOCOMEC_UNITS
from app.models.anomalies import (
    AnomalyEpisode,
    AnomalyHistogram,
    AnomalyStats,
    AnomalyStatus,
    AnomalyType,
    Direction,
    HistogramBin,
    HistogramBucket,
    Severity,
)

_EPISODE_COUNT = 30
_WINDOW_DAYS = 60


def _build_episodes() -> list[AnomalyEpisode]:
    rng = random.Random(1904)  # clin d'œil aux ~1904 segments du pipeline
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    episodes = []
    for i in range(_EPISODE_COUNT):
        severity = Severity.critical if rng.random() < 0.25 else Severity.alert
        direction = Direction.high if rng.random() < 0.8 else Direction.low
        if direction == Direction.high:
            peak = (rng.uniform(EXTREME_UPPER, EXTREME_UPPER + 2.5)
                    if severity == Severity.critical
                    else rng.uniform(MILD_UPPER, EXTREME_UPPER - 0.1))
        else:
            peak = rng.uniform(16.5, 19.5)
        # la salle switch est climatisée par les STULZ : ils dominent les épisodes
        equipment = rng.choice(STULZ_UNITS * 4 + SOCOMEC_UNITS)
        start = now - timedelta(hours=rng.uniform(2, _WINDOW_DAYS * 24))
        age_h = (now - start).total_seconds() / 3600
        status = (AnomalyStatus.resolved if age_h > 72
                  else AnomalyStatus.acknowledged if age_h > 24
                  else AnomalyStatus.open)
        episodes.append(AnomalyEpisode(
            id=f"EP-{i + 1:04d}",
            equipment=equipment,
            type=rng.choice(list(AnomalyType)),
            severity=severity,
            direction=direction,
            start=start.replace(microsecond=0),
            duration_min=round(rng.uniform(8, 160), 1),
            peak_value=round(peak, 2),
            status=status,
        ))
    episodes.sort(key=lambda e: e.start, reverse=True)
    return episodes


EPISODES: list[AnomalyEpisode] = _build_episodes()
EPISODE_IDS: frozenset[str] = frozenset(e.id for e in EPISODES)


def _with_overrides(
    episodes: list[AnomalyEpisode],
    overrides: dict[str, AnomalyStatus] | None,
) -> list[AnomalyEpisode]:
    if not overrides:
        return episodes
    return [
        e.model_copy(update={"status": overrides[e.id]}) if e.id in overrides else e
        for e in episodes
    ]


def get_episodes(
    overrides: dict[str, AnomalyStatus] | None = None,
    equipment: str | None = None,
    severity: Severity | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AnomalyEpisode]:
    out = _with_overrides(EPISODES, overrides)
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


def get_histogram(bucket: HistogramBucket) -> AnomalyHistogram:
    """Comptes d'anomalies par période (jour/semaine/mois), bacs contigus —
    les périodes sans anomalie sont incluses avec un compte nul."""
    counts: dict[date, dict[Severity, int]] = {}
    for e in EPISODES:
        start = _bucket_start(e.start.date(), bucket)
        counts.setdefault(start, {s: 0 for s in Severity})[e.severity] += 1

    bins: list[HistogramBin] = []
    if counts:
        cur, last = min(counts), max(counts)
        while cur <= last:
            by_sev = counts.get(cur, {s: 0 for s in Severity})
            bins.append(HistogramBin(
                period_start=cur,
                total=sum(by_sev.values()),
                by_severity=by_sev,
            ))
            cur = _next_bucket(cur, bucket)
    return AnomalyHistogram(bucket=bucket, bins=bins)


def get_stats(overrides: dict[str, AnomalyStatus] | None = None) -> AnomalyStats:
    eps = _with_overrides(EPISODES, overrides)
    by_equipment: dict[str, int] = {}
    for e in eps:
        by_equipment[e.equipment] = by_equipment.get(e.equipment, 0) + 1
    top_equipment = max(by_equipment, key=by_equipment.get)

    starts = sorted(e.start for e in eps)
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(starts, starts[1:])]
    mtba = sum(gaps) / len(gaps) if gaps else 0.0

    total_min = _WINDOW_DAYS * 24 * 60
    anomalous_min = sum(e.duration_min for e in eps)

    return AnomalyStats(
        total=len(eps),
        anomaly_rate_pct=round(100 * anomalous_min / total_min, 2),
        mtba_hours=round(mtba, 1),
        by_type={t: sum(1 for e in eps if e.type == t) for t in AnomalyType},
        by_severity={s: sum(1 for e in eps if e.severity == s) for s in Severity},
        by_direction={d: sum(1 for e in eps if e.direction == d) for d in Direction},
        by_status={st: sum(1 for e in eps if e.status == st) for st in AnomalyStatus},
        top_equipment=top_equipment,
        top_equipment_count=by_equipment[top_equipment],
    )
