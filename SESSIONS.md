# SESSIONS.md — Journal des sessions DataPulse

Retrace ce qui a été fait à chaque session de travail avec Claude Code. Une entrée par session : date, phases ROADMAP couvertes, réalisations, décisions, points en suspens. **À mettre à jour à la fin de chaque session.**

---

## Session 11 — 2026-09-22 — Planification du déploiement portfolio (aucun code modifié)

**Demande** : repartir de `f64f054` (« handover check ») et bâtir un plan pour rendre le projet déployable, en tenant compte du volume des données, de la confidentialité, et du fait qu'il servira de projet portfolio devant montrer le travail ML / data science. Session consacrée à la planification ; l'exécution viendra ensuite.

### Constats de l'audit
- Les 4 commits de déploiement du 15/08 (`86e30f0` → `039b573`), annulés par le `reset` du 01/09, sont **intacts sur `origin/main`** et leur contenu est encore dans l'index. Travail réutilisable : bundle 633 → 148 Mo, export gold 40 Mo → 1,1 Mo, détection de base en lecture seule, front + API sur un seul domaine.
- **L'historique git porte le nom du client** (28 commits + `SESSIONS.md`) : anonymiser l'arbre de travail ne suffit pas pour un repo public.
- **L'export gold casse la source live des anomalies** : `ml/anomalies.py` lit `silver_repo.span_days()` / `last_ts()` sur `th_clean`, table supprimée par `export_gold`. Masqué par `ANOMALIES_SOURCE=mock`, deviendrait un 500 en production.
- **pandas est sur le chemin de requête** (`gold_repo.read_health_hourly`) : ~90 Mo et ~1 s de démarrage à froid pour une seule ligne de logique pandas réelle.
- Aucune fuite à ce jour : aucun CSV/XLSX brut ni `.env` jamais commité (vérifié sur tout l'historique).

### Décisions
- **Confidentialité** : anonymisation complète (code, UI, docs, tests **et historique git** via `filter-repo` vers un nouveau repo public) **+ recalage temporel du gold**, qui règle d'un coup la datation mai 2026 et le rattachement au site réel.
- **Le recalage débloque le tout-live** : `ANOMALIES_SOURCE=mock` n'a plus de raison d'être, les 388 épisodes réels redeviennent récents → les 5 pages servent de la sortie de pipeline réelle. Contrepartie assumée : bandeau + `data_shift_days` exposé, une démo recalée doit le dire.
- **Hébergement** : Vercel (front + fonction Python, un seul projet) **+ Postgres managé** pour l'état applicatif — les 6 routes d'écriture ne peuvent pas vivre sur `/tmp` dans une démo publique.
- **Vitrine ML** : page « Méthode » dans l'application + README portfolio, alimentés par une doc de fond des choix DS/ML.
- **`SESSIONS.md` est gardé dans le repo public, anonymisé** : c'est la seule trace du *pourquoi* des arbitrages, et la source principale de `docs/ml-decisions.md`.
- Le déploiement Vercel du 15/08 ayant été supprimé, son erreur n'est plus consultable → on repart d'un déploiement neuf avec vérification `vercel dev` du routage `/api/*` (suspect n°1).

### Réalisations
- `docs/ml-decisions.md` (nouveau) : pourquoi ces choix DS/ML — problématique et personas → contraintes de données → décisions d'EDA (déduplication, replis capteur, seuil 125 s et segmentation, fenêtres 12/36/78 par ACF, seuils Tukey directionnels, hystérésis, bronze fidèle) → choix des modèles (HMM 6 états, IsolationForest, score pondéré non appris, filtre « HMM + franchissement réel », XGBoost delta top 20) avec les alternatives écartées et les chiffres honnêtes → ce qui est prouvé vs ce qui ne l'est pas.
- `docs/deployment-plan.md` (nouveau) : plan en 6 phases (récupération, confidentialité, données/recalage, Postgres, Vercel, vitrine) avec lexique d'anonymisation validé, cases à cocher, risques et parades. ~6-7 jours estimés.

### Phase 0 exécutée (même session)
- **0.1** — Branche `deploy-attempt-v1` créée sur `origin/main` (039b573) : les 4 commits annulés y sont figés et consultables. Arbre ramené à `f64f054` par `git reset --hard`, après sauvegarde de ce qui n'existait nulle part ailleurs : `docs/ml-decisions.md`, `docs/deployment-plan.md`, l'entrée SESSIONS ci-dessus, le réglage local du proxy Vite (`127.0.0.1:8000`) et l'export `datapulse_gold.db` (1,1 Mo, replacé dans `backend/data/`, ignoré par git à ce commit). **85 tests verts** sur la base restaurée.
- **0.2** — `.gitignore` nettoyé des lignes `CLAUDE.md`, `ROADMAP.md`, `SESSIONS.md` et `docs` : sans effet sur ces fichiers déjà suivis, elles piégeaient en revanche tout nouveau fichier de `docs/`.
- **Constat** : les 4 commits annulés ne portaient pas que du déploiement, mais aussi une **mise à jour de fond de la documentation**. Le retour à `f64f054` a donc restauré des docs **périmées** (`ml-data-integration.md` et `app/ml/README.md` annoncent encore health/forecast en 501 et les étapes F/I « à venir »), et `handover/current-state.md` n'existe **que** sur la branche. À récupérer depuis `deploy-attempt-v1` en Phases 5.3 et 6, pas à réécrire. Autre conséquence : la doc de la branche est en anglais, l'arbre restauré en français — langue unique à trancher en Phase 6.

### Phase 1.1–1.2 exécutée (même session)
- **1.1** — Lexique validé. La table de correspondance réelle vit dans `.anonymization-map.local.md`, **gitignoré** : publiée, elle dés-anonymiserait le dépôt d'un coup d'œil. Le plan de déploiement ne décrit donc que les valeurs d'arrivée.
- **1.2** — 76 remplacements sur 31 fichiers (frontend, backend, tests, docs, README/ROADMAP/CLAUDE), plus les identifiants de site du frontend et la liste des six autres villes du fichier 2022.
- **Conservés car non identifiants** : `MSC 10` / `MSC10` (terme télécom générique — et c'est la chaîne sur laquelle filtrent l'ETL et le package livré, donc aucun filtre n'est cassé), les noms des fichiers bruts, les marques d'équipement, et `DSIP4 — UC3` (décision : garder, le cadre académique explique les contraintes).
- **Point dur résolu** : le pipeline reconstruit les messages UPS avec un préfixe qui doit reproduire **à l'identique** celui du fichier de référence livré, sinon le golden test de fidélité compare des chaînes différentes. Ce préfixe porte le nom réel du site → il devient `Settings.raw_ups_message_prefix`, défaut neutre, surchargé par `RAW_UPS_MESSAGE_PREFIX` dans `backend/.env` (gitignoré). Golden tests toujours à 100 % ici ; valeur neutre dans le dépôt public, où ces tests sont de toute façon skippés faute de données brutes.
- **Validation** : **85 tests backend verts**, fidélité incluse. Frontend : 3 échecs / 10 succès — **préexistants**, vérifié en rejouant la suite sur l'état d'avant anonymisation (contexte react-router nul, libellé « Climatisation » introuvable).

### Phases 1.5 et 2 exécutées (même session)
- **1.5** — Garde-fou `tests/test_no_client_identifiers.py` : lit les termes interdits dans `.anonymization-map.local.md` (gitignoré) et échoue si l'un d'eux réapparaît ; *skippé* sans ce fichier, donc inoffensif dans le dépôt public. Vérifié **par un cas négatif** (fichier piège → échec), et son message ne réimprime pas le terme, seulement son rang.
- **Incident** : la seconde passe du script d'anonymisation a touché deux cibles qu'elle n'aurait pas dû — sa propre table de correspondance (reconstruite) et le worktree de la session de fond, `.claude/worktrees/…` (restauré fichier par fichier depuis `git show HEAD:`, en préservant les 4 fichiers de leur travail). Exclusions ajoutées au script.
- **2.1/2.2** — `export_gold.py` récupéré depuis `deploy-attempt-v1`, plus la table **`gold_meta`** (fin de couverture, étendue, décalage) : l'API borne désormais ses fenêtres sans toucher au silver, ce qui **corrige le 500 en production** qui serait apparu au passage des anomalies en live.
- **2.3** — `--shift-to-now` : translation unique de toutes les colonnes temporelles, ancrée sur le **dernier score horaire** (+135,5 j). La fin de couverture, qui le suit de 8,4 j, est bornée à l'instant de l'export pour ne pas ouvrir de fenêtre sur le futur. Les statuts d'épisode sont recalculés contre cette borne (no-op sans recalage).
- **2.4/2.5** — Démo en tout-live (`ANOMALIES_SOURCE=mock` retiré) ; `data_shift_days` exposé par `/api/health/overview`. Résultat servi : `updated_at` à l'heure courante, prévision repartant de maintenant, 388 épisodes récents. KPI anomalies : 24 h = 0, 7 j = 1, 30 j = 77, 90 j = 143 — le zéro à 24 h est **exact**, pas un bug.
- **2.6** — 6 tests (`tests/test_export_gold.py`). Suite complète : **94 tests verts**.
- **Piège vécu** : pointer l'API locale sur l'export versionné pour valider la lecture l'a repassé en journal WAL — le test `test_versioned_gold_export_is_not_in_wal_mode` l'a détecté, l'export a été régénéré.

### Phases 3 (code) et 5.1 exécutées (même session)
- **3.1/3.2** — `APP_DB_URL` : `app/db/app_db.py` résout l'URL par `make_url`, normalise `postgres://` → `postgresql+psycopg2` (encore émis par des hébergeurs, refusé par SQLAlchemy ≥ 1.4) et conserve les options TLS. Aucune dépendance nouvelle (`psycopg2-binary` déjà déclaré). Moteur PostgreSQL en **NullPool** (un pool ne survit pas à l'invocation serverless), `pool_pre_ping` (conteneur réutilisé ↔ connexion coupée côté hébergeur) et `connect_timeout=10`.
- **3.5** — 6 tests (`tests/test_app_db.py`) : résolution, normalisation des deux schémas, absence de pool, non-fuitage du mot de passe dans `str(url)`. Le test d'aller-retour réel s'active dès que `TEST_APP_DB_URL` est fournie.
- **3.3 en attente** : il manque la chaîne de connexion Neon (projet Neon dédié), à poser dans `backend/.env`. Le CLI Neon fourni dans le script d'onboarding n'est **pas** nécessaire — il outille un projet Node/TS (`neon.ts`, `neon deploy`, MCP, skills) ; notre backend est Python et n'a besoin que de l'URL, de préférence l'endpoint avec pool.
- **5.1** — `app/etl/export_model_cards.py` → `frontend/src/data/model-cards.json` : chiffres lus dans les `metadata.json` / `thresholds.json` et les volumes réels des couches, prose éditoriale dans le script. 5 tests, dont un garde-fou qui échoue si le JSON committé devient périmé après réentraînement.
- Suite complète (hors fidélité) : **98 verts, 1 skippé** (le test Postgres).

### Phase 3.3 exécutée — 2026-09-25
- Première tentative en échec : la ligne `APP_DB_URL` posée dans `backend/.env` reprenait l'exemple à trous (`<host>-pooler.<region>…`), d'où un `could not translate host name`. Utile malgré tout — tout le chemin de code était validé jusqu'à la résolution DNS.
- Connexion établie avec la vraie chaîne : **PostgreSQL 18.6**, endpoint **avec pool**, base `neondb`, moteur en `NullPool`.
- Schéma créé (`pm_schedules`, `anomaly_actions`, `reminder_actions`) par `init_db()`, idempotent. Aller-retour relu par une **nouvelle** connexion : la donnée est côté serveur, pas dans un cache de processus. Test d'intégration `test_app_db.py` : **7/7**, plus aucun skip.
- Routes d'écriture exercées à travers l'API contre Neon : PM planifiée (201) puis supprimée (204), anomalie acquittée (200), rappel reporté (204). Deux URL de ma sonde étaient fausses (`/schedules` au lieu de `/calendar`, `/schedule/{id}` au singulier) — le contrat de l'API est bien `PM-0004` en identifiant public. Écritures de sonde purgées, 4 PM de démonstration conservées.
- **À savoir** : en local, `data_shift_days` vaut `None` et les dates restent en mai 2026 — l'application lit la base analytique complète, non recalée. Le recalage ne concerne que l'export servi en déploiement.

### Plannings en lecture seule (3.6) — 2026-09-25
- **Décision** : sur l'instance publique, les plannings de PM sont **figés** (`PM_READ_ONLY=1`) plutôt que remis à zéro périodiquement. Sans authentification, la saisie d'un visiteur modifierait durablement le calendrier partagé par tous.
- **Backend** : garde `forbid_when_read_only` sur les trois routes d'écriture → **403** avec un message explicite ; la consultation est intacte. Nouvelle route `GET /api/config` (source des données, plannings figés) — volontairement sans rien sur la base ni l'hébergement, et un test le vérifie.
- **Frontend** : la configuration est lue **une fois au niveau de l'application** (`src/config.jsx`, `ConfigProvider` + `useConfig`), pas page par page. Premier essai via `useApi(api.config)` dans la page : il cassait 2 tests qui mockent `api` sans cette route (`fn is not a function`). Le provider est meilleur sur les deux plans — le bandeau de démonstration s'en servira aussi, et une page rendue isolément reçoit une valeur par défaut permissive, donc aucun mock à ajouter. Formulaire désactivé par `fieldset disabled` + note : la fonctionnalité reste visible sans être un piège.
- **Bug attrapé au passage** : `APP_DB_URL` primant sur `APP_DB_PATH`, la suite de tests écrivait dans la base Neon de la démo — et la fixture `reset_user_actions` y purgeait les actions utilisateur après chaque test. La conftest neutralise désormais `APP_DB_URL`. Aucun dégât : les seules écritures ont été créées puis supprimées par les tests eux-mêmes.
- Frontend : retour au niveau de référence (3 échecs préexistants / 10 succès), build vert.

### Relecture de SESSIONS.md (1.3) — 2026-09-25
Lecture intégrale des 712 lignes, en cherchant ce que le lexique ne couvre pas : personnes, chemins machine, URL, adresses, tiers, indices géographiques. **Trois trouvailles**, toutes corrigées :
1. **Noms de villes seuls** — le script d'anonymisation n'avait remplacé que les libellés complets des sites ; les villes employées seules subsistaient dans 4 phrases du journal (7 occurrences). Ce sont elles qui rattachaient le réseau à un pays. Remplacées par les codes de site.
2. **Nom de personne** — un nom servait de placeholder au champ « technicien » et de donnée de test (5 emplacements, frontend et backend). Remplacé par un libellé i18n (« Nom du technicien » / « Technician name ») côté interface et par des initiales neutres côté tests.
3. **Identifiant du projet d'hébergement de base** cité dans ce journal — retiré, remplacé par une mention générique.

Rien d'autre : aucun email, aucune URL externe, aucune adresse, aucun chemin machine nominatif (seuls un chemin d'installation Node standard et `127.0.0.1`, génériques), aucun tiers nommé.

