# DataPulse — Guide d'installation (handover)

> Mise en route locale du projet, backend + frontend. Pour l'architecture, voir [`architecture.md`](architecture.md) ; pour les endpoints, voir [`api-documentation.md`](api-documentation.md) ; pour la mise en production, voir [`deployment.md`](deployment.md).

## Prérequis

| Outil | Version | Remarque |
|---|---|---|
| Python | 3.13 | requis par les artefacts modèle `.joblib` (`scikit-learn==1.9.0`) — voir `backend/requirements.txt` |
| Node.js | 22 LTS recommandé | Vite 6 émet un warning EBADENGINE sous Node < 21.7 (fonctionne quand même) |
| Git | — | |

Pas de PostgreSQL local requis : `datacenter_ops` est **non joignable** en dev, les données arrivent en exports CSV (voir `docs/data-architecture.md`).

---

## 1. Backend

```bash
cd backend
python -m venv .venv
```

Windows (PowerShell) :
```powershell
.venv\Scripts\pip install -r requirements.txt
```

macOS/Linux :
```bash
.venv/bin/pip install -r requirements.txt
```

### Configuration — `.env`

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

`backend/.env.example` (déjà présent dans le repo, jamais committer `.env` lui-même) :

```ini
# Source des données métier : mock (défaut, générateurs seedés) ou live (pipeline ML).
# En "live", l'API lit le gold précalculé : lancer d'abord `python -m app.etl.run --train`
# depuis backend/, sinon les endpoints santé renvoient 501. Voir app/ml/README.md.
DATA_SOURCE=mock

# Dérogation par domaine (optionnelle) : ne basculer qu'une partie de l'application.
# Non renseignée → le domaine suit DATA_SOURCE.
# ANOMALIES_SOURCE=mock
# HEALTH_SOURCE=live

# Connexion PostgreSQL datacenter_ops — copier vers .env et remplir (jamais committer .env)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=datacenter_ops
DB_USER=
DB_PASSWORD=

# Base applicative SQLite (plannings de PM saisis dans l'outil).
# Optionnel — par défaut backend/data/datapulse.db, créée au démarrage.
# APP_DB_PATH=
```

**Pour démarrer en local, aucune variable n'est obligatoire à remplir** : `DATA_SOURCE=mock` fonctionne sans base PostgreSQL ni pipeline ML lancé. `DB_USER`/`DB_PASSWORD` ne servent que si un accès SQLAlchemy à la source devient possible un jour (§7 de `CLAUDE.md`) — ce n'est pas le cas actuellement.

Pour passer en données réelles (`DATA_SOURCE=live`), voir [`deployment.md`](deployment.md) §3 (lancer l'ETL avant de démarrer l'API).

### Lancer le serveur

```powershell
.venv\Scripts\uvicorn app.main:app --reload
```
```bash
.venv/bin/uvicorn app.main:app --reload
```

- API : `http://localhost:8000`
- Swagger interactif : `http://localhost:8000/docs`
- Le premier démarrage crée `backend/data/datapulse.db` (état applicatif) et `backend/data/datapulse_analytics.db` (bronze/silver/gold, vide tant que l'ETL n'a pas tourné), et seed un jeu de démo de PM si le calendrier est vide.

### Tests

```powershell
.venv\Scripts\python -m pytest tests/
```

---

## 2. Frontend

```bash
cd frontend
npm install
```

Pas de `.env` requis côté frontend : l'appel API passe par le proxy Vite (`vite.config.js`) `/api` → `http://localhost:8000`, donc `frontend/src/api/client.js` fait des `fetch('/api/...')` relatifs — rien à configurer pour pointer vers le backend en dev.

### Lancer le serveur de dev

```bash
npm run dev
```

- App : `http://localhost:5173`
- Le backend (`uvicorn`) doit tourner en parallèle sur le port 8000 pour que les appels API répondent.

### Build de production

```bash
npm run build     # sortie dans frontend/dist/
npm run preview   # sert le build localement pour vérification
```

### Tests

```bash
npm run test
```

---

## 3. Démarrage complet (les deux ensemble)

Deux terminaux :

```powershell
# Terminal 1 — backend
cd backend
.venv\Scripts\uvicorn app.main:app --reload
```

```bash
# Terminal 2 — frontend
cd frontend
npm run dev
```

Puis ouvrir `http://localhost:5173`. Toutes les données sont mockées par défaut (`DATA_SOURCE=mock`) — cohérentes avec les seuils réels du pipeline (Tukey 26.75/28.65°C) mais synthétiques, pas besoin d'accès à la base source pour développer.

---

## 4. Problèmes connus

- **Node absent/instable sur certaines machines de session** : si `node`/`npm` sont introuvables, réinstaller Node avant tout travail frontend (voir `SESSIONS.md` pour l'historique de ce point).
- **Port 8000 occupé par un process fantôme** : si `uvicorn` refuse de démarrer sans process visible sur le port, voir la mémoire de session *Stray backend port 8000* — contournement via un proxy Vite temporaire sur un port de secours.
- **Warning EBADENGINE** sous Node < 21.7 : sans conséquence sur `npm run dev`/`build`, mais bloque `create-vite` si jamais besoin de re-scaffolder.

## 5. Documents liés

- [`architecture.md`](architecture.md) — comment backend/frontend/stockage s'articulent
- [`api-documentation.md`](api-documentation.md) — détail des endpoints exposés une fois le backend lancé
- [`deployment.md`](deployment.md) — build de production et bascule vers les données réelles
- `backend/README.md` — README backend existant (rôle des deux bases SQLite)
