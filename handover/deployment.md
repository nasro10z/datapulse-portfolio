# DataPulse — Déploiement (handover)

> État actuel : projet académique **DSIP4 — UC3**, exécuté en local (pas d'hébergement cloud, pas de conteneurisation, pas de CI/CD configurés à ce jour — aucun `Dockerfile`/`docker-compose`/pipeline GitHub Actions dans le repo). Ce document couvre ce qui existe réellement : build de production des deux applications, et la bascule mock → pipeline réel, qui est la seule vraie étape de « mise en service » du projet.

## 1. Ce qui n'est pas fait (à savoir avant de proposer un déploiement)

- Pas de conteneurisation (Docker).
- Pas de reverse proxy / serveur HTTP de prod configuré (nginx, Caddy…).
- Pas de CI/CD (build/tests ne tournent pas automatiquement sur push/PR).
- Pas d'environnement staging/prod distinct — un seul environnement, local.
- Pas de gestion de secrets au-delà de `.env` (jamais committé, voir [`setup-guide.md`](setup-guide.md)).

Si le projet doit être réellement déployé (démo publique, remise finale hébergée), ces points sont **à statuer avec l'utilisateur avant d'agir** — voir §5.

---

## 2. Build de production

### Backend

Le backend n'a pas de build à proprement parler (Python interprété), mais un serveur ASGI de production plutôt que `--reload` :

```bash
cd backend
.venv/bin/pip install -r requirements.txt "uvicorn[standard]"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Pour plusieurs workers (recommandé en prod, un seul process ASGI ne parallélise pas le CPU) :

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

⚠️ Avec plusieurs workers, les deux bases SQLite (état applicatif + analytique) sont partagées par fichier — SQLite gère le multi-process en lecture/écriture concurrente mais avec un débit d'écriture limité (verrou fichier). Suffisant pour l'usage prévu (outil interne, faible concurrence d'écriture) ; à revoir si le volume d'écritures augmente (migrer vers PostgreSQL pour l'état applicatif, par exemple).

### Frontend

```bash
cd frontend
npm ci
npm run build      # → frontend/dist/, statique
```

`dist/` est un bundle statique (HTML/CSS/JS) — servable par n'importe quel serveur de fichiers statiques (nginx, Caddy, `serve`, un CDN...). Il n'y a **pas** de proxy Vite en production : le frontend buildé doit connaître l'URL réelle du backend.

**Point d'attention** : `frontend/src/api/client.js` fait des `fetch('/api/...')` **relatifs** (voir `setup-guide.md` §2). En dev, le proxy Vite résout ça vers `localhost:8000`. En production, deux options :

1. Servir le frontend et le backend **sous le même domaine** (reverse proxy qui route `/api/*` vers uvicorn et le reste vers `dist/`) — aucun changement de code requis.
2. Servir le frontend sur un domaine séparé du backend — il faudra alors adapter `client.js` pour préfixer les appels avec l'URL absolue du backend (actuellement non paramétré par variable d'environnement, à ajouter si ce cas se présente).

L'option 1 est la plus simple vu l'état actuel du code et est recommandée pour ce projet.

### Vérifier un build de prod avant de le livrer

```bash
cd frontend
npm run build && npm run preview   # sert dist/ en local pour vérification visuelle
```

---

## 3. Bascule mock → pipeline réel (`DATA_SOURCE=live`)

C'est la vraie étape de « mise en production » de ce projet : passer des données synthétiques au pipeline ML validé sur les données réelles (Phase 8 de `ROADMAP.md`, A→G faites).

1. S'assurer que les CSV sources sont déposés à l'emplacement attendu par `app/ml/data/raw/` (voir `docs/data-architecture.md` — **non committés**, `.gitignore` les exclut explicitement vu leur volume).
2. Lancer le pipeline ETL complet depuis `backend/` (env virtuel activé) :
   ```bash
   python -m app.etl.run --train
   ```

   - `--train` réentraîne le modèle de prévision (XGBoost sur le delta 6h) ; à omettre pour ne recalculer que bronze/silver/gold avec les modèles déjà entraînés (`python -m app.etl.run`).
   - `--skip-ingest` repart du bronze déjà chargé (utile pour ne rejouer que transform/detect/score/forecast).
   - Chaque étape est **idempotente** : rejouer le pipeline remplace entièrement sa cible, ne duplique rien — sûr à relancer.
3. Vérifier que le gold est peuplé (ex. `GET /api/anomalies` doit renvoyer des épisodes non vides une fois `DATA_SOURCE=live`).
4. Basculer `.env` :
   ```ini
   DATA_SOURCE=live
   ```
   Ou en dérogation partielle (utile car les données réelles s'arrêtent en mai 2026 — les vues bornées à une fenêtre récente comme `window-stats` seraient vides en `live` alors que les scores de santé se lisent bien sur la dernière heure connue) :
   ```ini
   HEALTH_SOURCE=live
   ANOMALIES_SOURCE=mock
   ```
5. Redémarrer uvicorn. Si le gold est vide alors que `DATA_SOURCE=live`, les endpoints santé renvoient un **501** explicite plutôt qu'une erreur opaque — c'est le signal que l'étape 2 n'a pas été faite ou a échoué.

---

## 4. Variables d'environnement à définir en déploiement

Voir [`setup-guide.md`](setup-guide.md) pour le détail de chaque variable. En résumé pour un déploiement :

| Variable                                                                | Obligatoire                              | Notes                                                                                                                                                      |
| ----------------------------------------------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DATA_SOURCE`                                                           | non (défaut `mock`)                      | `live` une fois le pipeline réel branché (§3)                                                                                                              |
| `ANOMALIES_SOURCE` / `HEALTH_SOURCE`                                    | non                                      | dérogation par domaine                                                                                                                                     |
| `DB_HOST/PORT/NAME/USER/PASSWORD`                                       | non actuellement                         | PostgreSQL source non joignable — préparé pour un futur accès direct, inutilisé aujourd'hui                                                                |
| `APP_DB_PATH`                                                           | non (défaut `backend/data/datapulse.db`) | à monter sur un volume persistant si le backend tourne dans un environnement éphémère (conteneur sans volume = état PM/acquittements perdu au redémarrage) |
| `analytics_db_path` (dans `config.py`, pas de var env dédiée à ce jour) | non                                      | idem — à surveiller si l'environnement d'exécution est éphémère                                                                                            |

**Piège principal en cas d'hébergement futur** : si le backend tourne dans un conteneur ou une VM sans stockage persistant, `backend/data/*.db` disparaît à chaque redémarrage — toute PM planifiée, tout acquittement, et le gold recalculé par l'ETL seraient perdus. Monter `backend/data/` sur un volume persistant est **indispensable** avant tout déploiement au-delà d'une démo locale.

---

## 5. Avant de déployer réellement quelque part

Ce projet n'a jamais été déployé hors poste local — avant de pousser vers un hébergeur, une VM, ou un service cloud, à clarifier avec l'utilisateur :

- la cible (interne only vs accessible publiquement — le produit manipule des données d'infrastructure télécom, la sensibilité doit être évaluée),
- si une authentification doit être ajoutée (aucune n'existe aujourd'hui, voir `api-documentation.md` §Conventions),
- le stockage persistant pour les deux bases SQLite,
- si `DATA_SOURCE=live` est souhaité dès le déploiement ou si le mock suffit pour la démo/remise.

## 6. Documents liés

- [`setup-guide.md`](setup-guide.md) — installation locale complète, `.env.example` détaillé
- [`architecture.md`](architecture.md) — pourquoi deux bases SQLite séparées, rôle de l'ETL
- [`api-documentation.md`](api-documentation.md) — comportement `501` en cas de gold vide
