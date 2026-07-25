# DataPulse — Backend (FastAPI)

API mockée (Phase 1) : tous les endpoints servent des données générées avec seed
fixe, cohérentes avec le pipeline ML validé (seuils Tukey 27.85/30.40°C, parc
MSC-10). Le vrai pipeline sera branché en Phase 8 sans changer les contrats.

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
