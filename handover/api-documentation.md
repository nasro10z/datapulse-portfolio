# DataPulse — Documentation API (handover)

> Référence de tous les endpoints REST exposés par le backend FastAPI. Pour l'architecture (aiguillage mock/live, où vivent les données), voir [`architecture.md`](architecture.md) §3. Swagger interactif toujours à jour : `http://localhost:8000/docs` (généré automatiquement par FastAPI depuis les schémas Pydantic ci-dessous).

## Conventions générales

- Base path : toutes les routes sont préfixées par **`/api`** (ex. `/api/health/overview`).
- Format : JSON en entrée/sortie, `Content-Type: application/json`.
- Dates/heures : ISO 8601 (`datetime` Pydantic).
- Erreurs : `404` avec `{"detail": "..."}` pour une ressource inconnue ; `422` pour un corps/paramètre invalide (validation Pydantic automatique) ; **`501`** avec `{"detail": "..."}` si `DATA_SOURCE=live` et que le gold n'a pas encore été calculé par l'ETL (voir `architecture.md` §3.1) — ce n'est pas une panne, c'est un pipeline pas encore lancé.
- Auth : aucune à ce jour (outil interne, pas exposé publiquement).
- Toutes les routes de lecture sont aiguillées mock ↔ live via `providers.py` de façon transparente — le contrat de réponse ne change jamais entre les deux sources.

---

## 1. Health — `/api/health`

Scores de santé du site et prévisions. Domaines : `environment`, `energy`, `battery`. Familles d'équipement : `stulz`, `socomec`, `yanan`.

### `GET /api/health/overview`
Score global du site + sous-scores par famille + par domaine, dernières 24h.

**Réponse** `HealthOverview` :
```jsonc
{
  "global_score": 69.9,
  "previous_score": 71.2,
  "status": "watch",              // healthy | watch | critical
  "sub_scores": [                  // 1 par famille d'équipement
    { "family": "stulz", "label": "...", "score": 82.1, "status": "healthy", "trend": "stable", "unit_count": 10, "note": null }
  ],
  "domain_scores": [                // 1 par domaine (environment/energy/battery)
    { "domain": "environment", "score": 90.0, "status": "healthy", "previous_score": 91.0, "note": null }
  ],
  "updated_at": "2026-08-05T10:00:00Z"
}
```

### `GET /api/health/forecast?horizon=24h|7d|30d`
Courbe du score global : historique + prévision + bande de confiance + franchissements de seuil prévus.

**Réponse** `ForecastResponse` : `{ horizon, points: [{ timestamp, value, lower, upper, is_forecast }], threshold_crossings: [{ timestamp, threshold, severity }] }`

### `GET /api/health/history?range=7d|30d|90d`
Historique brut (pas de prévision) du score global + des 3 domaines, pour le graphe Site Health.

**Réponse** `HealthHistoryResponse` : `{ range, points: [{ timestamp, global_score, environment, energy, battery }] }`

### `GET /api/health/predicted-faults?horizon=24h|7d|30d`
Prochaine panne estimée par famille d'équipement — **couche d'aide à la décision** : une fenêtre de risque indicative, jamais une certitude ni une alarme automatique.

