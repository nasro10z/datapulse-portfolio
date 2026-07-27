# SESSIONS.md — Journal des sessions DataPulse

Retrace ce qui a été fait à chaque session de travail avec Claude Code. Une entrée par session : date, phases ROADMAP couvertes, réalisations, décisions, points en suspens. **À mettre à jour à la fin de chaque session.**

---

<<<<<<< HEAD
## Session 3 — 2026-07-26 (suite) — Vue globale + responsive mobile

**Demandes** : (1) vue globale de tous les sites, puis personnalisation au site sélectionné ; (2) rendre l'ensemble mobile-friendly.

### Réalisations
- **Vue globale (persona manager)** : `pages/GlobalView.jsx` + données de flotte partagées `src/sites.js` (3 sites TelcoNet avec score/statut/légende/anomalies 7j/PM la plus proche/défaut principal ; MSC-10 aligné sur le score réel ~82). KPIs de flotte (score moyen, actifs totaux, anomalies 7j, PM la plus proche), bandeau d'insight sur le site le plus à risque, et **classement des sites du plus à risque au plus sain** (cartes cliquables).
- **Navigation globale ↔ site** dans `AppLayout` : l'app démarre en **vue globale** ; sélectionner un site (carte du classement ou menu du sélecteur, nouvelle entrée « Vue globale » en tête) **personnalise** l'app sur ce site (nav par-site affichée, pages routées). Un site non branché (MSC-03/BSC-07) affiche « intégration à venir » + bouton retour à la vue globale. La nav par-site est masquée en vue globale.
- **Mobile-friendly** : une seule build responsive sert desktop et mobile. En-tête compacté (padding réduit, libellé du thème masqué < 480px via `.hide-sm`, titre tronqué), sélecteur de langue conservé. Vérifié à 375px : aucun débordement horizontal (vue globale, pages par-site, table d'anomalies qui défile dans son conteneur), en-tête sans débordement.

### Validation
- Navigateur : landing en vue globale (flotte 80/100, classement BSC-07 69 → MSC-10 82 → MSC-03 88) ; clic MSC-10 → page Santé du site réelle (81.6) + nav par-site ; retour « Vue globale » via le sélecteur → nav masquée, KPIs. Mobile 375px : 0 débordement, thème en icône seule, table défilante. Aucune erreur console.
- `npm test` **9/9**. `npm run build` OK.

### Note
« Version mobile » = design responsive unique (pas de second codebase) : le même build s'adapte au téléphone et au desktop (standard, évite la double maintenance).

---

## Session 3 — 2026-07-26 (suite) — Navigation en tiroir, multi-sites, i18n FR/EN

**Demandes** : (1) supprimer la section « Planning calculé » de Maintenance ; (2) sélecteur de site cliquable + autres sites ; (3) navigation en menu latéral déroulant (3 lignes en haut à gauche, toutes tailles) ; (4) bouton thème déplacé en haut à droite ; (5) sélecteur de langue EN/FR à côté du thème.

### Réalisations
- **Maintenance** : section « Planning calculé » (table) supprimée. L'édition/suppression est préservée : clic sur un marqueur PM du **calendrier** → charge la PM dans le formulaire (mode édition) ; bouton Supprimer ajouté au formulaire. Marqueurs PM rendus en boutons accessibles.
- **Sélecteur de site** : bouton bas-de-sidebar transformé en menu déroulant (`role=listbox`) — 3 sites du réseau TelcoNet (MSC-10 branché ; MSC-03, BSC-07 en démo). Choisir un site non branché affiche un écran « intégration à venir » plutôt que des données trompeuses.
- **Navigation en tiroir sur toutes tailles** : la sidebar est masquée par défaut et révélée par le bouton 3 lignes (toujours visible, haut-gauche) ; backdrop + fermeture au clic sur un lien / Échap. `isMobile`/matchMedia supprimé (comportement unifié). Contenu principal pleine largeur.
- **Thème en haut à droite** : bascule clair/sombre déplacée du bas de sidebar vers le header (droite), à côté du sélecteur de langue.
- **i18n FR/EN** (`src/i18n.jsx`) : `LangProvider` + `useLang()` (`t`, `lang`, `setLang`, `locale`), dictionnaire FR/EN, persistance `localStorage` (`datapulse-lang`, défaut FR), `<html lang>` synchronisé. Segmented control FR|EN dans le header. Toutes les chaînes d'interface traduites (chrome, 5 pages, composants StatusBadge/EquipmentCard/ApiState/AnomalyHistogram/PMCalendar) ; dates via `toLocaleString(locale)` ; noms de mois/jours du calendrier dérivés de la locale. Le contenu servi par l'API (libellés de familles, messages de rappels) reste dans sa langue source — i18n backend hors périmètre.

### Validation
- Navigateur : nav masquée par défaut + hamburger l'ouvre (desktop) ; FR↔EN traduit nav/titres/thème et persiste ; site → BSC-07 affiche l'écran « integration coming soon » ; Maintenance sans table, clic calendrier → édition (form « Modifier PM-0004 », Supprimer présent). Aucune erreur console.
- `npm test` **9/9** (tests de pages enveloppés dans `LangProvider` via `renderWithLang` ; test Maintenance réécrit pour la nouvelle UI). `npm run build` OK.

### En suspens
- Contenu API non traduit (nécessiterait un i18n backend). Sites MSC-03/BSC-07 sans données (backend mono-site). Plan « Vue globale » (manager) esquissé à partir du design (fleet score, classement des sites, KPI) — reste à implémenter.

---

## Session 3 — 2026-07-26 (suite) — Bascule de thème clair/sombre

**Demande** : bouton mode clair/sombre dans la sidebar, même gabarit que le bouton de sélection de site (bas-gauche).

### Réalisations
- `hooks/useTheme.js` : état thème (défaut sombre), applique `data-theme` sur `<html>` et persiste dans `localStorage` (`datapulse-theme`). Effet de bord dans un `useEffect` (pas dans l'updater) — **StrictMode double-invoque les updaters**, ce qui annulait la bascule dans une première version.
- `index.html` : script inline qui pose `data-theme` depuis localStorage **avant** le rendu React (anti-flash).
- `AppLayout` : bas de sidebar refait en deux contrôles au même gabarit (bordure, rayon 12, `var(--surface)`) — indicateur de site « MSC-10 / UC3 · Site actif » (pastille pulse) + bouton bascule thème (icône soleil/lune, label « Mode sombre/clair », `aria-label`/`aria-pressed`). Reprend le pattern du site-switcher du mockup Identity v2.
- Tokens `[data-theme="light"]` déjà présents (Phase 2) — désormais atteignables.

### Validation
- Navigateur : bascule OK (fond sombre↔blanc, texte, label), persistée au reload sans flash. Contraste **thème clair AA** : texte 19:1, muted 4.89:1, accent 4.5:1.
- `npm test` **9/9** (+3 tests `useTheme` : défaut sombre, bascule+persistance, reprise du choix). `npm run build` OK.

---

## Session 3 — 2026-07-26 (suite) — Phase 10 (polish)

**Phases couvertes** : Phase 10 — parcours de test, responsive mobile, accessibilité. Livrable DSIP4 laissé de côté (bloqué par la validation Scenario 6, Phase 8).

### Réalisations
- **Responsive** : sidebar convertie en **tiroir mobile** sous 768px (`AppLayout` : hamburger avec `aria-expanded`, backdrop cliquable, fermeture au clic sur un lien et via Échap). Positionnement fixe piloté par CSS (`index.css`), translation d'ouverture pilotée en **inline depuis React** via un état `isMobile` (`matchMedia`) — choix délibéré après un long faux-bug (voir ci-dessous). `main` en padding responsive (`.app-main`). Vérifié : **0 débordement horizontal** sur les 5 pages à 375px, `main` pleine largeur.
- **Accessibilité** : titre de page en `<h1>` (les titres de Panel étaient déjà `<h2>`) → hiérarchie h1→h2 ; `:focus-visible` déjà global ; tous les interactifs (22) ont un nom accessible ; aria sur tiroir et badge ; contrastes audités **AA** (texte 18:1, muted 6.7–7.5:1, statuts 4.7–8.5:1, accent 4.3:1 réservé UI/large).
- **Tests parcours critiques** : mise en place **Vitest + Testing Library + jsdom** (config dans `vite.config.js`, `src/test/setup.js`, script `npm test`). 6 tests / 3 fichiers : planifier une PM (submit → payload → reload), consulter+acquitter une anomalie (+ filtre sévérité), lire le forecast (rendu chart + sous-scores + changement d'horizon). API mockée (niveau intégration).

### Piège rencontré (consigné en mémoire)
Le tiroir semblait cassé (transform figé à `translateX(-100%)` même ouvert, survivant à un override inline). Cause réelle : **le Browser pane non affiché met le compositeur en pause → les transitions CSS gèlent à leur valeur de départ**, donc `getComputedStyle`/`getBoundingClientRect` renvoient l'état pré-transition. Le code était correct depuis le début (prouvé en désactivant la transition : `left:0` à l'ouverture). Mémoire créée : `browser-pane-paused-compositor`.

### Validation
- Front : `npm test` **6/6 verts** ; `npm run build` OK (55 modules). Responsive/a11y vérifiés au navigateur (mesures DOM ; dev server propre relancé — l'ancien serveur 5173 d'une session précédente servait du code périmé).
- Backend inchangé (29/29 de la sous-session précédente).
- ⚠️ Node absent du PATH shell mais présent (`C:\Program Files\nodejs`) ; `.claude/launch.json` (gitignoré) pointe le chemin complet de node pour lancer Vite via le Browser pane.

### En suspens
- Livrable DSIP4 + Phases 8 (branchement pipeline réel, validation Scenario 6) et 9 (UPS/generators) — toujours bloquées par le code pipeline + accès DB.
- Option : e2e navigateur complet (Playwright) au-delà des tests d'intégration actuels.
- Toggle thème clair (tokens prêts, pas de bouton) — a11y contrastes du thème clair non audités (non atteignable dans l'UI).

---

## Session 3 — 2026-07-26 (suite) — Phase 8 (seam ML)

**Phases couvertes** : Phase 8, premier pas — le *seam* d'intégration mock ↔ live. Le branchement du vrai pipeline reste **bloqué** (voir En suspens).

### Constat de blocage
Revue complète du repo : **aucun code ML, notebook, artefact de modèle ni donnée** présent (seul `app/ml/README.md` en placeholder ; `.env` vide ; pas de `docs/`). Le pipeline validé vit dans le notebook Databricks, hors repo, et l'accès à PostgreSQL `datacenter_ops` n'est pas configuré. Impossible de brancher le pipeline réel ou de lancer la validation Scenario 6 sans ces éléments — et hors de question de fabriquer un faux pipeline « validé » (règle projet + honnêteté sur les perfs). Question posée à l'utilisateur (non répondue) ; défaut retenu : construire le seam, qui ne dépend d'aucun input externe.

### Réalisations (comportement inchangé, mock par défaut)
- **Aiguillage `DATA_SOURCE` (mock|live)** dans `config.py` ; `app/providers.py` = point unique de choix de source, lu à chaud. Les routes (`health`, `anomalies`, `reminders`) appellent désormais `providers.*`, plus jamais `mocks/` ni `ml/` directement.
- **Contrat `ml/`** : `ml/anomalies.py` (`raw_episodes`, `window_days`) et `ml/health.py` (`get_overview`, `get_forecast`) — stubs levant `NotImplementedError`, docstrings mappées aux étapes validées (préprocessing/segmentation/hystérésis/seuils Tukey). `ml/README.md` = guide d'intégration.
- **Agrégations partagées** (`services/anomaly_aggregation.py`) sorties de `mocks/anomalies.py` : surcharge de statut, filtrage, `compute_stats`, `compute_histogram` — identiques quelle que soit la source. `mocks/anomalies.py` réduit à la production d'épisodes bruts (`raw_episodes`, `window_days`).
- **Lecture DB documentée** (`db/queries.py`) : `read_temp_humidity` / `read_scada_logs` / `read_ups_events` / `read_scenario_6_labels` (pandas via `engine.py`). ⚠️ NON TESTÉ, noms de colonnes à confirmer (pas d'accès DB).
- **501 explicite** : handler `NotImplementedError → 501` dans `main.py` — `DATA_SOURCE=live` avant branchement renvoie un message clair, pas un 500 opaque. `.env.example` documente `DATA_SOURCE`.

### Validation
- `pytest tests/` : **29/29 verts** (3 nouveaux : défaut = mock ; `DATA_SOURCE=live` → 501 sur les 6 endpoints ; retour au mock OK). Refactor agrégations vérifié sans régression via les tests d'anomalies existants.
- **Vérif live** (uvicorn) : mock → 200 ; `DATA_SOURCE=live` → 501 avec message « fournir le pipeline ML validé » sur health + anomalies.

### En suspens (bloquant pour la suite de Phase 8)
- **Fournir le code du pipeline validé** (notebook/.py) → à adapter dans `ml/` (ne pas réécrire).
- **Accès DB** `datacenter_ops` (credentials dans `.env`, base joignable depuis la machine) → tester `db/queries.py`, confirmer les schémas.
- `scenario_6_label` + validation finale ; scoring composite santé ; sémantique forecast °C↔score (à trancher au branchement, cf. note session Phase 5).

---

## Session 3 — 2026-07-26 (suite) — Phases 6 & 7

**Phases couvertes** : Phase 6 (Maintenance) + Phase 7 (Reminders) — terminées.

### Réalisations
- **Phase 6 — Backend** : `PATCH /api/maintenance/schedule/{id}` (remplace les champs + recalcule la prochaine PM, 404 si inconnu) et `DELETE /api/maintenance/schedule/{id}` (204, 404 si inconnu) dans `services/maintenance.py`.
- **Phase 6 — Frontend** : `components/PMCalendar.jsx` — calendrier mensuel navigable (‹ / Aujourd'hui / ›), marqueurs PM par jour colorés par urgence (retard→critique, ≤7j→watch, sinon accent), élément dominant en haut de page. Liste « Planning calculé » enrichie de boutons Éditer (recharge la PM dans le formulaire, qui bascule en mode mise à jour) / Supprimer. Formulaire compact conservé, sert création + édition.
- **Phase 7 — Backend** : rappels dérivés inchangés, mais action utilisateur persistée (`db/tables.ReminderAction`, `services/reminders.py`) : `POST /{id}/acknowledge` (masque), `POST /{id}/snooze` (masque jusqu'à `snoozed_until`, `hours` borné 0<h≤720), `GET /count`. `apply_actions` filtre la liste dérivée à la lecture. Fix : SQLite ne conserve pas le fuseau → `snoozed_until` relu réinterprété en UTC.
- **Phase 7 — Frontend** : page Reminders avec Acquitter + Reporter (1 h / 1 j / 7 j) par carte ; badge compteur dans la nav (`AppLayout`, `GET /count` rechargé à chaque changement de page). `api/client.js` : `updateMaintenance`, `deleteMaintenance`, `remindersCount`, `acknowledgeReminder`, `snoozeReminder` ; `request()` gère 204 (corps vide).

### Validation
- `pytest tests/` : **26/26 verts** (7 nouveaux : update recalcule/persiste, delete retire, 404 update+delete, count=liste, acquittement retire + compteur, snooze masque, bornes `hours` 422). Fixture d'isolation étendue à `ReminderAction`.
- **Vérif backend live** (uvicorn) : PM créée→éditée (next_pm recalculé)→supprimée (204), 404 sur inconnu ; reminders count 4→3 après acquittement, snooze masque le rappel.
- **Vérif navigateur** (Vite + backend) — Node retrouvé à `C:\Program Files\nodejs` (absent du PATH shell, pas de la machine ; `.claude/launch.json` ajouté). `npm run build` OK (55 modules). Calendrier : navigation Août affiche GEN-01/STULZ-03/UPS-01 aux bonnes dates ; Reminders : acquittement retire la carte, badge nav passe à 3 ; page Anomalies (Phase 5) rendue et conforme (histogramme, répartitions, filtres, actions).

### En suspens
- Badge nav rechargé au changement de page seulement : après un acquittement *sur* la page Reminders, le badge reste à jour dès la navigation suivante (pas de rafraîchissement live intra-page — acceptable, amélioration possible via contexte partagé ou polling).
- Reste : Phase 8 (intégration pipeline ML réel + validation Scenario 6), Phase 9 (UPS/generators), Phase 10 (e2e, responsive, a11y, livrable). Le pattern « action utilisateur persistée surchargeant/filtrant une donnée dérivée » est désormais établi sur maintenance, anomalies et reminders.

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
=======
## Session 4 — 2026-07-25

**Phases couvertes** : Phase 5 (Anomaly Detection) — terminée. Phases 3 et 4 cochées rétroactivement (livrées en Session 2).

### Réalisations
- **Backend — premiers endpoints d'écriture** :
  - `GET /api/anomalies/histogram?bucket=day|week|month` → intervalles contigus (creux inclus) avec `total` / `alert` / `critical`.
  - `PATCH /api/anomalies/{id}` `{status}` → met à jour le statut d'un épisode, 404 si inconnu, 422 si statut invalide.
  - Modèles `HistogramBucket`, `HistogramBin`, `HistogramResponse`, `StatusUpdate`.
- **Frontend** :
  - `AnomalyHistogram` (barres empilées par sévérité, sélecteur jour/semaine/mois, tooltip, légende).
  - Actions **Acquitter / Résoudre** par ligne, désactivées selon le statut courant, avec rechargement et remontée d'erreur.
  - `SegmentedControl` extrait et réutilisé par le sélecteur d'horizon du Forecast (les deux contrôles étaient dupliqués).

### Décisions
- **Intervalles vides renvoyés à zéro** par l'histogramme : sans eux, une période calme serait indiscernable d'une absence de mesure.
- **État des statuts en mémoire** côté mock (repart à zéro au redémarrage du serveur) — la persistance viendra avec le branchement réel en Phase 8.
- Granularité **semaine** nettement plus lisible que **jour** sur une fenêtre de 60 jours ; `jour` reste la valeur par défaut, conformément à la ROADMAP.

### Validation
- `pytest tests/` : **20/20 verts** (14 existants + 6 nouveaux : histogramme × 3 granularités, bucket invalide → 422, mise à jour de statut, 404/422).
- `npm run build` OK.
- Vérification navigateur dans les deux thèmes : histogramme (jour + semaine), et aller-retour complet d'une action « Résoudre » (PATCH → rechargement → ligne passée à « Résolue », boutons désactivés).

### En suspens
- Phase 6 (calendrier dominant + édition/suppression) et Phase 7 (snooze/acquittement des rappels, badge compteur) : mêmes prérequis backend — endpoints d'écriture `DELETE`/`PATCH` sur `maintenance/calendar` et `reminders`.
- Code-splitting du bundle Recharts (662 kB).

---

## Session 3 — 2026-07-25

**Phases couvertes** : consolidation design (hors ROADMAP, demandée avant les phases 5–7) — thème clair/sombre + passage des graphiques sur Recharts.

### Réalisations
- **Thème clair/sombre complet** : `ThemeContext` (provider + hook), bouton bascule dans la topbar, persistance `localStorage`, suivi de `prefers-color-scheme` tant que l'utilisateur n'a pas choisi, `color-scheme` posé sur `<html>` pour aligner les contrôles natifs (date picker, select, scrollbars).
- **Tokens light complétés** : accents et statuts re-échelonnés pour le fond blanc (les pas clairs ne tenaient pas 4.5:1 en 10px), + tokens dataviz par thème (`--chart-grid`, `--chart-axis`, `--chart-track`).
- **Recharts** : `TrendChart` reconstruit (ComposedChart — bande de confiance empilée limitée à la prévision, historique plein / prévision pointillée, légende, tooltip custom, marqueurs de franchissement) ; `HealthGauge` en RadialBarChart ; nouveau `DistributionChart` (barres horizontales) branché sur `by_type` / `by_severity` / `by_direction` déjà exposés par `/api/anomalies/stats`.

### Décisions
- **Répartitions en teinte unique + libellés d'axe** plutôt qu'une palette catégorielle : blue/violet échouent le seuil de séparation (ΔE 11.1 en vision normale, 1.9 en protanopie). Les couleurs de statut réservées ne servent que pour la sévérité, qui *est* un statut.
- **Domaine Y explicite** sur le forecast : l'auto-domaine de Recharts repart de 0 à cause de la bande empilée et écrasait la courbe.
- **`react-router-dom` maintenu en 7.18.x** malgré 2 alertes `npm audit` (GHSA-qwww-vcr4-c8h2, CSRF en mode RSC) : aucune version corrigée n'existe au-dessus, et redescendre en 7.11 expose 14 advisories. L'app est une SPA cliente sans RSC ni server actions — non exposée. À revoir quand un correctif sort.
- Statuts light vérifiés : healthy #0F7A57 (5.33:1), watch #9A6510 (4.95:1), critical #C1443B (5.05:1) sur blanc.

### Validation
- `npm run build` OK. Bundle 657 kB (Recharts) — avertissement de taille Vite, code-splitting à envisager en Phase 10.
- Vérification navigateur des 5 pages **dans les deux thèmes**.

### En suspens
- Reprise de la ROADMAP en Phase 5 (Anomalies) : histogramme temporel + actions acquitter/résoudre — nécessite d'abord les endpoints d'écriture côté backend (`PATCH /api/anomalies/{id}`, snooze reminders, suppression d'entrée calendrier), absents de la Phase 1.
- Code-splitting du bundle Recharts.
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a

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