**Le garde-fou a appris deux choses au passage.**
- La recherche en **sous-chaîne** est inutilisable pour les noms courts : un nom de ville de la liste se trouve au milieu d'un participe présent très courant, ce qui faisait échouer le test sur un fichier parfaitement propre. Le test lit désormais **deux blocs** — sous-chaîne pour les identifiants composés (un souligné n'offre pas de limite de mot), mot entier pour les noms courts. Les deux modes sont vérifiés par des fichiers pièges.
- Un garde-fou **ne doit pas citer les termes qu'il interdit** : ma docstring donnait l'exemple en clair, et le test s'est signalé lui-même.

**Risque résiduel assumé** : le journal décrit le contexte (opérateur télécom, data center, parc d'équipements, cadre académique conservé sur décision). Aucun identifiant ne subsiste, mais le recoupement de ces éléments reste possible pour un lecteur déterminé — c'est le prix de garder un journal qui explique le *pourquoi*.

### Commits + réécriture d'historique (1.4) — 2026-09-25
- **5 commits thématiques** (anonymisation · export gold et recalage · PostgreSQL et lecture seule · model cards · documentation), **sans co-signature Claude** sur décision. Le premier lot a été refait : `main.py` y enregistrait la route `/api/config` dont le module arrivait au lot suivant — le commit n'aurait pas démarré.
- **Constat en vérifiant l'accès GitHub** : `gh` est installé et authentifié (un push passerait sans rien demander), et l'historique portait **deux identités** — un email académique en `.dz`, qui réintroduisait à chaque commit le pays que l'anonymisation venait de retirer, et le **nom complet + email personnel d'une co-autrice**. Réécrits : `users.noreply` du compte pour l'un (le nom reste), `DataPulse Team` pour l'autre (option retenue par l'utilisateur).
- **`filter-repo`** sur un clone, 28 commits : `--replace-text` **et** `--replace-message`, les messages de commit portant eux aussi des identifiants (« Sélecteur de site déroulant (… branché ; …/… en démo) »). Règles ordonnées du plus spécifique au plus général — sinon le nom seul mangeait le préfixe du libellé complet — et bornées par des limites de mot pour les noms courts.
- **Vérifications** : zéro occurrence de chaque terme (contenu et messages, tout l'historique), deux auteurs neutres, et le **tree final identique au local au hash près** — seule l'histoire a changé. Un ancien commit relu à la main se lit de façon cohérente (`id: 'msc10'`, `MSC-10`, `TelcoNet`), pas comme un texte expurgé.
- **En attente** : le `git push` vers `datapulse-portfolio`, laissé à l'accord explicite. Le clone réécrit vit dans le scratchpad de session, remote déjà configuré.

### En suspens
- **0.3 tranché** : le dépôt public cible sera **`datapulse-portfolio`** (nouveau dépôt, à créer sur GitHub ; `datapulse-app` reste privé et intact).
- **Phase 1 restant** : le seul push vers le dépôt public (1.4 faite) (`filter-repo` → `datapulse-portfolio`, créé) — 1.4 attend 1.3, un terme trouvé hors lexique obligeant à rejouer la réécriture d'historique.
- **3 tests frontend cassés, préexistants** : à corriger avant la CI de la Phase 6.
- Rien n'est committé : `.gitignore`, `SESSIONS.md`, `frontend/vite.config.js` modifiés et les deux nouveaux documents `docs/` non suivis.

---

## Session 10 — 2026-07-28 (suite) — Phase 8 F+I : scoring santé réel + prévision (notebook `health_scores.ipynb`)

**Demande** : extraire du notebook `health_scores.ipynb` (dossier `datapulse`, hors dépôt) tout ce qu'il faut pour rendre le score de santé et sa prévision opérationnels dans l'application, et faire descendre les CSV utilisés par le notebook dans les couches bronze / silver / gold.

### Le parcours des CSV du notebook
Les deux fichiers que lit le notebook existaient déjà comme **références de fidélité**, mais rien ne les faisait descendre jusqu'au gold. C'est fait :

| Fichier notebook | Bronze | Silver | Gold |
|---|---|---|---|
| `temp_humid_last.csv` | `raw_temp_humidity` (137 970) | `th_clean` (107 047) | `health_score_hourly` |
| `msc10_combined_ups.csv` | `raw_scada_log` (3 274) | **`scada_clean`** (2 569, nouveau) | `health_score_hourly` |
| `site_health_scores.csv` (sortie) | — | — | `health_score_hourly` (2 137 h), `health_score`, `forecast_point` |

`scada_clean` est produit par LEUR `clean_and_dedupe` : il reproduit `msc10_combined_ups.csv` **à la ligne près** (2 569 = 2 569, déjà couvert par le golden test d'ingestion).

### Réalisations
- **`ml/health_score/`** (maths pures, aucune I/O) : `config.py` (poids v1.0, mots-clés, dates de PM, seuils), `features.py` (helpers + features horaires env/énergie/batterie), `scoring.py` (risques de base → calibration énergie → score global, driver, statut, priorité, action conseillée), `forecasting.py` (features de prévision, entraînement, déroulé récursif).
- **Stockage** : `silver.scada_clean` et `gold.health_score_hourly` (+ repositories) ; `gold_repo` sait désormais écrire/lire l'instantané `health_score` et les `forecast_point`.
- **ETL** : `transform.transform_scada`, `etl/score.py`, `etl/forecast.py`, `etl/run.py` (orchestration bronze → silver → gold, idempotente).
- **Source live** : `ml/health.py` implémenté — les 5 routes santé lisent le gold, plus aucun `NotImplementedError` (501 uniquement si le gold est vide, avec la marche à suivre).
- **Correctif** `config.py` : `.env` était cherché en chemin relatif alors qu'`uvicorn --app-dir backend` démarre à la racine — `DATA_SOURCE` dans `backend/.env` n'était jamais lu.

### Décisions
- **Fidélité prouvée, pas supposée** : `test_scoring_reproduces_notebook_output` compare le portage à `site_health_scores_v1_0.csv` sur les entrées livrées → **égalité exacte** (< 1e-6) sur les 4 scores. Le fichier de sortie du notebook a été déposé en référence (`app/ml/data/raw/reference/`, gitignoré).
- **Lectures capteur invraisemblables = données manquantes** : l'export brut encode le repli capteur par une humidité à 0-11 % (le fichier livré, lui, porte NaN). Comptées comme mesures, elles faisaient exploser l'écart-type horaire et, via l'échelle p95, déréglaient le terme de variabilité sur toute la série. Bornes de plausibilité posées dans `config` (humidité ≥ 15 %, température ≥ 5 °C ; le fichier livré descend à 23,5 % et 17,9 °C). Écart résiduel sur le score global : **0,45 point en moyenne**, dû au millésime de l'export — énergie et batterie sont bit-exactes.
- **Le modèle de prévision est choisi par les données** : persistance / linéaire / gradient boosting sont entraînés, le meilleur sur la **validation** est retenu. Sur ces données c'est la **persistance** (MAE val. 6,44 vs 6,61 linéaire vs 11,03 GB) — conforme au notebook, où aucun modèle ne bat la persistance (test : 6,00 vs 6,18 / 10,55 / 16,14). Servir un modèle moins bon que « le score reste où il est » aurait été une régression déguisée en modèle.
- **Au-delà de +6 h** (pas validé du modèle), la trajectoire vient d'un **déroulé récursif à conditions inchangées** ; seuls le calendrier et le risque de PM évoluent, et la bande s'élargit en √pas à partir de l'écart-type des résidus de test.
- **Franchissement de seuil** = passage sous un seuil **non encore franchi** (borne basse de la bande). Un seuil déjà franchi est l'état courant, pas une prévision : le signaler à chaque point noyait le signal (24 « franchissements » sur 24 points).
- **Domaine → `family`** : `environmental→stulz`, `energy→socomec`, `battery→yanan`, l'ordre attendu par le frontend, qui libelle ces cartes **par domaine** (`FAMILY_DOMAIN_LABEL_KEY`). `family` n'est qu'une clé technique — aucun frontend touché, libellés corrects à l'écran.
- **Prévision par sous-score** : projection à niveau constant avec bande élargie, faute de modèle validé par domaine. Une bande large qui dit « on ne sait pas » vaut mieux qu'une courbe inventée.

### Validation
- `pytest` : **78/78 verts** (65 + 13 nouveaux), dont le golden de fidélité au notebook.
- Pipeline complet réel (`python -m app.etl.run --train`) : bronze 137 970 + 3 274 → silver 107 047 + 2 569 → gold 388 épisodes, 2 137 heures scorées, 4 lignes d'instantané, 164 points de prévision.
- Navigateur en `DATA_SOURCE=live` : **Aperçu** (global 69,9 · Env 90,0 · Énergie 68,4 · Batterie 54,2 · prochaine panne = Batterie · anomalies `SALLE_SWITCH`), **Santé du site** (score, 3 domaines, courbes 7/30/90 j), **Prévision** (pannes par domaine, courbe globale historique+prévision continue, 1 franchissement, 3 sous-scores). Aucune erreur console.

### Correctif de suivi — déploiement Vercel monoprojet (front + API)

**Demande** : déployer le backend sur Vercel ou ailleurs, et quoi mettre dans le projet pour qu'il parle au frontend Vercel.

**Conseil donné, choix utilisateur = tout sur Vercel.** Les deux arguments contre étaient : (1) six routes d'écriture couvrant 3 pages sur 5 (planification PM, acquittement d'anomalie, cloche) réussissent puis oublient sur un système de fichiers éphémère ; (2) l'ETL ne peut pas tourner sur Vercel — il lui faut le stack ML, justement exclu du bundle, et un accès en écriture. Le gold y reste donc un instantané exporté à la main. L'utilisateur a tranché pour la démo de consultation, déjà préparée.

**Ajouté** :
- `api/index.py` — point d'entrée ASGI. Met `backend/` sur le `sys.path` et fixe les deux chemins de base en **absolu** via `setdefault` (un chemin relatif serait résolu contre le répertoire de travail de la fonction, non garanti) ; le tableau de bord Vercel reste prioritaire.
- `vercel.json` — build Vite + réécritures `/api/*` vers la fonction, le reste vers `index.html` (routage SPA).
- `requirements.txt` racine — un simple `-r backend/requirements.txt`, lu par le runtime Python de Vercel.
- `.vercelignore` corrigé : il excluait `backend/data/` **entier**, donc il aurait supprimé le gold du déploiement. Passé en `backend/data/*` + exception sur l'export.

Front et API sur le même domaine → les appels relatifs `fetch('/api/...')` continuent de fonctionner : **aucun CORS, aucune modification de `client.js`** (20 sites d'appel intacts).

**Piège attrapé de justesse.** Après avoir testé `api/index.py` en local, le gold versionné est repassé en **journal WAL** : le fichier est inscriptible sur un poste de dev, donc le pragma s'applique — et une base en WAL est illisible sur le disque en lecture seule du déploiement. Le fichier étant binaire, ça ne se voit pas dans un diff et tout continue de marcher en local. J'allais expédier exactement le bug contre lequel j'avais conçu la lecture seule. Garde-fou ajouté : `test_versioned_gold_export_is_not_in_wal_mode`, qui vise le fichier versionné par son emplacement canonique et non par `settings.analytics_db_path` — sinon la conftest le redirige vers un dossier temporaire et le test se skippe silencieusement.

**Vérifié** : point d'entrée importé comme le fait Vercel → 6 routes à 200, santé 69,9 lue depuis le gold ; simulation des motifs `.vercelignore` (gold inclus, base 39 Mo exclue, sous-paquets ML exclus, lecteurs gold inclus) ; `npm run build` OK ; 87 tests verts.

**Non vérifiable en local** : le chemin exact que la réécriture Vercel transmet à la fonction. Les routers FastAPI sont déjà montés sous `/api`, donc ça fonctionne si Vercel transmet le chemin d'origine — son comportement documenté. Procédure de vérification et solution de repli notées dans `handover/deployment.md` §4b.

### Correctif de suivi — bundle de déploiement (633 Mo → ~190 Mo estimés)

**Demande** : réduire la taille pour passer sous la limite Vercel (500 Mo), piste évoquée = sortir la base bronze du dépôt.

**La piste ne pouvait pas marcher** : `backend/data/` est gitignoré depuis le début, aucune base n'est suivie, et le dépôt entier pèse **150 Ko empaquetés**. Les 633 Mo sont le bundle de la **fonction**, c'est-à-dire les dépendances Python installées — pas le contenu du dépôt.

**Où passaient les 633 Mo** (mesuré en local, 486 Mo de `site-packages`) : scipy 115 · xgboost 98 · pandas 67 · sklearn 44 · numpy 55 · sqlalchemy 19. Or `import app.main` ne charge **que pandas et numpy** — sklearn, xgboost, scipy, hmmlearn, joblib, openpyxl et psycopg2 ne sont importés que par `app/etl/detect.py` et les sous-paquets `app/ml/{environmental,alarm_anomaly,health_score}`, tous hors du chemin de requête. Environ **330 Mo de dépendances pour du code jamais exécuté en production**.

**Correctif** — la séparation existait déjà dans l'architecture, elle n'était juste pas reflétée dans les dépendances :
- `requirements.txt` réduit à l'API servie (fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy, pandas, numpy) ;
- `requirements-etl.txt` (nouveau) : sklearn épinglé, hmmlearn, xgboost, joblib, openpyxl, psycopg2 ;
- `requirements-dev.txt` (nouveau) : ETL + pytest/httpx ;
- `.vercelignore` (nouveau) : exclut `app/etl/`, les trois sous-paquets ML, `app/ml/models/` (6,6 Mo d'artefacts), les tests et la doc. **`app/ml/anomalies.py` et `app/ml/health.py` restent** — malgré leur emplacement, ce sont de simples lecteurs du gold appelés par `providers.py`.
- Instructions d'installation mises à jour (`README.md`, `backend/README.md`, `handover/setup-guide.md`, `handover/deployment.md`) : `requirements-dev.txt` pour développer, `requirements.txt` seul pour déployer.

**Vérifié par simulation** : arborescence déployée reconstituée (code excluant l'ETL/ML → 215 Ko), `import app.main` OK, et les 5 routes répondent 200 — y compris en `DATA_SOURCE=live` sur le vrai gold (santé 69,9 · 388 épisodes · 56 points de prévision). Estimation du bundle : **~148 Mo en local**, soit ~190 Mo en roues Linux.

**Stockage — décision prise : démo Vercel en lecture seule.**
- `app/etl/export_gold.py` (nouveau) : extrait une base **gold seule** de l'analytique — 39,09 Mo → **1,05 Mo** (2 137 heures scorées, 388 épisodes, 164 points de prévision, 4 sous-scores), figée en journal `DELETE`.
- `.gitignore` : `backend/data/` devient `backend/data/*` + exception `!backend/data/datapulse_gold.db` — git ne sait pas ré-inclure un fichier dont le dossier parent est exclu.
- `app/storage/analytics_db.py` : détection d'une base non inscriptible (`is_read_only()`) → ni pragma WAL ni `create_all`. Les deux sont des **écritures** ; une base en WAL ne peut d'ailleurs pas s'ouvrir en lecture sur un disque non inscriptible (il lui faut créer ses `-wal`/`-shm`). Tentative initiale avec l'URI `mode=ro` abandonnée : elle échoue sous Windows (`unable to open database file`), et elle est inutile — le journal `DELETE` posé à l'export suffit.
- Variables de déploiement documentées (`.env.example`, `handover/deployment.md` §4 bis) : `ANALYTICS_DB_PATH` sur le gold versionné, `APP_DB_PATH=/tmp/datapulse.db`.

**Vérifié en conditions réelles** : arborescence déployée + gold passé en lecture seule (`chmod a-w`) → les **10 routes** répondent 200, santé 69,9 sur données réelles, prévision 56 points avec 1 franchissement, et l'écriture d'une PM renvoie 201 (sur `/tmp`). Test de non-régression ajouté (`test_read_only_analytics_db_is_served_without_writing_to_it`).

**Limite assumée** : l'état applicatif étant sur `/tmp`, planifier une PM ou acquitter une anomalie **réussit mais ne persiste pas**. La consultation, elle, est complète.

### Correctif de suivi — source par domaine (anomalies en mock pour la démo)

**Demande** : anomalies en mock, le reste en live, pour la démo.

`DATA_SOURCE` pilotait les deux domaines d'un bloc. Ajout d'une **dérogation par domaine** dans `config.py` : `ANOMALIES_SOURCE` et `HEALTH_SOURCE`, non renseignées par défaut → le domaine suit `DATA_SOURCE`. Un seul bouton dans le cas général, la granularité ne se paie que si on la demande. `providers.py` lit les propriétés résolues ; aucune route touchée.

`backend/.env` (local, gitignoré) : `DATA_SOURCE=live` + `ANOMALIES_SOURCE=mock`. Vérifié : anomalies = 30 épisodes mockés (STULZ-xx, dates autour de maintenant, fenêtre 24 h non vide, 1 ouverte / 1 acquittée / 28 résolues) et santé toujours réelle (global 69,9 · Env 90,0 · Énergie 68,4 · Batterie 54,2, dernière heure 10/05/2026).

**Au passage** : `conftest.py` crée désormais les tables au chargement au lieu de compter sur la fixture `client`. La fixture autouse écrit dans la base applicative après *chaque* test, y compris ceux qui ne montent pas le client — lancer un fichier de tests seul échouait sur des tables absentes selon l'ordre alphabétique.

### Correctif de suivi — passage à XGBoost delta (notebook mis à jour)

**Retour utilisateur** : « la persistance ne prédit rien, elle donne l'ancienne valeur — passe au modèle XGBoost trouvé dans le notebook. » Le notebook a été mis à jour entre-temps (113 → 224 cellules) : la version que j'avais portée ne contenait que des modèles prédisant le **niveau**, la nouvelle ajoute la section qui règle le problème.

**Ce qui change tout — la cible** : `target_health_change_6h = target_health_6h - overall_site_health`. La santé globale se comporte comme un AR(1) ; prédire le niveau revient à demander à des arbres d'extrapoler une tendance, ce qu'ils ne savent pas faire. Sur le **delta**, la persistance n'est plus qu'un « delta = 0 » et le modèle n'apprend que l'écart. Reconstruction : `clip(santé_courante + delta, 0, 100)`.

**Porté** :
- `ml/health_score/forecast_features.py` (nouveau) : ~1 200 features dynamiques sur 22 variables sources — retards, variations, vitesses, moyennes/écarts/min/max/étendues glissantes, **pentes** glissantes (forme fermée des moindres carrés), accélération, compteurs de dégradation continue, interactions entre sous-systèmes.
- `forecasting.py` réécrit : XGBoost « large » pour classer les features, puis réentraînement sur les **top 20 / 50 / 100 / 200** avec N choisi sur la **validation** → **top 20** retenu (MAE val. 5,80 vs 6,19-6,28 pour les autres ; le notebook obtient 5,79 sur les mêmes tailles — portage fidèle).
- Variante **pondérée** sur les heures de chute (poids 1,25 / 1,75 / 2,50 selon l'amplitude) conservée dans les métriques : meilleure sur les chutes, moins bonne en MAE globale — donc pas le modèle servi.
- Dépendance ajoutée : `xgboost` (3.3.0) dans `requirements.txt`. L'ETL seul l'utilise ; l'API ne charge aucun modèle.

**Amortissement du déroulé récursif** (décision propre à l'application, absente du notebook qui ne fait pas de multi-pas) : le modèle n'est validé qu'à +6 h. Réappliqué tel quel, son delta se compose et la trajectoire 7 j **saturait à 100/100** — annoncer « site parfait pendant une semaine » est un pire mensonge qu'une droite plate. Chaque delta au-delà du premier pas est donc réduit géométriquement (`RECURSIVE_DELTA_DAMPING = 0.5`), ce qui borne l'excursion totale à ~2× le premier pas. Résultat servi : 69,9 → convergence vers 76,4 au lieu de 100.

**Écart honnête sur le test** : le notebook rapporte XGBoost top 20 à MAE 5,03 contre persistance 6,00 (+0,97). Sur notre gold : **6,085 contre 6,124 (+0,04)** ; sur les scores du notebook eux-mêmes, mon portage donne 5,70 contre 5,95 (+0,25) en retenant top 100. Les MAE de **validation** coïncident (5,80 vs 5,79), donc la méthode est fidèle ; l'écart au test vient du jeu de test lui-même (~316 heures, erreur à queue lourde) et de la divergence environnementale du millésime d'export déjà documentée. Le gain réel pour le produit n'est pas le dixième de MAE : c'est que **la courbe bouge enfin**, portée par un modèle.

### Correctif de suivi — fenêtre Anomalies vide

**Constat** : les KPI « 24 h / 7 j » de la page Anomalies affichaient 0 et le donut « Répartition par modèle » était vide, alors que le gold contient bien **388 épisodes** (`/api/anomalies/stats` et l'histogramme, non fenêtrés, les affichent).

**Cause** : `compute_window_stats` bornait la fenêtre à `datetime.now()`. L'export est figé — dernière lecture capteur le **18/05/2026**, dernier épisode le **09/05/2026** — soit ~72 jours avant la date du jour : la fenêtre tombait entièrement après la fin des données. Même mécanisme dans `etl/detect._status_for`, qui vieillissait les statuts contre l'horloge (388/388 « résolues » par construction).

**Correctif** : nouveau contrat `reference_now()` sur les deux sources d'anomalies (mock = `now`, live = **fin de la couverture silver**) ; `WindowStats` porte désormais `reference_at`, affiché dans le sous-titre du panneau (« 24 h — jusqu'au 18/05/2026 19:19 (fin des données observées) »), et le donut affiche un état vide explicite au lieu d'une légende orpheline.

Ancrage volontairement sur la **fin de la couverture capteur**, pas sur le dernier épisode : une fenêtre calée sur le dernier épisode contiendrait toujours au moins une anomalie par construction et ne mesurerait plus rien. Conséquence assumée : 24 h et 7 j restent à **0** — les 9 derniers jours d'observation sont réellement sans anomalie — mais le panneau dit maintenant « rien à signaler sur la période » au lieu de paraître cassé.

### En suspens
- **Déploiement Vercel : les écritures ne persistent pas** (choix assumé, démo de consultation). Si la remise doit permettre de planifier une PM ou d'acquitter une anomalie durablement, deux voies : Postgres hébergé pour l'état applicatif (Neon/Supabase — les repositories isolent déjà le stockage, cf. `docs/data-architecture.md` §3), ou hébergeur à disque persistant (Railway/Render/Fly) où l'architecture actuelle tourne sans modification.
- **Le gold versionné est un instantané** : `backend/data/datapulse_gold.db` doit être régénéré (`python -m app.etl.export_gold`) puis recommitté après chaque exécution du pipeline, sinon le déploiement sert des scores périmés.
- Gain au test mince (+0,04 MAE) face à la persistance, là où le notebook obtient +0,97. À revoir si l'écart environnemental du millésime d'export est résorbé (export brut aligné sur `temp_humid_last.csv`).
- Notebook cellules 192-222 non portées : pipeline v2, évaluation *walk-forward*, temps d'avance des alertes, score énergie+batterie 2022 pour validation inter-périodes, réglage Optuna. LightGBM (MAE test 5,025, à 0,007 d'XGBoost top 20) écarté pour ne pas ajouter une seconde dépendance de gradient boosting.
- `weight_version` v1.0 figée : le notebook a des curseurs de poids (ipywidgets) non exposés dans l'application ; `recalculate_health_scores` n'a pas été porté (pas de surface UI pour le piloter).
- Dates de PM en dur (`ENV_LAST_PM_DATE`, `ENERGY_LAST_PM_DATE`) — à brancher sur les plannings réels de `pm_schedules` (état applicatif) pour que le risque de PM suive les interventions saisies.
- Phase 8 H (temps réel/incrémental) toujours bloquée : pas de flux source.

---

## Session 9 — 2026-07-28 (suite) — Page Aperçu (dashboard site) + rappels en notifications

**Demande** : nouvel onglet « Aperçu » par site — score global + sous-scores (24h), prochaine panne prédite avec détails, aperçu des 5 dernières anomalies, prochaine maintenance + nombre cette semaine. Et changer la logique des rappels pour qu'ils apparaissent comme des notifications (cloche en haut à droite, popover) plutôt qu'une page dédiée.

### Constat de départ
Aucune donnée manquante : cette page agrège uniquement des endpoints déjà construits dans les sessions 5-8 (`health/overview`, `health/predicted-faults`, `anomalies`, `maintenance/calendar`, `reminders`). **Zéro changement backend** cette session — une première depuis le début de la finalisation UI/UX.

### Décision
- **Aperçu devient la page d'index** (`/`) du site — c'est un vrai dashboard de synthèse, pas un onglet parmi d'autres (cohérent avec la note Session 3 : « Page Aperçu dédiée, comme la référence »). Santé du site déplacée sur `/health` pour libérer `/`.
- **Prochaine panne prédite** : une seule (pas 3 cartes comme sur Prévision) — la plus proche dans le temps parmi les 3 familles, horizon 7 j (24h donnait trop souvent « aucune panne prévue », peu utile en aperçu).
- **Rappels** : page + route `/reminders` retirées de la navigation ; remplacées par `NotificationBell` (cloche + badge dans le header, popover avec actions acquitter/reporter). Le composant `Reminders.jsx` et l'endpoint `remindersCount` restent dans le code mais ne sont plus utilisés (cf. mémoire scope discipline — code mort conservé, pas supprimé).
- **Extraction DRY** (3ᵉ occurrence du même motif) : `components/KpiCard.jsx`, `components/DueBadge.jsx`, `components/DeltaTag.jsx`, `constants/domains.js`, `utils/maintenanceKpi.js` — Maintenance.jsx refactorisé pour les utiliser ; Site Health/Prévision **non touchées** (copies locales laissées telles quelles, déjà vérifiées, pour ne pas prendre de risque de régression sur du code livré).

### Réalisations
- Frontend uniquement : `pages/Overview.jsx` (nouveau), `components/NotificationBell.jsx` (nouveau, ferme au clic extérieur + Échap), `layout/AppLayout.jsx` (nav réordonnée, badge de rappels déplacé de la sidebar vers la cloche), `App.jsx` (routing : `/` → Overview, `/health` → Site Health, route `/reminders` retirée), i18n FR/EN (+`overview.*`, `nav.overview`, `layout.notifications`). `CLAUDE.md` mis à jour (architecture + specs Aperçu/Rappels).
- Test `Overview.test.jsx` ajouté (score, sous-scores, panne la plus proche retenue sur 2 candidates, anomalie récente, prochaine PM).

### Validation
- `npm run build` OK. Navigateur (backend live sur :8000, plus de processus fantôme — libéré côté utilisateur) : les 5 sections dans l'ordre demandé avec de vraies données ; cloche visible même en Vue globale ; popover ouvert → 4 rappels avec actions ; acquittement d'un rappel de maintenance → badge 4→3, entrée disparaît de la liste (revérifié en direct) ; clic en dehors → popover se ferme ; navigation Maintenance/Santé du site revérifiée après le refactor DRY, aucune régression visuelle. Aucune erreur console sur l'ensemble du parcours.
- `npm test` (vitest) : toujours cassé par le souci d'environnement préexistant (`html-encoding-sniffer`/ESM) — non lié au code, non revérifiable dans cet environnement.

### En suspens
- Les 5 pages « page par page » de la demande initiale sont maintenant **toutes finalisées** (Aperçu, Santé du site, Prévision, Anomalies, Maintenance). Reste ouvert : Phase 8 F (scoring santé réel, notebook non prêt) et l'intégration SCADA (`alarm_anomaly`) pour la dimension anomalies.
- `Reminders.jsx` et `api.remindersCount` non supprimés mais orphelins (plus référencés) — à nettoyer si confirmé définitivement inutile.

---

## Session 8 — 2026-07-28 (suite) — Finalisation UI/UX Maintenance (formulaire détaillé + calendrier cliquable)

**Demande** : formulaire « Planifier une PM » plus détaillé, placé **avant** le calendrier (inversion du spec CLAUDE.md §6 d'origine — décision produit assumée par l'utilisateur) ; calendrier cliquable pour voir le détail du jour et de la PM ; tout en haut, prochaine maintenance + nombre de maintenances cette semaine.

### Décision
- Champs additifs sur `ScheduleRequest`/`CalendarEntry` : `assigned_to` (technicien) et `notes`, tous deux optionnels — pas de nouvelle table, juste 2 colonnes nullable sur `pm_schedules` (état applicatif déjà en écriture utilisateur, migration triviale contrairement à la table gold de la session Anomalies).
- Champ équipement transformé en **sélecteur** (parc réel STULZ/SOCOMEC/YANAN) plutôt que texte libre — nouvel endpoint `GET /api/maintenance/equipment` (source `mocks/equipment.ALL_UNITS`, donnée réelle statique, pas un mock aléatoire).
- KPI « prochaine maintenance » et « cette semaine » **calculés côté frontend** à partir de `calendar.data` déjà chargé (tri par `days_remaining`, filtre 0–7 j) — aucune donnée supplémentaire à exposer côté API.
- Calendrier : chaque cellule de jour devient un bouton cliquable (accessible, `aria-label`) au lieu de seuls les marqueurs de PM ; sélectionner un jour affiche son détail dans un panneau dédié (toutes les PM du jour, avec notes/technicien si renseignés, actions Modifier/Supprimer). « Modifier » recharge le formulaire (repositionné en premier) et y scrolle.
- CLAUDE.md §6 mis à jour pour refléter le nouveau layout (le document décrivait encore l'ancien ordre « calendrier dominant, formulaire compact » ainsi qu'une liste « Planning calculé » déjà supprimée en Session 3).

### Réalisations
- Backend : `models/maintenance.py`, `db/tables.py` (colonnes `assigned_to`/`notes`), `services/maintenance.py`, `api/maintenance.py` (+`GET /equipment`). **Migration manuelle** de `backend/data/datapulse.db` (`pm_schedules`, 4 lignes) via `ALTER TABLE ... ADD COLUMN` (nullable, pas de valeur par défaut nécessaire). Tests +3 (détails optionnels/persistés, contrat du catalogue équipement).
- Frontend : `PMCalendar.jsx` réécrit (cellule de jour = bouton, prop `selectedDate`/`onDayClick` remplace `onSelect`) ; `Maintenance.jsx` réécrit — ordre KPI → formulaire (5 champs, équipement en select) → calendrier + panneau détail du jour. `api/client.js` (+`maintenanceEquipmentOptions`), i18n FR/EN étendu. `Maintenance.test.jsx` mis à jour (select au lieu de texte libre, nouveau test de sélection de jour — piège évité : le calendrier affiche le mois **courant réel**, pas une date fixe, donc le test construit sa date dynamiquement plutôt que de coder en dur un mois arbitraire).

### Validation
- `pytest backend/tests/` : **53/54** (même échec préexistant `openpyxl`, sans rapport).
- Navigateur (build + vérification bout-en-bout, backend réel sur :8000 — l'utilisateur a résolu le processus fantôme du port 8000 signalé en session précédente) : KPI correct (GEN-01 « Dans 7 j », 1 maintenance cette semaine), formulaire en premier avec sélecteur d'équipement peuplé (14 unités), navigation de mois testée, clic sur une cellule de jour → panneau détail (équipement, délai, dernière PM), bouton Modifier → formulaire pré-rempli (« Modifier PM-0004 », y compris période en semaines) et scrollé en vue. Aucune erreur console.

### En suspens
- Page Rappels reste à finaliser (dernière page de la demande « page par page »).
- `npm test` (vitest) non revérifié cette session — souci d'environnement préexistant sans rapport avec le code (cf. sessions précédentes).

---

## Session 7 — 2026-07-28 (suite) — Finalisation UI/UX Anomalies (KPI fenêtré + dimension de détection)

**Demande** : refonte de la page Anomalies — (1) total + tendance 24h/semaine, taux d'anomalies sur la fenêtre, famille la plus contributrice ; (2) pie chart du modèle générant le plus d'anomalies ; (3) distribution par dimension (environnement/SCADA) ; (4) distribution par sévérité ; (5) table de détail. Layout à concevoir, backend à vérifier/étendre si besoin.

### Constat de départ
Aucune des données demandées n'existait : `AnomalyStats` ne portait qu'un total **all-time** (pas de fenêtre 24h/7j, pas de tendance), `top_equipment` était une unité précise (pas une famille), et rien ne distinguait le **modèle de détection** à l'origine d'un épisode — notion pourtant déjà réelle dans le pipeline validé (`environmental` HMM vs `alarm_anomaly` IsolationForest SCADA, catégories UPS/CLIM/ENERGY, cf. CLAUDE.md §4).

### Décision
- Nouveau champ **additif** `AnomalyEpisode.dimension` (`environment`/`scada`, défaut `environment`) — décorrélé de la famille d'équipement (les deux modèles peuvent en principe toucher le même équipement, ex. CLIM via alarme SCADA). Seul `environment` existe réellement à ce jour (SCADA/`alarm_anomaly` non branché, cf. mémoire `phase8-state`) ; le mock illustre les deux pour la démo.
- Nouveau `family_of(equipment)` (services, indépendant de la source) pour dériver stulz/socomec/yanan depuis l'identifiant brut (y compris `SALLE_SWITCH` → stulz).
- Nouvel endpoint `GET /api/anomalies/window-stats?window=24h|7d` (total, tendance vs période précédente de même durée, taux, famille top, répartition par dimension) — sert à la fois le KPI (1) et le pie chart (2)/la distribution (3), un seul fetch partagé.
- **Portée volontairement réduite aux 5 éléments demandés** : l'histogramme temporel (jour/semaine/mois) et les répartitions par type/direction/statut de la page précédente ont été retirés (cohérent avec le retour utilisateur de la session Site Health : ne pas garder de sections non demandées). `components/AnomalyHistogram.jsx` n'est plus utilisé mais pas supprimé (facilement réintégrable si souhaité).
- Familles affichées avec le libellé « domaine » (Environnement/Énergie/Batterie) plutôt que STULZ/SOCOMEC/YANAN, cohérent avec la préférence exprimée sur Forecast dans la session précédente.

### Réalisations
- Backend : `models/anomalies.py` (+`AnomalyDimension`, `AnomalyWindow`, `WindowStats`), `mocks/anomalies.py` (dimension par équipement), `services/anomaly_aggregation.py` (+`family_of`, `compute_window_stats` — bug corrigé en cours de route : comparaison naïve/aware entre mock (tz-aware) et gold live (naïf), normalisée via un helper `_naive`), `providers.py`, `api/anomalies.py` (`GET /window-stats`). `storage/schema/gold.py` + `storage/repositories/gold_repo.py` : colonne `dimension` (défaut `environment`) ; **migration manuelle** de la base gold réelle existante (`backend/data/datapulse_analytics.db`, 388 épisodes) via `ALTER TABLE ... ADD COLUMN dimension TEXT DEFAULT 'environment'` (évite un ré-ingestion complète qui aurait buté sur `openpyxl` absent pour la partie SCADA du backfill). `etl/detect.py` explicite `dimension=environment`. Tests étendus (+4 cas).
- Frontend : `Anomalies.jsx` réécrit dans l'ordre demandé — KPI fenêtré (sélecteur 24h/7j partagé), pie chart Recharts, distribution par dimension, distribution par sévérité (inchangée, all-time), table + filtres + actions (inchangés). `api/client.js` (+`anomalyWindowStats`), i18n FR/EN (+overview/window/pie/dimension/family). `Anomalies.test.jsx` mis à jour (mock `anomalyWindowStats` remplace `anomalyHistogram`, +1 test sur le rechargement au changement de fenêtre).

### Validation
- `pytest backend/tests/` : **50/51** (même échec préexistant `openpyxl`, sans rapport). Vérifié séparément en **live** (`DATA_SOURCE=live`, vraie base migrée) : `/window-stats` répond sans erreur pour 24h et 7j (0 résultat — le jeu de données réel s'arrête en mai 2026, cohérent avec un pipeline batch historique, pas un flux temps réel jusqu'à « aujourd'hui »).
- Navigateur (build + vérification bout-en-bout) : KPI 24h→7j vérifié (total 1→4, taux 1.70%→2.85%, famille Environnement ×1→×4), pie chart + distribution par dimension cohérents (100 % Environnemental/HMM sur les données mock actuelles — SOCOMEC n'est pas apparu dans l'échantillon de fenêtre, comportement attendu vu le volume). Aucune erreur console.
- ⚠️ **Contournement de vérification** : un processus backend orphelin sur le port 8000 (probablement issu d'un `preview_start` antérieur dans cette session) s'est révélé injoignable par tous les outils disponibles (Bash/PowerShell/WMI/tasklist/WSL) tout en occupant réellement le port (`WinError 10048` confirmé) — code périmé (routes manquantes → 405 au lieu de 200). Contourné en pointant temporairement `vite.config.js` vers un port 8001 contrôlé le temps de la vérification, puis reverté (`git diff` confirme aucun changement résiduel).

### En suspens
- Page Maintenance / Rappels restent à finaliser (dernières pages de la demande « page par page »).
- Port 8000 potentiellement occupé par un processus fantôme non identifiable — si le démarrage du backend échoue avec « address already in use », un redémarrage de la machine est probablement nécessaire (aucun outil disponible ne l'a détecté).
- `npm test` (vitest) toujours cassé par le souci d'environnement préexistant (`html-encoding-sniffer`/ESM) — non revérifié cette session, sans rapport avec le code.
- Distribution par sévérité (4) reste all-time (non fenêtrée) — cohérent avec la demande littérale (fenêtre mentionnée seulement pour 1 et 2), à reconsidérer si l'utilisateur veut l'aligner sur la fenêtre 24h/7j.

---

## Session 5 — 2026-07-28 — Finalisation UI/UX Santé du site (branchée sur l'API)

**Demande** : finaliser le frontend page par page (UI/UX + branchement backend réel), en commençant par Santé du site : score global (%, statut, diff dernière mesure) en haut à gauche, sous-scores (environnement/énergie/batterie, diff + statut) en haut à droite, puis évolution du score global, puis évolution des sous-scores.

### Constat de départ
`pages/SiteHealth.jsx` était **100 % mocké côté frontend** (`siteHealthData.js`), seule page à ne pas utiliser `useApi`/`api.healthOverview()`. Le contrat backend (`HealthOverview`) n'exposait que des sous-scores **par famille d'équipement** (STULZ/SOCOMEC/YANAN, consommés par Forecast) — aucune décomposition par domaine (environnement/énergie/batterie), aucune valeur précédente pour un delta, aucun historique pour un graphique d'évolution.

### Décision
Étendre le contrat `HealthOverview` de façon **additive** (les sous-scores par famille et la page Forecast restent inchangés) plutôt que détourner le champ existant :
- `HealthOverview.previous_score` (delta du score global) + `domain_scores: list[DomainScore]` (environment/energy/battery, chacun avec `score`/`status`/`previous_score`/`note`).
- Nouvel endpoint `GET /api/health/history?range=7d|30d|90d` → série quotidienne `global_score` + les 3 domaines, pour les deux graphiques d'évolution.
- Poids domaine → score global : environment 40 % / energy 35 % / battery 25 % (mock, cf. `mocks/health.py`). Seuils de statut unifiés à 82/68 (mêmes seuils que la référence de design), corrige au passage un bug du mock (statut global ne passait jamais en "critical").
- `ml/health.py` : stub `get_history()` ajouté + docstring mise à jour (contrat Phase 8 F, toujours non branché).

### Réalisations
- Backend : `models/health.py`, `mocks/health.py`, `ml/health.py`, `providers.py`, `api/health.py` mis à jour ; tests `test_health.py` étendus (domain_scores + statuts + `/history` 3 fenêtres + validation 422).
- Frontend : `SiteHealth.jsx` réécrit pour consommer `api.healthOverview()` + `api.healthHistory(range)` via `useApi`/`ApiState` (plus aucune donnée inventée) ; sélecteur de fenêtre 7j/30j/90j partagé par les deux graphiques d'évolution. `siteHealthData.js` supprimé (mock devenu inutile). i18n FR/EN étendu (`vsLast`, `rangeLabel`, `d7/d30/d90`, `domainEnvironment/domainEnergy/domainBattery`).
- `.claude/launch.json` créé (backend uvicorn + frontend vite) pour la vérification navigateur.
- **Retour utilisateur (même session)** : suppression des sections « Détail des sous-scores » (jauges radiales, redondantes avec la carte sous-scores du hero) et « Par famille d'équipement » — la page se limite désormais au hero (score global + sous-scores domaine) et aux deux graphiques d'évolution. Composant `Gauge` local et import `EquipmentCard` retirés (code mort) ; clés i18n `detail`/`byFamily` retirées.

### Validation
- `pytest backend/tests/test_health.py` : **7/7 verts**. Suite complète backend : 44/45 (1 échec préexistant sans rapport, `test_ingestion_fidelity` — `openpyxl` absent de l'environnement Python utilisé pour la vérification).
- `npm run build` OK. Navigateur (backend live + Vite) : hero score global 79.7/100 « À surveiller » -0.6, 3 sous-scores domaine avec delta + statut, jauges détail, cartes famille (STULZ/SOCOMEC/YANAN inchangées), 2 graphiques d'évolution — sélecteur 7j/30j/90j vérifié fonctionnel (refetch confirmé sur le réseau, réaffiche 30 points 30/06→28/07). FR↔EN vérifié. Aucune erreur console.
- `npm test` (vitest) : échec d'environnement préexistant (`html-encoding-sniffer`/ESM, reproduit aussi sur le commit non modifié via `git stash`) — non lié à cette session.

### En suspens
- Pages Anomalies / Maintenance / Rappels : UI/UX à finaliser de la même manière (prochaines pages de la demande « page par page »).
- `npm test` cassé par un souci d'environnement (dépendance ESM/CommonJS de jsdom) — à investiguer indépendamment de l'UI.
- Décomposition par domaine actuellement mockée (poids 40/35/25 arbitraires) ; à reconsidérer si/quand la Phase 8 F (scoring composite réel) est débloquée.

---

## Session 6 — 2026-07-28 (suite) — Finalisation UI/UX Prévision (pannes prédites + prévision des sous-scores)

**Demande** : refonte de la page Prévision — (1) cards « prochaines pannes prédites » par sous-score (timing + sévérité) en premier, (2) chart Global Health Score en second, (3) prévision des sous-scores en troisième.

### Constat de départ
Le contrat backend ne portait aucune notion de « panne prédite » (timing/sévérité), ni de prévision par famille (seul le score *courant* par famille existait, via `HealthOverview.sub_scores`, sans dimension temporelle). Le forecast existant (`/api/health/forecast`) est le modèle **environnemental réel** (HMM, seuils Tukey 26,75/28,65 °C sur température salle switch) — à ne pas confondre avec un score 0-100 ; ses `threshold_crossings` sont en fait déjà la donnée de « prochaine panne » pour STULZ/climatisation.

### Décision
- Sous-scores Forecast restent **par famille d'équipement** (STULZ/SOCOMEC/YANAN), conformément à CLAUDE.md §6 — pas de bascule vers la taxonomie par domaine utilisée sur Site Health (les deux vues coexistent, cf. `HealthDomain` note dans `models/health.py`).
- Nouveau `PredictedFault` (family/label/predicted_at/severity/note) réutilise l'enum `Severity` (alert/critical) des anomalies plutôt que `HealthStatus` — sémantique « sévérité de panne » distincte de « statut de santé courant ». STULZ dérive du premier `threshold_crossing` du forecast réel ; SOCOMEC/YANAN sont mockés (aucune panne / alerte baseline) en attendant des modèles équivalents validés.
- Nouveau `SubScoreForecastResponse` (par famille, mêmes `ForecastPoint` que le forecast global) sur le même `ForecastHorizon` (24h/7j/30j) que le chart dominant — un seul sélecteur d'horizon partagé pour toute la page.

### Réalisations
- Backend : `models/health.py` (+`PredictedFault(s)`, `SubScoreSeries`, `SubScoreForecastResponse`), `mocks/health.py` (constantes famille factorisées `_FAMILY_LABEL/_SCORE/_STATUS/_TREND/_NOTE`, `get_predicted_faults`, `get_subscore_forecast`, seeds déterministes remplaçant `hash()`), `ml/health.py` (stubs + docstring), `providers.py`, `api/health.py` (`GET /predicted-faults`, `GET /forecast/sub-scores`). Tests étendus (10 nouveaux cas).
- Frontend : `Forecast.jsx` réécrit — section 1 cards « pannes prédites » (sévérité via `StatusBadge`, ou « aucune panne prévue » avec icône `CheckCircle2`) ; section 2 = chart existant inchangé (`TrendChart` + franchissements) ; section 3 = petits multiples `TrendChart` par famille (historique plein + prévision pointillée, réutilisation telle quelle du composant). `api/client.js` (+`predictedFaults`, `subScoreForecast`), i18n FR/EN (+`nextFault`, `nextFaultSub`, `noFaultPredicted`, `predictedAround`, `subScores` reformulé). `Forecast.test.jsx` mis à jour pour les nouveaux appels API (l'ancien `healthOverview` n'est plus utilisé sur cette page).

### Validation
- `pytest backend/tests/` : **57/58** (même échec préexistant `openpyxl`, sans rapport). `npm run build` OK.
- Navigateur (backend live + Vite) : 3 sections dans l'ordre demandé ; STULZ affiche une vraie alerte à 7j (9 franchissements, cohérent avec le message sous le chart) et « aucune panne prévue » à 24h (aucun franchissement sur cette fenêtre) ; SOCOMEC toujours sain ; YANAN alerte baseline. Sélecteur d'horizon partagé vérifié : un clic refetch les 3 endpoints (`forecast`, `predicted-faults`, `forecast/sub-scores`) avec le nouvel horizon. FR↔EN vérifié. Aucune erreur console.
- `npm test` (vitest) : toujours cassé par le même souci d'environnement préexistant (non lié).

### En suspens
- Pages Anomalies / Maintenance / Rappels restent à finaliser.
- SOCOMEC/YANAN predicted-faults et sub-score forecast sont mockés (pas de modèle de prévision validé pour ces familles, contrairement à l'environnemental) — à remplacer si des modèles équivalents sont livrés.

---

## Session 4 — 2026-07-27 — Architecture des données + pipeline livré + socle `storage/`

**Demande** : penser l'intégration des données (historique + temps réel) avant de
rebrancher Santé du site ; ne pas mélanger la donnée avec l'ETL. Puis analyse du
package `mlops-api` (modèles/train/preprocessing livrés) et démarrage.

### Réalisations
- **`docs/data-architecture.md`** : plan complet. Séparation à 3 axes **storage /
  etl / ml** ; couches **medallion bronze/silver/gold** (gold = miroir des modèles
  Pydantic) ; **3 fichiers SQLite** à écrivain unique (source CSV → `datapulse_analytics.db`
  écrit par l'ETL → `datapulse.db` écrit par l'API) ; batch + temps réel = un seul
  transform, deux déclencheurs (backfill / incrémental + watermark) ; API qui **lit
  le gold précalculé**. Décisions actées via questions : SQLite partout, serving gold.
- **Analyse `mlops-api`** (pipeline validé livré, hors notebook) : 2 modèles entraînés
  — `environmental` (HMM temp/hum, F1=0.83) et `alarm_anomaly` (IsolationForest SCADA,
  catégories UPS/CLIM/ENERGY) — + preprocessing pur, artefacts `.joblib`, sa propre API
  (non réutilisée), Docker, et `datapulse.db` (107 060 lignes temp/hum). **Décision :
  intégration en librairie** (leur `src/` → notre `ml/`).
- **Décisions produit appliquées** : granularité **par salle** (SALLE_SWITCH, pas par
  STULZ) ; **seuils livrés 26.75 / 28.65** (thresholds.json, split train) propagés
  partout (mocks/equipment.py, CLAUDE, README, i18n, docs) ; source = **exports CSV**
  (PostgreSQL non joignable — plateforme isolée) ; **Scenario 6 supprimé de toute la
  mémoire projet** (CLAUDE, ROADMAP, SESSIONS, docs, `db/queries.py`).
- **Étape A — socle `storage/`** (non-cassant, mock reste défaut) : `storage/analytics_db.py`
  (SQLite dédié, WAL, `URL.create()`, `init_analytics_db`), `storage/schema/` avec `Base`
  propre + **bronze** (`raw_temp_humidity`, `raw_scada_log`, `ingest_watermark`), **silver**
  (`th_clean`), **gold** (`anomaly_episode`, `health_score`, `forecast_point` — miroirs
  Pydantic). Câblé au lifespan FastAPI. `config.py` : `analytics_db_path`.

### Validation
- `pytest tests/` : **33/33 verts** (4 nouveaux `test_storage` : création des 7 tables
  des 3 couches, aller-retour bronze, reconstruction `AnomalyEpisode` depuis gold,
  silver + watermark). Seuils changés sans régression (constantes importées symboliquement).

### Étape B — faite (même session)
- `mlops-api` **vendorisé** dans `app/ml/` (`environmental`, `alarm_anomaly`, `models/`) :
  imports réécrits en `app.ml.*`, `MODELS_DIR` corrigé (`app/ml/models`), deps ajoutées
  (`hmmlearn`, `scikit-learn==1.9.0`, `openpyxl`). **Vérifié** : les 2 modèles chargent et
  prédisent (env : is_anomaly sur 100 lectures du CSV ; alarm : sur features d'exemple).
  `model_registry.py` copié mais non utilisé (glue de leur API ; import obsolète).

### Données brutes reçues + documentation (même session)
- **4 fichiers bruts fournis** et copiés dans `backend/app/ml/data/raw/` (gitignoré) :
  `temp_humid_msc10.csv` (140 077 lignes, latin-1, sans `ts`), `logs_msc10.xlsx`
  (2 250, en-tête ligne 1, SCADA 2026), `ups_socomec1_msc10_events.csv` (1 024, 1re
  ligne parasite), `alarmes_scada_2022.xlsx` (35 408 multi-sites → **2 664 MSC 10**).
  Inspectés (colonnes/volumes/pièges).
- **`docs/ml-data-integration.md`** créé : état réalisé (A+B) + inventaire des données
  + écarts brut↔entraînement à gérer en C/D (encodage latin-1, `ts` à reconstruire,
  en-têtes décalés, filtrage MSC 10, états A/D/Q/Acquittement, formats de date).

### Étape C — lecteurs bruts + fidélité (faits ; écriture bronze à venir)
- `app/etl/ingest/sources.py` : lecteurs normalisant les fichiers bruts (encodage
  latin-1, `ts` reconstruit, en-têtes décalés, filtrage MSC 10, mapping UPS miroir
  de `merge_ups_source`), réutilisant `clean_and_dedupe`/`dedupe_and_index` (jamais
  réimplémentés).
- **Golden tests** (`tests/test_ingestion_fidelity.py`, skippés si données absentes) :
  environnemental **99.95 % / 99.76 %** vs `temp_humid_last.csv` ; SCADA **100 % exact**
  vs `msc10_combined_ups.csv` (2569/2569, catégories 100 %). **35 tests verts.**
- **Découverte** (notebook fourni) : les **alarmes 2022 n'ont jamais servi au modèle**
  (format de date `M/J/AAAA h:mm AM/PM` → NaT → `dropna`). Combiné = 2026 (logs+UPS)
  uniquement ; notre ingestion l'exclut explicitement → même résultat. Documenté.
- Références copiées dans `app/ml/data/raw/reference/` (gitignoré) pour les tests.

### Étapes C (fin) & D — faites
- **C — écriture bronze** : `storage/repositories/{bronze_repo,silver_repo}` (contrat
  lecture/écriture, insertion en masse via `to_sql`, remplacement idempotent),
  `etl/ingest/backfill.py` (watermark). Backfill réel : `raw_temp_humidity`=**137 970**,
  `raw_scada_log`=**3 274**.
- **D — transform bronze→silver** : `etl/transform.py` réutilise `dedupe_and_index` +
  `add_segments` (package validé). Réel : `th_clean`=**107 047** lignes, **1 905 segments**
  (≈ 1904 validés dans CLAUDE.md) — forte confirmation de la fidélité de segmentation.
- Tests : `tests/test_etl.py` (backfill idempotent + watermark ; transform → segments).
  **37 tests verts.**

### Étape E — détection → épisodes → gold (faite)
- **Décision (via question)** : gold = **runs d'anomalie du HMM**, pas les épisodes
  hystérésis. Le run brut a montré **1383 épisodes dont 72 % en température normale**
  (HMM multivarié : anomalies humidité/contextuelles étiquetées de force en °C).
  → 2e décision : **filtrer sur franchissement réel de seuil température**.
- `etl/detect.py` : déroule le HMM (réutilise `compute_rolling_features` +
  `prepare_hmm_sequences` + scaler/hmm/anomalous_states) sur le silver, groupe les
  runs anormaux, ne garde que ceux franchissant un seuil Tukey livré, mappe →
  `AnomalyEpisode` (equipment=`SALLE_SWITCH`, direction/pic/sévérité dérivés de la
  température, type=`collective`, status par ancienneté). `gold_repo` (replace/read).
- Réel : **388 épisodes** (228 high / 160 low, 14 critical, pics 17.9–30.7 °C), **0**
  en température normale. Tests `test_detect.py` (filtre + gold round-trip). **41 verts.**
- ⚠️ Gold peuplé mais `DATA_SOURCE=mock` par défaut → l'API sert toujours les mocks
  tant que G n'a pas basculé `providers` en lecture gold.

### Étape G — anomalies en live (faite)
- `ml/anomalies.py` (source live) implémenté : **lit le gold** (`gold_repo.read_episodes`) ;
  `window_days` = étendue du silver (`silver_repo.span_days`). `providers` inchangé
  (le seam route déjà mock↔live). Aucun calcul sur le chemin de requête.
- Vérifié **en live** (`DATA_SOURCE=live`, vraie base) : `GET /api/anomalies`=200 avec
  **388 épisodes** ; stats total=388, taux 4,2 %, MTBA 11,1 h, alert 374/critical 14,
  high 228/low 160 ; histogramme 7 mois ; rappels dérivés OK. `health/overview` &
  `forecast` restent **501** (étape F). Surcharge de statut/actions utilisateur intacte.
- Tests hermétiques : `conftest` pose `ANALYTICS_DB_PATH` jetable (gold vide en test →
  réponses vides mais 200). `test_ml_seam` scindé (health 501 / anomalies 200). **42 verts.**

### Prochaines étapes (cf. ROADMAP Phase 8)
- **F** — health scores + forecast → gold (scoring composite à définir) puis source
  live health → retrait des 2 derniers 501. **I** — rebrancher Santé du site sur l'API.
- Anomalies **SCADA** (alarm_anomaly, forme ≠ AnomalyEpisode) + silver SCADA :
  capacité nouvelle à concevoir séparément. Anomalies **humidité** du HMM : flux à part éventuel.
- **À fournir par l'utilisateur** : les CSV bruts d'entraînement du modèle SCADA
  (`logs_msc10.csv`, `ALARMES SCADA 2022.xlsx`, `ups_clean.csv`).
- Repositories `storage/repositories/` (contrat lecture/écriture) : à écrire juste avant D/E.
- Table gold des anomalies d'alarmes SCADA (forme différente d'`AnomalyEpisode`) : à ajouter
  avec les CSV SCADA. Temps réel (H) différé (pas de flux live).

---

## Session 3 — 2026-07-26 (suite) — Refonte UI (Recharts / Lucide / Framer Motion)

**Demande** : rapprocher le dashboard du design de référence (captures + `DataPulse - Identity v2 (standalone).html`) : sidebar persistante slate foncé, canvas clair, cartes blanches surélevées, charts Recharts, icônes Lucide, animations Framer Motion.

### Réalisations
- **Référence** : `docs/ui-reference.md` (specs extraites du HTML + description des 10 captures) et dossier `docs/screenshots/` (à remplir avec les PNG). Données/couleurs exactes extraites du HTML : statuts feutrés **Sain #3FA69C · Surveillance #B8823E · Critique #C1443B**, seuils `≥82 / ≥68`, sous-scores pondérés (Env 87/30%, Énergie 81/25%, Batterie 66/25%, Alarmes 90/20% → **81**).
- **Librairies** : `recharts`, `lucide-react`, `framer-motion` installées.
- **Layout & profondeur** (global, toutes pages) : conteneur `flex flex-row`, **sidebar persistante** (desktop) en **slate foncé** (`--sidebar-*`, `#171C29`), tiroir sur mobile ≤768px ; canvas **gris clair `#F3F4F6`** ; cartes **blanches surélevées** (`--shadow-card`, `rounded-lg`). Thème **clair par défaut**. Icônes **Lucide** dans la nav + header ; horloge « SYNCHRONISÉ · HH:MM ».
- **Page Santé du site refaite** (`pages/SiteHealth.jsx` + `siteHealthData.js`) avec **Recharts** (courbe d'évolution multi-lignes 7j/30j/90j, barres de résumé des sous-scores colorées par statut, **jauges radiales** par sous-score, sparklines par famille) et **Framer Motion** (fade-in + slide-up à l'entrée, scale au survol). Données/couleurs exactes de la référence.

### Validation
- `npm run build` OK (2814 modules ; bundle ~243 KB gzip — Recharts/Framer). `npm test` **9/9** (tests useTheme mis à jour pour le défaut clair).
- Navigateur : sidebar `#171C29` persistante (position static, flex-row), canvas `#F3F4F6`, cartes blanches + ombre, **10 surfaces Recharts** rendues, couleurs de statut correctes (env teal / énergie or / batterie rouge), 10 cartes animées. Les 4 autres pages héritent du nouveau shell sans débordement.

### En suspens
- Conversion des pages **Forecast / Anomalies / Maintenance / Rappels** en Recharts + Lucide + Framer Motion (elles héritent déjà du nouveau layout/cartes mais gardent les charts SVG maison). Page « Aperçu » dédiée (comme la référence) optionnelle. Les captures PNG restent à déposer dans `docs/screenshots/`.

---

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

**Phases couvertes** : Phase 10 — parcours de test, responsive mobile, accessibilité. Livrable DSIP4 laissé de côté (bloqué par la Phase 8).

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
- Livrable DSIP4 + Phases 8 (branchement pipeline réel) et 9 (UPS/generators) — toujours bloquées par le code pipeline + accès données.
- Option : e2e navigateur complet (Playwright) au-delà des tests d'intégration actuels.
- Toggle thème clair (tokens prêts, pas de bouton) — a11y contrastes du thème clair non audités (non atteignable dans l'UI).

---

## Session 3 — 2026-07-26 (suite) — Phase 8 (seam ML)

**Phases couvertes** : Phase 8, premier pas — le *seam* d'intégration mock ↔ live. Le branchement du vrai pipeline reste **bloqué** (voir En suspens).

### Constat de blocage
Revue complète du repo : **aucun code ML, notebook, artefact de modèle ni donnée** présent (seul `app/ml/README.md` en placeholder ; `.env` vide ; pas de `docs/`). Le pipeline validé vit dans le notebook Databricks, hors repo, et l'accès à PostgreSQL `datacenter_ops` n'est pas configuré. Impossible de brancher le pipeline réel sans ces éléments — et hors de question de fabriquer un faux pipeline « validé » (règle projet + honnêteté sur les perfs). Question posée à l'utilisateur (non répondue) ; défaut retenu : construire le seam, qui ne dépend d'aucun input externe.

### Réalisations (comportement inchangé, mock par défaut)
- **Aiguillage `DATA_SOURCE` (mock|live)** dans `config.py` ; `app/providers.py` = point unique de choix de source, lu à chaud. Les routes (`health`, `anomalies`, `reminders`) appellent désormais `providers.*`, plus jamais `mocks/` ni `ml/` directement.
- **Contrat `ml/`** : `ml/anomalies.py` (`raw_episodes`, `window_days`) et `ml/health.py` (`get_overview`, `get_forecast`) — stubs levant `NotImplementedError`, docstrings mappées aux étapes validées (préprocessing/segmentation/hystérésis/seuils Tukey). `ml/README.md` = guide d'intégration.
- **Agrégations partagées** (`services/anomaly_aggregation.py`) sorties de `mocks/anomalies.py` : surcharge de statut, filtrage, `compute_stats`, `compute_histogram` — identiques quelle que soit la source. `mocks/anomalies.py` réduit à la production d'épisodes bruts (`raw_episodes`, `window_days`).
- **Lecture DB documentée** (`db/queries.py`) : `read_temp_humidity` / `read_scada_logs` / `read_ups_events` (pandas via `engine.py`). ⚠️ NON TESTÉ, noms de colonnes à confirmer (pas d'accès DB).
- **501 explicite** : handler `NotImplementedError → 501` dans `main.py` — `DATA_SOURCE=live` avant branchement renvoie un message clair, pas un 500 opaque. `.env.example` documente `DATA_SOURCE`.

### Validation
- `pytest tests/` : **29/29 verts** (3 nouveaux : défaut = mock ; `DATA_SOURCE=live` → 501 sur les 6 endpoints ; retour au mock OK). Refactor agrégations vérifié sans régression via les tests d'anomalies existants.
- **Vérif live** (uvicorn) : mock → 200 ; `DATA_SOURCE=live` → 501 avec message « fournir le pipeline ML validé » sur health + anomalies.

### En suspens (bloquant pour la suite de Phase 8)
- **Fournir le code du pipeline validé** (notebook/.py) → à adapter dans `ml/` (ne pas réécrire).
- **Accès DB** `datacenter_ops` (credentials dans `.env`, base joignable depuis la machine) → tester `db/queries.py`, confirmer les schémas.
- Scoring composite santé ; sémantique forecast °C↔score (à trancher au branchement, cf. note session Phase 5).

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
- Reste : Phase 8 (intégration pipeline ML réel), Phase 9 (UPS/generators), Phase 10 (e2e, responsive, a11y, livrable). Le pattern « action utilisateur persistée surchargeant/filtrant une donnée dérivée » est désormais établi sur maintenance, anomalies et reminders.

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
