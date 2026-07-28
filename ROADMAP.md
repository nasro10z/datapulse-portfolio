# ROADMAP.md — DataPulse

Ordre de développement recommandé, du scaffold initial jusqu'au livrable DSIP4. Chaque phase est pensée pour être une session de travail ciblée avec Claude Code (une phase = un ou plusieurs prompts précis, pas "fais tout").

---

## Phase 0 — Setup du repo
- [ ] Créer la structure `backend/` + `frontend/` telle que définie dans `CLAUDE.md`
- [ ] Initialiser FastAPI (`main.py`, config CORS pour autoriser le frontend en dev)
- [ ] Initialiser le projet React (Vite recommandé pour la rapidité)
- [ ] Ajouter `CLAUDE.md` et ce `ROADMAP.md` à la racine
- [ ] Configurer les variables d'environnement (connexion PostgreSQL `datacenter_ops`, ne jamais committer les credentials)
- [ ] Mettre en place un `requirements.txt` et un `package.json` propres

## Phase 1 — Backend : squelette API avec données mockées
Objectif : débloquer le frontend sans dépendre du pipeline ML réel.
- [ ] Définir les schémas Pydantic pour : health score (global + sub-scores), anomalie, épisode de maintenance, reminder
- [ ] Endpoint `GET /api/health/overview` — health score global + par équipement (données mockées cohérentes avec les seuils Tukey réels)
- [ ] Endpoint `GET /api/health/forecast?horizon=24h|7d|30d` — courbe historique + prévision + bande de confiance (mock)
- [ ] Endpoint `GET /api/anomalies` — liste d'épisodes (timestamp, durée, équipement, sévérité, statut), filtrable par date/équipement/sévérité
- [ ] Endpoint `GET /api/anomalies/stats` — comptes, fréquences par type/sévérité, MTBA (mean time between anomalies)
- [ ] Endpoint `POST /api/maintenance/schedule` — reçoit équipement + date dernière PM + période, retourne la date calculée de prochaine PM
- [ ] Endpoint `GET /api/maintenance/calendar` — liste des PM planifiées pour affichage calendrier
- [ ] Endpoint `GET /api/reminders` — rappels actifs (maintenances à venir, seuils approchants, anomalies non acquittées)
- [ ] Tests de contrat basiques (schéma de réponse) pour chaque endpoint

## Phase 2 — Frontend : squelette + intégration du design system
- [ ] Extraire les tokens du design Claude Design (couleurs, typographie, espacements) en config Tailwind/CSS variables
- [ ] Intégrer le logo DataPulse (header + favicon)
- [ ] Construire les composants de base réutilisables : gauge de health score, badge de sévérité (Healthy/Watch/Critical), card d'équipement, composant graphique courbe + bande de confiance
- [ ] Mettre en place le routing entre les 5 pages + sidebar de navigation
- [ ] Brancher chaque page sur les endpoints mockés de la Phase 1

## Phase 3 — Page Site Health Overview
- [ ] Health score agrégé du site (gauge/radial)
- [ ] Cards par famille d'équipement (10 STULZ, 2 SOCOMEC, 2 YANAN) avec mini-score, tendance, badge de statut

## Phase 4 — Page Prédiction des pannes (Forecast)
- [ ] Global Health Score Chart en pleine largeur, sélecteur d'horizon (24h/7j/30j)
- [ ] Bandes de confiance + alertes de franchissement de seuil prévu
- [ ] Section sub-scores en dessous, cards secondaires par famille d'équipement

## Phase 5 — Page Anomaly Detection ✅
- [x] Stat cards : total anomalies, taux d'anomalies, MTBA, équipement top contributeur
- [x] Histogramme des comptes d'anomalies dans le temps (filtrable jour/semaine/mois)
- [x] Répartition par type (collective/durée/séquence) et sévérité (alerte/critique, haut/bas) — + direction + statut
- [x] Table des épisodes récents avec actions (acquitter/résoudre) — + filtres équipement/sévérité
- [x] Backend : `PATCH /api/anomalies/{id}` (action persistée) + `GET /api/anomalies/histogram?bucket=`

