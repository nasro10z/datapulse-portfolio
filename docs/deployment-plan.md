# DataPulse — Plan de déploiement portfolio

Plan d'exécution pour rendre DataPulse **déployable publiquement** et **présentable en
portfolio**, à partir du commit `f64f054` (« handover check »).

Ce document est un plan de travail : il se lit de haut en bas, phase par phase, et se
coche au fur et à mesure. Les documents de référence associés :
[`ml-decisions.md`](ml-decisions.md) (choix DS/ML), [`data-architecture.md`](data-architecture.md),
[`../handover/deployment.md`](../handover/deployment.md), [`../handover/current-state.md`](../handover/current-state.md).

---

## 0. Décisions actées

| Sujet | Décision |
|---|---|
| **Confidentialité** | Anonymisation complète (code, UI, docs, tests, historique git) **+ recalage temporel** du gold pour que la démo ne soit ni datée de mai 2026 ni rattachable au site réel |
| **Hébergement** | **Vercel** (front + fonction Python dans un seul projet) **+ Postgres managé** (Neon/Supabase) pour l'état applicatif, afin que les écritures persistent |
| **Vitrine ML** | Une **page « Méthode »** dans l'application + un **README portfolio**, alimentés par [`ml-decisions.md`](ml-decisions.md) |
| **Historique Vercel** | Un déploiement a été tenté le 15/08 puis **supprimé** ; le message d'erreur n'est plus disponible → on repart d'un déploiement neuf avec une checklist de vérification |

### Point de départ technique

Quatre commits de déploiement (`86e30f0`, `6811d75`, `d43faa3`, `039b573`) ont été
annulés par un `reset` sur `f64f054` le 01/09. **Ils ne sont pas perdus** : ils vivent sur
`origin/main` et leur contenu est encore dans l'index local. Ce travail est bon et
largement réutilisable :

| Acquis | Fichier |
|---|---|
| Bundle 633 Mo → 148 Mo | `requirements.txt` (racine) / `requirements-etl.txt` / `requirements-dev.txt` + `.vercelignore` |
| Base servie 40 Mo → 1,1 Mo | `backend/app/etl/export_gold.py` |
| Compatibilité disque en lecture seule | `is_read_only()` dans `backend/app/storage/analytics_db.py` |
| Front + API sur un seul domaine (zéro CORS) | `api/index.py` + `vercel.json` |

### Trois problèmes connus à traiter

1. **L'historique git porte le nom du client.** Les 28 commits et `SESSIONS.md` (70 Ko)
   contiennent les identifiants réels. Anonymiser l'arbre de travail ne suffit pas pour un
   repo public. → Phase 1.4.
2. **L'export gold casse la source live des anomalies.** `export_gold.py` ne garde que les
   4 tables gold, or `ml/anomalies.py` lit `silver_repo.span_days()` / `last_ts()` sur
   `th_clean`, supprimée de l'export. Masqué aujourd'hui par `ANOMALIES_SOURCE=mock` ;
   devient un **500 en production** dès que les anomalies passent en live. → Phase 2.2.
3. **pandas est sur le chemin de requête** (`gold_repo.read_health_hourly` via
   `pd.read_sql`) : ~90 Mo de dépendances et ~1 s d'import à chaque démarrage à froid, pour
   une seule ligne de logique pandas réelle. Non bloquant, mais c'est le levier de repli si
   Vercel coince. → Phase 4.6.

