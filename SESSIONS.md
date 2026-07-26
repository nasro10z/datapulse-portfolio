# SESSIONS.md — Journal des sessions DataPulse

Retrace ce qui a été fait à chaque session de travail avec Claude Code. Une entrée par session : date, phases ROADMAP couvertes, réalisations, décisions, points en suspens. **À mettre à jour à la fin de chaque session.**

---

## Session 3 — 2026-07-26 (suite) — Phase 5 Anomaly Detection

**Phases couvertes** : Phase 5 — terminée (page enrichie + endpoints d'écriture/agrégation).

### Réalisations
- **Backend** — les épisodes restent en lecture seule (mock/ML) ; seule l'action utilisateur (acquitter/résoudre) est persistée, sur le même modèle que les PM :
  - `db/tables.AnomalyAction` (clé = id d'épisode `EP-0001`, stable au redémarrage), `services/anomalies.py` (get_status_overrides / set_status).
  - `mocks/anomalies.py` : statut effectif = statut simulé surchargé par l'action ; `get_histogram(bucket)` (bacs contigus jour/semaine/mois, périodes vides à 0) ; `by_status` ajouté à `AnomalyStats`.
  - Routes : `PATCH /api/anomalies/{id}` (404 si épisode inconnu), `GET /api/anomalies/histogram?bucket=day|week|month`, `GET /api/anomalies` et `/stats` surchargés par les actions.
  - **Cohérence reminders** : la route `reminders` injecte désormais les épisodes déjà surchargés → un épisode acquitté ne génère plus de rappel « non acquitté » (le point en suspens de la session précédente est traité, et c'est adossé à un vrai enregistrement, pas une disparition silencieuse).
- **Frontend** — page Anomalies complétée : histogramme empilé par sévérité + sélecteur jour/semaine/mois (`components/AnomalyHistogram.jsx`), panneau Répartitions (type/sévérité/direction/statut, données déjà servies par le backend), filtres équipement + sévérité (branchés sur les query params backend), boutons Acquitter/Résoudre par ligne (`PATCH` + reload). `api/client.js` : `anomalyHistogram`, `updateAnomalyStatus`, filtrage des params vides.

### Validation
- `pytest tests/` : **19/19 verts** (4 nouveaux : histogramme 3 granularités + conservation du total, acquittement persisté + reflété dans `by_status`, 404 épisode inconnu, acquittement d'une anomalie « open » qui efface son rappel). Fixture autouse `reset_anomaly_actions` ajoutée pour isoler les tests de mutation sur la base partagée.
- **Vérif backend live** (uvicorn) : histogramme day=59 bacs / month=3, `PATCH` acquitte, rappel `RM-AN-…` présent puis absent, `by_status` mis à jour, 404 sur id inconnu.
- ⚠️ **Frontend non buildé/vérifié navigateur cette session : Node absent de la machine** (les sessions précédentes l'avaient ; `npm`/`node.exe` introuvables). Code écrit sur les patterns exacts des pages existantes ; à builder + vérifier au navigateur au prochain démarrage avec Node dispo.

### En suspens
- Rebuild + vérif navigateur de la page Anomalies dès que Node est réinstallé.
- Phases 6–7 restantes : `PATCH`/`DELETE /maintenance/schedule/{id}` (édition/suppression) + vue calendrier dominante ; snooze/acquittement reminders + badge compteur nav. Le pattern « action persistée surchargeant une donnée dérivée » est maintenant établi (maintenance + anomalies) et réutilisable pour le snooze.

---

## Session 3 — 2026-07-26 — Persistance PM

**Phases couvertes** : préparation Phases 5–7 — persistance des plannings de PM (pré-requis édition/suppression Phase 6, snooze/acquittement Phase 7).

### Contexte
Revue complète du codebase : Phases 3 et 4 constatées déjà réalisées en Phase 2 (gauge + cards Site Health, chart pleine largeur + sélecteur horizon + bandes + sous-scores Forecast). Prochain vrai chantier = Phases 5–7, toutes bloquées par l'absence d'endpoints d'écriture et par un état applicatif en mémoire volatile.

### Réalisations
- Remplacement du store en mémoire (`_STORE` module-level) par une **persistance SQLite** dédiée à l'état applicatif, distincte de la base source PostgreSQL :
  - `app/db/app_db.py` (engine + sessionmaker SQLite via `URL.create()`, `init_db`, dépendance `get_session`), `app/db/tables.py` (`PMSchedule`, SQLAlchemy 2.0 `DeclarativeBase`).
  - Logique métier PM déplacée de `mocks/` vers `app/services/maintenance.py` (calcul date + CRUD) — les plannings sont saisis par l'utilisateur, pas mockés.
  - `mocks/maintenance.py` réduit au **jeu de démo** (`seed_demo_calendar`, inséré seulement si le calendrier est vide).
  - Routes `maintenance` et `reminders` branchées sur `Depends(get_session)` ; `mocks/reminders.py` reçoit désormais le calendrier en argument (aucune dépendance base dans `mocks/`).
  - Lifespan FastAPI : `init_db()` + seed de démo au démarrage.
- `config.py` : `app_db_path` (défaut `backend/data/datapulse.db`, surchargeable via `APP_DB_PATH`). `.gitignore` : `backend/data/`. `.env.example` + `README.md` backend mis à jour (tableau deux-bases).

### Décisions
- **Deux bases séparées** : PostgreSQL `datacenter_ops` reste en lecture seule (données data center) ; l'état saisi dans l'outil va en SQLite local — ce que l'utilisateur saisit n'a pas à être écrit dans la base source.
- Sémantique Forecast (courbe en °C sous un panel « Global Health Score ») laissée en l'état : données d'échantillon, à revoir lors du branchement des vrais modèles (Phase 8).

### Validation
- `pytest tests/` : **15/15 verts** (nouveau test `test_schedule_persists_on_disk` : relecture via un moteur SQLite neuf sur le même fichier).
- Test de redémarrage réel : PM POSTée sur un process, relue par un **process neuf** (calendrier + reminders dérivés) → persistance confirmée sur disque.

### En suspens
- Endpoints d'écriture restants pour Phases 5–7 : `PATCH /anomalies/{id}` (acquitter/résoudre), `PATCH`/`DELETE /maintenance/schedule/{id}`, snooze/acquittement reminders — l'acquittement d'anomalie devra coexister avec la dérivation des reminders (sinon un reminder disparaît sans trace de snooze).
- Contenu Phase 5 (histogramme, filtres UI, répartitions by_type/by_severity déjà servies par le backend), Phase 6 (vue calendrier + édition/suppression), Phase 7 (snooze + badge compteur nav).

---

## Session 2 — 2026-07-25

**Phases couvertes** : Phase 2 (frontend : design system + squelette 5 pages) — terminée.

### Réalisations
- Premier commit git du repo (baseline Phase 0+1), puis branche `worktree-phase2-frontend-design-system`.
- Tokens Identity v2 extraits en CSS variables (`src/design-system/tokens.css`) : palette ink/slate, accent bleu #2F6BFF, statuts Healthy/Watch/Critical, typo Space Grotesk + JetBrains Mono (chiffres tabulaires), espacements/rayons/motion. Thème sombre par défaut + surcharges `[data-theme="light"]`.
- Logo DataPulse (mark "pulse" SVG extrait du fichier Identity v2) en header sidebar + favicon SVG.
- Composants de base : `HealthGauge` (arc 270°), `StatusBadge` (icône + libellé, jamais couleur seule), `EquipmentCard` (score/tendance/statut), `TrendChart` (courbe + bande de confiance, historique plein / prévision pointillée, franchissements de seuil, crosshair + tooltip), `Panel`.
- Routing react-router-dom : layout sidebar + topbar fidèle au mockup, 5 pages (Site Health, Forecast, Anomalies, Maintenance, Reminders) toutes branchées sur les 7 endpoints mockés (`src/api/client.js`, hook `useApi` avec états chargement/erreur).

### Décisions
- Palette viz : mono-série en Phase 2 (viz-1 #2F6BFF validé CVD/contraste sur surface sombre) ; toute future palette multi-séries devra repasser le validateur (les accents clairs échouent la bande de luminosité en mode sombre en usage catégoriel).
- Le "calendrier" Maintenance est une table chronologique en Phase 2 ; la vue calendrier dominante arrive en Phase 6.

### Validation
- `npm run build` OK (53 modules).
- Vérification visuelle navigateur des 5 pages sur les mocks (backend uvicorn + Vite) : rendu conforme au design, tooltip/crosshair et sélecteur d'horizon fonctionnels.

### En suspens
- Enrichissement par page (Phases 3–7) : histogramme anomalies, actions acquitter/résoudre, snooze reminders, badge compteur nav, vue calendrier.
- Toggle thème clair (tokens prêts, pas de bouton).

---

## Session 1 — 2026-07-25

**Phases couvertes** : Phase 0 (scaffold) + Phase 1 (backend mocké) — terminées et validées.

### Réalisations
- Scaffold complet `backend/` (FastAPI) : `app/api/` (4 routers), `app/models/` (schémas Pydantic), `app/mocks/` (générateurs seedés), `app/db/engine.py` (SQLAlchemy `URL.create()`, non branché), `app/config.py` (pydantic-settings + `.env`), `app/ml/` (placeholder avec README de la règle de séparation ml/api).
- 7 endpoints mockés : `GET /api/health/overview`, `GET /api/health/forecast?horizon=24h|7d|30d`, `GET /api/anomalies` (filtres equipment/severity/from/to), `GET /api/anomalies/stats`, `POST /api/maintenance/schedule`, `GET /api/maintenance/calendar`, `GET /api/reminders`.
- Mocks cohérents avec le pipeline validé : seuils Tukey 27.85/30.40°C, 30 épisodes d'anomalies (fourchette 27-36), parc réel 10 STULZ + 2 SOCOMEC + 2 YANAN (YANAN en statut "watch" avec note baseline).
- Tests de contrat pytest pour les 4 domaines (schémas, filtres, calcul de date PM avec clamp fin de mois, 422 sur entrées invalides).
- Scaffold `frontend/` : Vite 5 + React 18 + Tailwind v4, page placeholder, proxy `/api` → localhost:8000. Build vérifié OK.
- `.gitignore`, `.env.example`, `README.md` backend.

### Décisions
- Scope session confirmé : Phase 0 + 1 (frontend reste une coquille).
- Styling : Tailwind v4 + CSS variables (tokens Identity v2 extraits en Phase 2).
- Scaffold frontend écrit à la main avec Vite 5 : `create-vite` récent incompatible avec Node v21.2.0 local (requiert `styleText` de Node 21.7+).

### Validation
- `pytest tests/` : **14/14 verts** (contrats health/forecast/anomalies/maintenance/reminders).
- Smoke test uvicorn : `/api/health/overview` répond (global_score=81.6, healthy), les 7 endpoints présents dans l'OpenAPI.
- Vulnérabilités npm corrigées : override `esbuild ^0.25` + upgrade `vite ^6.4.3` (patch du bypass `server.fs.deny` Windows) → `npm audit` : 0 vulnérabilité. Vite 6 émet un warning EBADENGINE sur Node v21.2.0 mais build et dev server fonctionnent.

### En suspens
- Premier commit git à faire (tout est encore untracked).
- Optionnel : passer Node en 22 LTS pour éliminer le warning EBADENGINE et rouvrir l'option `create-vite`/Vite 7+.
- Prochaine session : Phase 2 (tokens design system depuis "DataPulse - Identity v2 (standalone).html", composants de base, routing 5 pages).
