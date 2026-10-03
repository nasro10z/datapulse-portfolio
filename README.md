# DataPulse

Plateforme d'analytics et de maintenance prédictive pour un data center télécom (**MSC-10**) — projet académique **DSIP4 — Use Case UC3**.

DataPulse est une **couche d'aide à la décision** : elle donne aux managers de site, superviseurs d'alarmes et techniciens de maintenance une vue de la santé des équipements, des anomalies détectées et des maintenances à venir — ce n'est pas un système d'alarme autonome, elle ne décide jamais à la place de l'humain.

**Équipements couverts** : 10× climatisations STULZ ASD 522 AS, 2× onduleurs 200kVA, 2× groupes électrogènes.

---

## Stack

FastAPI (backend) · React/Vite (frontend) · SQLite (stockage bronze/silver/gold + état applicatif) · pandas/scikit-learn/hmmlearn/XGBoost (pipeline ML, livré et validé).

## Démarrer en 2 minutes

```bash
# Backend
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # Windows : .venv\Scripts\pip ...
copy .env.example .env                       # macOS/Linux : cp .env.example .env
.venv/bin/uvicorn app.main:app --reload      # Windows : .venv\Scripts\uvicorn ...
```

```bash
# Frontend (autre terminal)
cd frontend
npm install
npm run dev
```

App sur `http://localhost:5173`, API sur `http://localhost:8000/docs`. Aucune base externe requise : le backend tourne par défaut avec des données mockées (`DATA_SOURCE=mock`), déjà cohérentes avec les seuils réels du pipeline. Détail complet, prérequis et `.env` : **[handover/setup-guide.md](handover/setup-guide.md)**.

---

## S'orienter dans le repo

| Je veux... | Je vais... |
|---|---|
| Comprendre le produit, les personas, l'avancement du projet | [handover/project-overview.md](handover/project-overview.md) |
| Comprendre comment frontend / backend / stockage s'articulent | [handover/architecture.md](handover/architecture.md) |
| Installer le projet en local | [handover/setup-guide.md](handover/setup-guide.md) |
| Consulter la liste des endpoints REST et leurs schémas | [handover/api-documentation.md](handover/api-documentation.md) |
| Builder pour la production / basculer sur les données réelles | [handover/deployment.md](handover/deployment.md) |
| Voir le détail du pipeline de données (bronze/silver/gold) | [docs/data-architecture.md](docs/data-architecture.md) |

```
datapulse/
├── backend/       # FastAPI — routes, services, pipeline ML vendorisé, ETL, stockage
├── frontend/       # React/Vite — 5 pages + composants + design system
├── handover/       # documentation de passation (ce tableau)
```

