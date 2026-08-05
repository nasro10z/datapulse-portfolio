# DataPulse — Vue d'ensemble du projet (handover)

> Document de passation. Pour le détail opérationnel (comment développer, conventions, contraintes)
## 1. Qu'est-ce que DataPulse

DataPulse est une plateforme d'analytics et de maintenance prédictive. C'est le livrable du projet académique **DSIP4 — Use Case UC3**.

- **Positionnement** : une **couche d'aide à la décision** — jamais présentée comme un système d'alarme autonome ou qui décide à la place de l'humain.
- **Site couvert** : data center télécom **MSC-10**.
- **Catégories d'Équipements surveillés** :
  - ENVIRONNEMENTALES
  - ENERGETIQUES
  - BATTERIES
- **Personas cibles** : manager de site (vue globale), superviseur d'alarmes (réduire la fatigue liée aux fausses alertes), technicien de maintenance (anticiper la dégradation avant panne).

## 2. Stack technique

| Couche | Techno |
|---|---|
| Backend | FastAPI (Python) |
| Frontend | React (Vite) |
| Stockage analytique | SQLite (bronze/silver/gold, voir §4) |
| État applicatif (PM, acquittements, snooze) | SQLite séparé |
| Source de données brute | PostgreSQL `datacenter_ops` — **non joignable directement**, données fournies en exports CSV |
| ML | pandas, numpy, scikit-learn, hmmlearn, XGBoost — pipeline déjà validé, livré en package `mlops-api` |

## 3. Architecture du repo

```
datapulse/
├── backend/app/
│   ├── api/          # routes FastAPI par domaine
│   ├── models/        # schémas Pydantic
│   ├── ml/              # pipeline ML vendorisé (mlops-api) — maths pures, aucune I/O
│   ├── etl/             # orchestration : lit bronze, appelle ml/, écrit silver/gold
│   ├── storage/       # persistance pure (tables + repositories)
│   ├── services/     # logique métier (PM, anomalies, agrégations)
│   ├── mocks/        # données de démo (jeu de seed, plus la source de vérité)
│   └── db/               # SQLite état applicatif
├── frontend/src/
│   ├── components/
│   ├── pages/           # Aperçu (/), Santé du site (/health), Forecast, Anomalies, Maintenance
│   ├── design-system/ # tokens extraits de Claude Design (Identity v2)
│   └── api/
```


## 4. Pipeline de données — principe medallion

```
SOURCE (PostgreSQL, lecture seule, via CSV)
   → bronze (brut, append-only : raw_temp_humidity, raw_scada_log)
   → silver (nettoyé : th_clean, scada_clean — dédup, segments, rolling stats)
   → gold (prêt-à-servir : anomaly_episode, health_score_hourly, forecast_point)
   → API (lit uniquement le gold)
```

- **Granularité de détection** : par catégorie d'équipement ( ex: environnemental ), pas par unité STULZ individuelle.
- **Seuils de sévérité** (Tukey IQR, livrés avec le modèle `environmental`) : `mild_upper=26.75°C`, `extreme_upper=28.65°C`.
- **Prévision** : XGBoost entraîné sur le **delta 6h** (variation, pas niveau) sur les top 20 features ; au-delà de +6h, déroulé récursif amorti à conditions inchangées.
- Aucune affirmation de performance au-delà des métriques livrées dans `metadata.json` des modèles (ex. F1 anomalie `environmental` = 0.83) — pas de jeu de labels ground-truth externe disponible.

## 5. Design produit — les 5 pages

1. **Aperçu** (`/`, page d'accueil d'un site) : score global + sous-scores 24h, prochaine panne prédite, 5 dernières anomalies, prochaine maintenance + compte 7 jours.
2. **Santé du site** (`/health`) : gauge de score + cards par famille d'équipement.
3. **Forecast** : Global Health Score Chart pleine largeur (dominant, sélecteur 24h/7j/30j) + sous-scores en cards secondaires.
4. **Anomalies** : stat cards, histogramme empilé (jour/semaine/mois), répartitions (type/sévérité/direction/statut), table d'épisodes avec actions acquitter/résoudre.
5. **Maintenance** : KPI prochaine PM en haut, formulaire de planification, calendrier cliquable (vue dominante), édition/suppression.

Les **rappels** ne sont pas une page : cloche dans le header avec badge de compteur et popover (acquitter/reporter).

Design system : palette navy/charcoal/gris neutres, accents thermique/énergie/criticité utilisés avec parcimonie, typographie à chiffres tabulaires (Space Grotesk + JetBrains Mono), thème sombre par défaut.

## 6. État d'avancement (voir `ROADMAP.md` et `SESSIONS.md` pour le détail)

| Phase | Statut |
|---|---|
| 0 — Scaffold repo | ✅ |
| 1 — Backend mocké (7 endpoints) | ✅ |
| 2 — Frontend : design system + squelette 5 pages | ✅ |
| 3 — Page Santé du site | ✅ |
| 4 — Page Forecast | ✅ |
| 5 — Page Anomalies (histogramme, filtres, acquitter/résoudre) | ✅ |
| 6 — Page Maintenance (calendrier dominant, édition/suppression) | ✅ |
| 7 — Reminders (snooze/acquittement, badge nav) | ✅ |
| 8 — Intégration pipeline ML réel (A→G) | ✅ sauf **H** (ingestion temps réel — bloqué faute de flux live disponible) |
| 9 — Extension UPS/generator | ⬜ non démarrée |
| 10 — Polish & livrable | Tests critiques ✅, responsive ✅, accessibilité ✅ ;

**Chiffres clés du pipeline réel branché** (Phase 8) :
- 107 047 lignes température/humidité → 1 905 segments
- 388 épisodes d'anomalies (228 high / 160 low, 14 critical)
- 2 137 heures de health score, 164 points de forecast
- `health/overview` en live : score global 69,9 (Env 90,0 · Énergie 68,4 · Batterie 54,2)
*