**Réponse** `PredictedFaultsResponse` : `{ horizon, faults: [{ family, label, predicted_at, severity, note }] }` (`predicted_at`/`severity` nullable si aucune panne anticipée sur l'horizon).

### `GET /api/health/forecast/sub-scores?horizon=24h|7d|30d`
Même chose que `/forecast` mais **par famille d'équipement** au lieu du score global — alimente les cards secondaires de la page Forecast.

**Réponse** `SubScoreForecastResponse` : `{ horizon, series: [{ family, label, points: [ForecastPoint] }] }`

---

## 2. Anomalies — `/api/anomalies`

Épisodes d'anomalies détectés (HMM environnemental branché ; IsolationForest SCADA prêt côté `ml/` mais pas encore de données SCADA en anomalie à ce jour — voir `dimension` ci-dessous).

### `GET /api/anomalies`
Liste des épisodes, filtrable.

**Query params** (tous optionnels) : `equipment` (str), `severity` (`alert`|`critical`), `from`/`to` (datetime, bornes de `start`).

**Réponse** : `list[AnomalyEpisode]`
```jsonc
{
  "id": "EP-0001",
  "equipment": "STULZ-03",
  "type": "collective",           // collective | duration | sequence
  "severity": "alert",              // alert | critical
  "direction": "high",              // high | low
  "start": "2026-05-12T03:14:00Z",
  "duration_min": 42.5,
  "peak_value": 28.9,
  "status": "open",                 // open | acknowledged | resolved — surchargé par l'action utilisateur
  "dimension": "environment"        // environment (HMM temp/humidité) | scada (IsolationForest)
}
```

### `GET /api/anomalies/stats`
Compteurs globaux (sur l'historique complet des données livrées).

**Réponse** `AnomalyStats` : `{ total, anomaly_rate_pct, mtba_hours, by_type, by_severity, by_direction, by_status, top_equipment, top_equipment_count }`

### `GET /api/anomalies/histogram?bucket=day|week|month`
Comptes d'anomalies dans le temps, en bacs contigus (périodes vides incluses à 0), empilés par sévérité.

**Réponse** `AnomalyHistogram` : `{ bucket, bins: [{ period_start, total, by_severity }] }`

### `GET /api/anomalies/window-stats?window=24h|7d`
Stats bornées à une fenêtre glissante — alimente le KPI d'ouverture de la page Anomalies (total + tendance vs période précédente équivalente).

**Réponse** `WindowStats` : `{ window, total, previous_total, rate_pct, top_family, top_family_count, by_dimension, reference_at }`

> `reference_at` = fin de la période **observée** (pas l'heure courante) : sur un export historique figé (les données réelles s'arrêtent en mai 2026), sans cette date un « 0 anomalie » se lirait comme une page cassée plutôt que « rien à signaler sur la période ».

### `PATCH /api/anomalies/{episode_id}`
Acquitter ou résoudre un épisode (action utilisateur, persistée en SQLite état applicatif — voir `architecture.md` §4.3).

**Corps** `StatusUpdate` : `{ "status": "acknowledged" }` (ou `"resolved"`, `"open"`)
**Réponse** : `AnomalyEpisode` mis à jour · **404** si `episode_id` inconnu.

> Effet de bord : un épisode acquitté ne génère plus de rappel « anomalie non acquittée » (voir §3, `unacked_anomaly`).

---

## 3. Maintenance — `/api/maintenance`

Plannings de PM (maintenance préventive) — **saisis par l'utilisateur**, persistés en SQLite état applicatif, jamais dans la base source.

### `GET /api/maintenance/equipment`
Parc réel du site (10 STULZ, 2 SOCOMEC, 2 YANAN), pour peupler le sélecteur du formulaire.

**Réponse** : `list[str]` (ex. `["STULZ-01", ..., "SOCOMEC-01", "SOCOMEC-02", "YANAN-01", "YANAN-02"]`)

### `POST /api/maintenance/schedule`
Planifie une PM. `next_pm_date` est calculée côté serveur (`last_pm_date + period_value×period_unit`, clampée en fin de mois).

**Corps** `ScheduleRequest` : `{ equipment, last_pm_date, period_value (>0), period_unit ("days"|"weeks"|"months"), assigned_to?, notes? }`
**Réponse** `201` `CalendarEntry` : `{ id, equipment, last_pm_date, period_value, period_unit, next_pm_date, days_remaining, assigned_to, notes }`

### `GET /api/maintenance/calendar`
Liste de tous les plannings actifs (`days_remaining` recalculé à chaque lecture, pas stocké).

**Réponse** : `list[CalendarEntry]`

### `PATCH /api/maintenance/schedule/{pm_id}`
Édite un planning existant (même corps que `POST`, `next_pm_date` recalculée).

**Réponse** : `CalendarEntry` mis à jour · **404** si `pm_id` inconnu.

### `DELETE /api/maintenance/schedule/{pm_id}`
Supprime un planning.

**Réponse** : `204` · **404** si `pm_id` inconnu.

---

## 4. Reminders — `/api/reminders`

Rappels **dérivés** (jamais stockés directement) : PM à venir, seuils qui approchent, anomalies non acquittées. Pas de page dédiée — cloche dans le header (badge = `count`, popover = liste).

### `GET /api/reminders`
Liste des rappels actifs, une fois les rappels acquittés retirés et ceux snoozés masqués jusqu'à expiration.

**Réponse** : `list[Reminder]`
```jsonc
{
  "id": "RM-AN-EP-0003",           // préfixe par origine : RM-AN- (anomalie), RM-PM- (maintenance), RM-TH- (seuil)
  "kind": "unacked_anomaly",         // upcoming_pm | threshold_approach | unacked_anomaly
  "equipment": "STULZ-03",
  "message": "...",
  "due_at": "2026-08-06T09:00:00Z",
  "severity": "warning"                // info | warning | critical
}
```

### `GET /api/reminders/count`
Juste le compteur, pour le badge de la cloche sans charger toute la liste.

**Réponse** `ReminderCount` : `{ count: 4 }`

### `POST /api/reminders/{reminder_id}/acknowledge`
Acquitte un rappel (masqué définitivement de la liste dérivée).

**Réponse** : `204`

### `POST /api/reminders/{reminder_id}/snooze`
Reporte un rappel de N heures.

**Corps** `SnoozeRequest` : `{ "hours": 24 }` (borné `0 < hours ≤ 720`, soit 30 jours max)
**Réponse** : `204`

---

## 5. Enums partagés (référence rapide)

| Enum | Valeurs |
|---|---|
| `HealthStatus` | `healthy`, `watch`, `critical` |
| `EquipmentFamily` | `stulz`, `socomec`, `yanan` |
| `HealthDomain` | `environment`, `energy`, `battery` |
| `Trend` | `up`, `stable`, `down` |
| `AnomalyType` | `collective`, `duration`, `sequence` |
| `Severity` (anomalies) | `alert`, `critical` |
| `Direction` | `high`, `low` |
| `AnomalyStatus` | `open`, `acknowledged`, `resolved` |
| `AnomalyDimension` | `environment` (HMM), `scada` (IsolationForest) |
| `HistogramBucket` | `day`, `week`, `month` |
| `AnomalyWindow` | `24h`, `7d` |
| `ForecastHorizon` | `24h`, `7d`, `30d` |
| `HistoryRange` | `7d`, `30d`, `90d` |
| `PeriodUnit` | `days`, `weeks`, `months` |
| `ReminderKind` | `upcoming_pm`, `threshold_approach`, `unacked_anomaly` |
| `ReminderSeverity` | `info`, `warning`, `critical` |

## 6. Documents liés

- [`architecture.md`](architecture.md) — comment ces routes s'articulent avec `providers.py`, `services/`, `ml/`, le stockage
- Schémas Pydantic sources : `backend/app/models/{health,anomalies,maintenance,reminders}.py`
- Routes sources : `backend/app/api/{health,anomalies,maintenance,reminders}.py`
- Client frontend correspondant : `frontend/src/api/client.js`
