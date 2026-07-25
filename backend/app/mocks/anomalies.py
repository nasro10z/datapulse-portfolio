"""Mocks anomalies — ~30 épisodes sur 60 jours, cohérents avec le pipeline
validé (27-36 épisodes après hystérésis, seuils Tukey directionnels)."""
import random
from datetime import datetime, timedelta, timezone

from app.mocks.equipment import EXTREME_UPPER, MILD_UPPER, STULZ_UNITS, SOCOMEC_UNITS
from app.models.anomalies import (
    AnomalyEpisode,
    AnomalyStats,
    AnomalyStatus,
    AnomalyType,
    Direction,
    HistogramBin,
    HistogramBucket,
    HistogramResponse,
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


def get_episodes(
    equipment: str | None = None,
    severity: Severity | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[AnomalyEpisode]:
    out = EPISODES
    if equipment:
        out = [e for e in out if e.equipment == equipment]
    if severity:
        out = [e for e in out if e.severity == severity]
    if date_from:
        out = [e for e in out if e.start >= date_from]
    if date_to:
        out = [e for e in out if e.start <= date_to]
    return out


def set_status(episode_id: str, status: AnomalyStatus) -> AnomalyEpisode | None:
    """Met à jour le statut d'un épisode. Mock : l'état vit en mémoire et
    repart à zéro au redémarrage — la persistance viendra avec la Phase 8."""
    for e in EPISODES:
        if e.id == episode_id:
            e.status = status
            return e
    return None


def _floor_to_bucket(dt: datetime, bucket: HistogramBucket) -> datetime:
    day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if bucket == HistogramBucket.day:
        return day
    if bucket == HistogramBucket.week:
        return day - timedelta(days=day.weekday())  # lundi
    return day.replace(day=1)


def _next_bucket(dt: datetime, bucket: HistogramBucket) -> datetime:
    if bucket == HistogramBucket.day:
        return dt + timedelta(days=1)
    if bucket == HistogramBucket.week:
        return dt + timedelta(days=7)
    return (dt.replace(day=28) + timedelta(days=4)).replace(day=1)


def get_histogram(bucket: HistogramBucket = HistogramBucket.day) -> HistogramResponse:
    """Comptes d'épisodes par intervalle. Les intervalles sans épisode sont
    renvoyés à zéro : sans eux, une accalmie ressemblerait à une absence
    de mesure sur le graphique."""
    if not EPISODES:
        return HistogramResponse(bucket=bucket, bins=[])

    counts: dict[datetime, list[int]] = {}
    for e in EPISODES:
        key = _floor_to_bucket(e.start, bucket)
        slot = counts.setdefault(key, [0, 0])
        slot[0 if e.severity == Severity.alert else 1] += 1

    cursor = min(counts)
    last = max(counts)
    bins = []
    while cursor <= last:
        alert, critical = counts.get(cursor, [0, 0])
        bins.append(HistogramBin(
            period_start=cursor,
            total=alert + critical,
            alert=alert,
            critical=critical,
        ))
        cursor = _next_bucket(cursor, bucket)
    return HistogramResponse(bucket=bucket, bins=bins)


def get_stats() -> AnomalyStats:
    eps = EPISODES
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
        top_equipment=top_equipment,
        top_equipment_count=by_equipment[top_equipment],
    )