## Phase 6 — Page Maintenance Préventive ✅
- [x] Calendrier en haut (élément dominant) — vue mensuelle navigable, marqueurs PM colorés par urgence
- [x] Formulaire compact : équipement / dernière PM / période → calcul automatique (sert aussi à l'édition)
- [x] Liste "Planning calculé" avec édition/suppression
- [x] Backend : `PATCH` / `DELETE /api/maintenance/schedule/{id}`

## Phase 7 — Page Reminders ✅
- [x] Liste des rappels actifs avec actions snooze/acquitter
- [x] Badge de compteur dans la nav
- [x] Backend : `POST /api/reminders/{id}/snooze` + `/acknowledge`, `GET /api/reminders/count` (actions persistées, filtrent la liste dérivée)

## Phase 8 — Intégration du vrai pipeline ML (package `mlops-api` livré)
Architecture détaillée : **`docs/data-architecture.md`** (couches bronze/silver/gold,
séparation storage/etl/ml, intégration en librairie). Source de données = **exports
CSV** (PostgreSQL non joignable). Pipeline livré = package `mlops-api` (2 modèles :
`environmental` HMM temp/humidité, `alarm_anomaly` IsolationForest SCADA).
- [x] **Seam mock ↔ live** : aiguillage par `DATA_SOURCE`, `app/providers.py` (routes découplées de la source), contrat `ml/` (stubs + README), agrégations partagées (`services/anomaly_aggregation.py`), 501 explicite tant que non branché
- [ ] **A** — `storage/` : base analytique SQLite + schémas bronze/silver/gold + repositories (testable à vide)
- [x] **B** — `mlops-api` vendorisé dans `app/ml/` (`environmental`, `alarm_anomaly`, `models/`) ; imports réécrits en `app.ml.*`, chemins modèles corrigés ; les 2 modèles chargent et prédisent (vérifié). Deps : `hmmlearn`, `scikit-learn==1.9.0`, `openpyxl`.
- [x] **C** — `etl/ingest` : lecteurs bruts (`sources.py`) + **golden tests de fidélité** (env 99.95 %, SCADA 100 % exact) ; **écriture bronze** (`storage/repositories/bronze_repo`, `etl/ingest/backfill`, watermark + idempotence). Backfill réel : `raw_temp_humidity`=137 970, `raw_scada_log`=3 274. NB : alarmes 2022 hors combiné modèle (perdues par parsing dans le notebook d'origine).
- [x] **D** — `etl/transform` : bronze → silver (`th_clean`) via `dedupe_and_index`+`add_segments` du package. Réel : 107 047 lignes, **1 905 segments** (≈ 1904 validés).
- [x] **E** — `etl/detect` : HMM environnemental déroulé sur le silver → runs d'état anormal **filtrés sur franchissement réel de seuil température** (décision produit) → gold `anomaly_episode` **par salle** (`SALLE_SWITCH`). Réel : **388 épisodes** (228 high / 160 low, 14 critical), 0 en température normale. `gold_repo` écrit. NB : anomalies humidité/contextuelles du HMM écartées (≈1383 runs bruts → 388).
- [ ] **F** — `etl/score,forecast` : health scores + forecast → gold
- [~] **G** — source live → lecture `gold_repo` : **anomalies + rappels servis en live** (`ml/anomalies` lit le gold, `providers` inchangé). Vérifié : `GET /api/anomalies`=200 (388 épisodes), stats/histogramme/rappels OK, plus de 501. Reste : health/forecast (dépend de F).
- [ ] **H** — `etl/incremental` + temps réel (watermark) — quand un flux sera disponible

## Phase 9 — Extension de la couverture
- [ ] Étendre la détection d'anomalies aux UPS (SOCOMEC) et generators (YANAN)
- [ ] Exploiter la comparaison inter-unités des 10 STULZ identiques (méthode à haut potentiel identifiée)

## Phase 10 — Polish & livrable
- [x] Tests des parcours critiques (planifier une PM, consulter/acquitter une anomalie, lire le forecast) — Vitest + Testing Library (6 tests, API mockée). NB : niveau intégration ; e2e navigateur complet (Playwright) laissé en option.
- [x] Responsive mobile sur les 5 pages — sidebar en tiroir sous 768px (hamburger + backdrop + Échap), 0 débordement horizontal vérifié à 375px
- [x] Vérification accessibilité — structure de titres (h1→h2), `:focus-visible`, noms accessibles sur tous les interactifs, aria sur tiroir/badge, contrastes AA (texte 18:1, muted ~7:1, statuts ≥4.7:1)
- [ ] Rédaction du livrable DSIP4 — s'appuyer sur les métriques livrées avec les modèles (`metadata.json`) ; pas d'affirmation de performance non sourcée.

---

## Principe de travail avec Claude Code
Une session = une case à cocher (ou un petit groupe cohérent), avec les specs exactes en entrée plutôt qu'un brief vague. Toujours faire relire/valider par une revue rapide avant de passer à la case suivante.