**Aucune fuite de données à ce jour** : aucun CSV/XLSX brut ni `.env` n'a jamais été
commité (vérifié sur tout l'historique), et le gold ne contient aucun identifiant client.

---

## Phase 0 — Récupérer sans rien perdre · ~0,5 j — **faite**

- [x] **0.1** Branche de référence `deploy-attempt-v1` créée sur `origin/main` (039b573) :
      les 4 commits annulés y sont figés. Arbre de travail ramené à `f64f054` par
      `git reset --hard`, après sauvegarde de ce qui n'existait nulle part ailleurs
      (`ml-decisions.md`, ce plan, l'entrée SESSIONS de la session 11, le réglage local du
      proxy Vite, l'export gold de 1,1 Mo). Suite de tests rejouée sur la base restaurée :
      **85 tests verts**.
- [x] **0.2** `.gitignore` nettoyé : les lignes `CLAUDE.md`, `ROADMAP.md`, `SESSIONS.md` et
      `docs` sont supprimées. Elles étaient sans effet sur ces fichiers (déjà suivis) mais
      piégeaient tout **nouveau** fichier de `docs/` — dont ce plan, qui n'était visible
      qu'avec `git add -f`.
- [x] **0.3** Dépôt public cible : **`datapulse-portfolio`**, nouveau dépôt à créer sur
      GitHub. `datapulse-app` reste privé et intact comme filet de sécurité.

### ⚠️ Ce qui est parké sur `deploy-attempt-v1` — à récupérer, pas à réécrire

Les 4 commits annulés ne contenaient pas que du déploiement : ils portaient aussi une
**mise à jour de fond de la documentation**, perdue par le retour à `f64f054`. À récupérer
depuis la branche au moment voulu, plutôt qu'à réécrire :

| Contenu parké | Pourquoi ça compte | Phase qui le récupère |
|---|---|---|
| `handover/current-state.md` (217 lignes, **n'existe que sur la branche**) | Le meilleur document du repo pour un portfolio : ce qui est réel vs démo, les chiffres honnêtes, comment distinguer les deux à l'écran | 5.3 |
| `docs/ml-data-integration.md`, `backend/app/ml/README.md` | Les versions de `f64f054` sont **périmées** (elles annoncent encore health/forecast en 501 et les étapes F/I « à venir ») | 6 |
| `handover/{architecture,deployment,api-documentation,project-overview,setup-guide}.md` | Réécrits et complétés, pas seulement traduits | 6 |
| Les fichiers de déploiement (`vercel.json`, `api/index.py`, `export_gold.py`, split des requirements, `is_read_only()`) | Le travail technique réutilisable | 2 et 4 |

Toute la documentation de la branche est en **anglais** ; l'arbre restauré est en
**français**, comme `ml-decisions.md` et ce plan. Choix de langue à trancher en Phase 6 —
une seule langue pour tout le repo.

---

## Phase 1 — Confidentialité · ~1,5 j — **1.1 et 1.2 faites**

### 1.1 Lexique d'anonymisation — **fait**

La table de correspondance réelle vit dans `.anonymization-map.local.md`, **gitignoré** :
publiée, elle dés-anonymiserait tout le reste du dépôt d'un seul coup d'œil. Ce document
ne décrit donc que les valeurs d'arrivée.

| Domaine | Valeur retenue |
|---|---|
| Opérateur | `TelcoNet` (identifiant technique), « opérateur télécom » (libellés) |
| Site branché | `MSC-10`, identifiant frontend `msc10` |
| Sites de démonstration | `MSC-03` / `msc03`, `BSC-07` / `bsc07` |
| Capteur de salle | `SITE01_SALLE_SWITCH` |
| Base source PostgreSQL | `datacenter_ops` |
| Autres sites du fichier 2022 | « six autres sites du même réseau » |

**Conservés, car non identifiants** : `MSC 10` / `MSC10` (terme télécom générique — et
c'est aussi la chaîne sur laquelle filtrent l'ETL et le package livré, donc rien ne casse),
les noms des fichiers bruts, les marques d'équipement (`STULZ`, `SOCOMEC`, `YANAN`) et la
référence au cadre académique `DSIP4 — Use Case UC3`.

**Hors dépôt par nature** : les messages SCADA bruts et les bases locales
(`backend/app/ml/data/`, `backend/data/`) portent le nom réel — tous gitignorés.
L'anonymisation porte sur le dépôt, pas sur les données privées de la machine de dev.

### 1.2 Application du lexique — **faite** (76 remplacements, 31 fichiers)

- [x] Passe scriptée sur tout l'arbre (frontend, backend, tests, docs, `README`,
      `ROADMAP`, `CLAUDE.md`) — le script est conservé dans le scratchpad de session
- [x] Identifiants de site du frontend (`sites.js`) alignés sur les nouveaux libellés :
      `msc10` / `msc03` / `bsc07`, résolus par `findSite` avec repli sur `SITES[0]`
- [x] Liste des six autres villes du fichier 2022, dans `ml-data-integration.md`
- [x] Le **gold** est déjà propre (`SALLE_SWITCH` seul, aucun préfixe de site)

**Le seul point dur, et sa solution** : le pipeline reconstruit les messages UPS avec un
préfixe qui doit reproduire **à l'identique** celui du fichier de référence livré, faute de
quoi le golden test de fidélité (100 % sur 2 569 lignes) compare des chaînes différentes.
Ce préfixe porte le nom réel du site. Il est donc devenu un réglage,
`Settings.raw_ups_message_prefix`, à valeur par défaut neutre et surchargeable par
`RAW_UPS_MESSAGE_PREFIX` dans `backend/.env` (gitignoré) :

- sur la machine de dev, la vraie valeur est posée dans `.env` → le golden test passe à
  100 % comme avant ;
- dans le dépôt public, la valeur par défaut est neutre — et les tests de fidélité y sont
  de toute façon *skippés*, puisqu'ils exigent les données brutes, qui sont privées.

Les deux filtres qui font tourner l'ETL (`message.str.contains("MSC 10")`) sont
**inchangés**, `MSC 10` étant conservé par le lexique.

### 1.3 `SESSIONS.md` — **faite**

Lecture intégrale (712 lignes). Trois trouvailles hors lexique, toutes corrigées : des
**noms de villes employés seuls** (le script n'avait traité que les libellés complets de
site — c'étaient eux qui rattachaient le réseau à un pays), un **nom de personne** servant
de placeholder et de donnée de test, et l'**identifiant du projet d'hébergement de base**
cité dans le journal. Rien d'autre : aucun email, aucune URL externe, aucun chemin machine
nominatif, aucun tiers nommé.

Le garde-fou en sort renforcé : il lit désormais **deux blocs de termes** — sous-chaîne
pour les identifiants composés, **mot entier** pour les noms courts, parce qu'un nom de
ville de la liste se trouve au milieu d'un participe présent très courant et faisait
échouer le test sur un fichier propre. Les deux modes sont vérifiés par des fichiers
pièges. Et le module ne cite plus aucun terme interdit : il se signalait lui-même.

#### Décision initiale sur ce fichier

**Garder, anonymisé.** C'est le journal de décisions du projet (une entrée par session :
réalisations, décisions, points en suspens) — la seule trace du *pourquoi* des arbitrages,
et la source principale de [`ml-decisions.md`](ml-decisions.md). Dans un portfolio, c'est
une pièce rare : elle montre un raisonnement, des arbitrages assumés et des erreurs
corrigées, pas seulement un résultat.

- [ ] Appliquer le lexique sur les 70 Ko
- [ ] Relecture manuelle (le journal est le fichier le plus susceptible de contenir un
      détail client hors lexique)

### 1.4 Historique git

- [ ] `git filter-repo` sur un **clone**, avec le lexique en table de remplacement
- [ ] Pousser vers un **nouveau repo public** ; le repo actuel reste **privé et intact**
- [ ] Vérifier après coup : `git log -S` sur chaque terme du lexique → zéro occurrence

On garde ainsi l'historique phasé (qui vaut pour un portfolio) sans le nom du client.

### 1.5 Garde-fou anti-régression

- [ ] `backend/tests/test_no_client_identifiers.py` : parcourt l'arbre et échoue si un
      terme du lexique réapparaît. Branché en CI (Phase 6).

---

## Phase 2 — Volume des données et recalage temporel · ~1 j — **faite**

- [x] **2.1** `export_gold.py` récupéré depuis `deploy-attempt-v1` (avec `is_read_only()`
      et les 3 tests de stockage associés) : 39 Mo → **1,03 Mo**, journal `DELETE`,
      `vacuum`. Exception ajoutée au `.gitignore` pour versionner l'export.
- [x] **2.2** Table **`gold_meta`** (fin de couverture, étendue d'observation, décalage
      appliqué), écrite par l'export et lue par `ml/anomalies` — repli sur le silver en
      local. **Le 500 en production est corrigé**, et un test le prouve en servant les
      fenêtres depuis un export gold seul.
- [x] **2.3** Option `--shift-to-now` : translation **unique** de toutes les colonnes
      temporelles, calée sur le **dernier score horaire** (la donnée la plus fraîche que
      l'application affiche). Décalage actuel : **+135,5 jours**.
- [x] **2.4** Démo en **tout-live** : `ANOMALIES_SOURCE=mock` retiré de `.env`.
- [x] **2.5** `data_shift_days` exposé par `GET /api/health/overview` (`None` en mock).
      Le bandeau d'interface reste à faire — il va avec la page Méthode, en Phase 5.
- [x] **2.6** 6 tests (`tests/test_export_gold.py`) : contenu de l'export, uniformité de
      la translation, ancrage à l'heure courante, bornage de la fin de couverture,
      cohérence des statuts, et lecture des fenêtres **sans silver**.

### Deux décisions de conception, et pourquoi

**L'ancrage.** Trois dates coexistent dans la source : dernier score horaire
(10/05 10:00), dernier épisode (09/05, soit 1,25 j avant) et fin de couverture capteur
(18/05, soit 8,4 j après). Une translation étant **unique** par construction, une seule
peut tomber sur « maintenant ». C'est le **dernier score horaire** qui a été retenu :
c'est ce qu'affichent l'Aperçu et la Santé du site, et c'est de là que repart la
prévision. Conséquence assumée : la fin de couverture tomberait 8,4 j dans le futur —
elle est donc **bornée à l'instant de l'export**, sans quoi les fenêtres glissantes
s'ouvriraient sur des dates qui n'existent pas encore.

**Les statuts recalculés.** Le statut d'un épisode est dérivé de son âge contre la fin
de la période observée. Après recalage, un épisode vieux de 30 heures serait resté
étiqueté « résolu » — un artefact de calcul, pas un fait de maintenance. L'export les
recalcule donc contre la borne retenue ; sans recalage, c'est un no-op (même borne que
`etl/detect`), ce qu'un test vérifie.

### Ce que la démo montre désormais

| Vue | Avant | Après recalage |
|---|---|---|
| Aperçu / Santé du site | `updated_at` en mai 2026 | **heure courante** |
| Prévision | historique et courbe figés en mai | repart de maintenant, 30 j devant |
| Anomalies — table, histogramme, répartition | 388 épisodes datés de mai | **388 épisodes récents** |
| Anomalies — KPI 24 h / 7 j | 0 et 0 | **0 et 1** (30 j : 77, 90 j : 143) |

Le KPI 24 h reste à zéro, et c'est **exact** : la donnée source n'a réellement aucun
épisode dans les dernières 24 h précédant le dernier score. Le panneau affiche un état
vide explicite plutôt qu'un zéro ambigu. Repasser à `ANOMALIES_SOURCE=mock` remplirait
ces deux KPI avec des épisodes inventés — une ligne de `.env`, au prix de l'honnêteté de
la démonstration.

---

## Phase 3 — Écritures persistantes (Postgres managé) · ~1 j — **faite**

Six routes d'écriture sur trois pages (planifier / modifier / supprimer une PM, acquitter
une anomalie, acquitter / reporter un rappel). Sur `/tmp`, elles réussissent puis
s'évaporent — inacceptable pour une démo publique.

- [x] **3.1** `APP_DB_URL` dans `app/config.py` (défaut : SQLite local) ; `app/db/app_db.py`
      résout l'URL via `make_url`, normalise `postgres://` → `postgresql+psycopg2` et
      conserve les options de connexion (`sslmode`).
- [x] **3.2** Aucune dépendance nouvelle : `psycopg2-binary` était déjà déclaré. Moteur
      PostgreSQL construit avec **`NullPool`** (un pool ne survit pas à l'invocation
      serverless), `pool_pre_ping` (le conteneur réutilisé peut tenir une connexion déjà
      fermée côté hébergeur) et `connect_timeout=10` (échouer vite plutôt que de tenir la
      requête jusqu'au délai maximum de la fonction).
- [x] **3.4** Types vérifiés : `DateTime(timezone=True)`, `Mapped[date]`, `Mapped[bool]` —
      aucun type SQLite-spécifique dans `db/tables.py`, la bascule est gratuite.
- [x] **3.5** 6 tests (`tests/test_app_db.py`) sur la résolution d'URL, la normalisation,
      l'absence de pool et le non-fuitage des identifiants dans `str(url)`. Le test
      d'aller-retour réel s'exécute dès que `TEST_APP_DB_URL` est fournie.
- [x] **3.3** Projet Neon branché (PostgreSQL 18.6, endpoint avec pool, base `neondb`).
      Schéma créé — `pm_schedules`, `anomaly_actions`, `reminder_actions`. Vérifié à trois
      niveaux : aller-retour relu par une **nouvelle** connexion (donc côté serveur, pas
      dans un cache de processus), test d'intégration qui ne skippe plus (7/7), et les
      routes d'écriture exercées à travers l'API — PM planifiée (201) puis supprimée (204),
      anomalie acquittée (200), rappel reporté (204). Les 4 PM de démonstration sont
      seedées ; les écritures de la sonde ont été purgées.
- [x] **3.6** Plannings de maintenance en **lecture seule** sur l'instance publique
      (`PM_READ_ONLY=1`) — décidé plutôt qu'une remise à zéro périodique. Sans
      authentification, la saisie d'un visiteur modifierait durablement le calendrier que
      voient tous les autres. Les trois routes d'écriture répondent **403** (garde
      côté serveur : l'API est la frontière, et elle est publique) ; la consultation n'est
      pas touchée. Une route `GET /api/config` expose l'état de l'instance, lue **une fois
      au niveau de l'application** (`ConfigProvider`) plutôt que page par page — la même
      information servira le bandeau de démonstration. L'interface présente alors le
      formulaire désactivé (`fieldset disabled`) avec une note : la fonctionnalité reste
      visible pour un visiteur, sans être un piège. 5 tests, dont un qui vérifie que
      `/api/config` ne dit rien de la base ni de l'hébergement.

      ⚠️ Effet de bord corrigé au passage : `APP_DB_URL` **prime** sur `APP_DB_PATH`, donc
      un poste de dev branché sur le PostgreSQL de la démo faisait tourner **toute la
      suite de tests dans cette base partagée** — la fixture `reset_user_actions` y
      supprimait les acquittements après chaque test. La conftest neutralise désormais
      `APP_DB_URL`.

**En local, `data_shift_days` vaut `None` et les dates restent en mai 2026** : l'application
lit `datapulse_analytics.db`, la base complète et non recalée, où le silver fournit les
bornes. Le recalage ne concerne que l'**export** servi en déploiement, vers lequel
`ANALYTICS_DB_PATH` pointera. Ce n'est donc pas un symptôme, c'est la configuration.

**Le CLI Neon n'est pas nécessaire.** Le script d'onboarding (`neon.ts`, `neon deploy`,
MCP, `neon skills`) outille un projet Node/TypeScript ; notre backend est Python et parle
à PostgreSQL par SQLAlchemy. Une seule chose est utile : la **chaîne de connexion**, de
préférence celle de l'endpoint **avec pool** (`...-pooler...`), puisque chaque invocation
ouvre sa propre connexion.

---

## Phase 4 — Déploiement Vercel · ~1 j

- [ ] **4.1** Rejouer les fichiers de déploiement : `api/index.py`, `vercel.json`,
      `.vercelignore`, split des requirements (148 Mo au lieu de 633).
- [ ] **4.2** Retirer `uvicorn[standard]` du bundle de production (c'est Vercel qui sert
      l'ASGI ; uvloop/httptools sont compilés pour rien) et épingler la version Python.
- [ ] **4.3** **Vérifier le routage `/api/*`** : `vercel.json` réécrit `/api/(.*)` vers
      `/api/index`, or les routers FastAPI sont déjà montés sous `/api`. Si la fonction
      reçoit `/api/index`, **toutes** les routes répondent 404. Vérification avec
      `vercel dev` en local ; deux replis documentés : `root_path` sur l'application
      FastAPI, ou montage des routers sans préfixe.
- [ ] **4.4** Variables : `APP_DB_URL` en **secret du dashboard** (jamais dans le repo),
      `ANALYTICS_DB_PATH` en chemin absolu, `DATA_SOURCE=live`.
- [ ] **4.5** Checklist du premier déploiement :
      - [ ] les 5 routes de lecture répondent 200 ;
      - [ ] `updated_at` porte une date récente (le recalage fonctionne) ;
      - [ ] une PM planifiée **survit à un redéploiement** (Postgres fonctionne) ;
      - [ ] taille de fonction et durée de démarrage à froid relevées et notées dans
            `handover/deployment.md`.
- [ ] **4.6** *Si* la taille ou le délai coincent : sortir pandas du chemin de requête
      (`read_health_hourly` en SQL + dictionnaires) → ~90 Mo de moins. Prévu comme repli,
      pas fait d'office.

**Limites à garder en tête** : la documentation Vercel annonce **250 Mo** décompressés par
fonction (et non 500 comme noté auparavant dans le repo), et une durée d'exécution bornée
sur l'offre gratuite.

---

## Phase 5 — Vitrine du travail ML / DS · ~1,5 j — **5.1 faite**

Sans cette phase, l'application déployée ne montre **aucun** travail ML : elle lit du gold
précalculé, et les modèles sont volontairement exclus du bundle.

- [x] **5.1** `app/etl/export_model_cards.py` → `frontend/src/data/model-cards.json`,
      importé par le front au build. Les **chiffres viennent des artefacts**
      (`metadata.json`, `thresholds.json`) et les volumes des couches, des bases
      elles-mêmes ; seule la prose (à quoi sert le modèle, pourquoi celui-là, ce qu'il ne
      fait pas) est éditoriale et vit dans le script. Aucun modèle n'entre dans le bundle.
      5 tests comparent la carte publiée aux artefacts — dont un garde-fou qui échoue si
      le JSON committé devient périmé après un réentraînement.
- [ ] **5.2** Page `/methode` (+ entrée de navigation, i18n FR/EN comme le reste de
      l'application), alimentée par [`ml-decisions.md`](ml-decisions.md) :
      - le schéma bronze → silver → gold chiffré (137 970 → 107 047 lignes, 1 905 segments,
        2 569 lignes SCADA → 388 épisodes, 2 137 heures scorées, 164 points de prévision) ;
      - trois model cards (HMM 6 états F1 0,83 · IsolationForest 300 arbres, contamination
        3 % · XGBoost delta 6 h top 20, MAE 6,085 vs persistance 6,124) ;
      - les décisions structurantes : détection par salle, seuils Tukey 26,75 / 28,65,
        hystérésis, filtre « HMM + franchissement réel » (1 383 → 388), cible delta ;
      - les preuves de fidélité (égalité < 1e-6 avec le notebook, SCADA reproduit à 100 %) ;
      - les **limites assumées** (validé à +6 h seulement, pas de vérité terrain, recalage
        temporel).
- [ ] **5.3** README portfolio : problème métier, lien de démo, captures des pages, schéma
      d'architecture, résultats ML, « ce qui est réel vs démo », lancement local, tests.
- [ ] **5.4** Bandeau de démo dans l'application (données recalées, écritures ouvertes au
      public).

---

## Phase 6 — Finition · ~0,5 j

- [ ] `handover/deployment.md` et `handover/current-state.md` mis à jour (anonymisés, cas
      Postgres, routage Vercel vérifié).
- [ ] `SESSIONS.md` et `ROADMAP.md` complétés.
- [ ] CI GitHub Actions : `pytest` + `vitest` + le garde-fou d'anonymisation (1.5).
- [ ] *(optionnel)* Passe de traduction EN pour aligner `docs/ml-decisions.md` et ce plan
      sur le reste de `docs/` et `handover/`, déjà en anglais.

**Total estimé : 6 à 7 jours de travail effectif.** Les phases 1, 2 et 5 sont indépendantes
des phases 3 et 4 et peuvent avancer en parallèle.

---

## Risques et parades

| Risque | Parade |
|---|---|
| Le rewrite Vercel casse le routage `/api` | `vercel dev` avant tout déploiement (4.3), deux replis prêts |
| Démarrage à froid proche de la limite (pandas + Postgres) | Mesure en 4.5, repli pandas en 4.6 |
| Le recalage temporel rend un graphe incohérent (prévision démarrant dans le passé) | Décalage **unique** pour toutes les colonnes + test d'ordre chronologique (2.6) |
| `filter-repo` réécrit tous les SHA | Opéré sur un **clone**, vers un **nouveau** repo ; l'original privé reste intact |
| Base de démo polluée par les visiteurs | Seed idempotent + remise à zéro optionnelle (3.6) |
| Le gold versionné devient périmé | Régénérer `export_gold` **et recommitter** après chaque exécution du pipeline (déjà documenté) |
