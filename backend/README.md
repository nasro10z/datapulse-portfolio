# DataPulse — Backend (FastAPI)

API mockée (Phase 1) : les endpoints de lecture servent des données générées avec
seed fixe, cohérentes avec le pipeline ML validé (seuils Tukey 27.85/30.40°C, parc
MSC-10). Le vrai pipeline sera branché en Phase 8 sans changer les contrats.

## Deux bases, deux rôles

| Base | Rôle | Module |
|---|---|---|
| PostgreSQL `datacenter_ops` | source de données du data center, **lecture** | `app/db/engine.py` (non branché) |
| SQLite `data/datapulse.db` | état saisi dans l'outil (plannings de PM), **écriture** | `app/db/app_db.py` |

Les plannings de PM ne sont pas des données mockées : ils sont saisis par
l'utilisateur et persistés en SQLite (`app/services/maintenance.py`). Le fichier
est créé au démarrage et un jeu de démo n'est inséré que si le calendrier est
vide — supprimer `data/datapulse.db` remet l'état à zéro.

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # puis remplir DB_USER / DB_PASSWORD (non requis en Phase 1)
```

## Lancer

```powershell
.venv\Scripts\uvicorn app.main:app --reload
```

Swagger : http://localhost:8000/docs

## Tests

```powershell
.venv\Scripts\python -m pytest tests/
```
