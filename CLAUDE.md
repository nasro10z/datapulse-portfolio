# CLAUDE.md — DataPulse

Ce fichier donne à Claude Code le contexte nécessaire pour travailler efficacement sur ce projet. Lis-le avant toute tâche de développement.

## 1. Contexte du projet

**DataPulse** est une plateforme d'analytics et de maintenance prédictive développée pour un opérateur télécom qui possède des data centers en collaboration avec une société de service data science , dans le cadre du projet académique **DSIP4 — Use Case UC3**. L'équipe s'appelle **DataPulse**.

- **Site couvert** : data center télécom MSC-10
- **Équipements surveillés** :
  - 10× unités de climatisation **STULZ ASD 522 AS** (installées 2019 )
  - 2× onduleurs **SOCOMEC 200kVA** (installés 2020 — )
  - 2× groupes électrogènes **YANAN** (installés 2025 — phase d'établissement de baseline)
- **Positionnement produit** : une **couche d'aide à la décision**, PAS un système d'alarme autonome. Ne jamais présenter le produit comme prenant des décisions automatiques.
- **Deux personas cibles** :
  - Manager des sites → objectif : avoir une vue des sites et une vue globale pour mieux mener ses taches manageriales
  - Superviseurs d'alarmes → objectif : réduire la fatigue liée aux fausses alertes
  - Techniciens de maintenance → objectif : anticiper la dégradation avant panne

## 2. Stack technique

- **Backend** : FastAPI (Python)
- **Frontend** : React
- **Base de données source** : PostgreSQL (`datacenter_ops`) — **non joignable directement** (plateforme isolée qui garde la base intouchable). Les données sont fournies en **exports CSV** des tables, ingérés par l'ETL. (Si un accès SQLAlchemy devenait possible : `URL.create()`, jamais psycopg2 direct.)
- **ML/Data science** : pandas, numpy, scikit-learn, implémentation de modèles entrainés dur les données pour pouvoir détécter les anomalies et faire des prédictions
- **Langue de dev** : Python par défaut ; Scala/Spark uniquement si explicitement demandé

## 3. Architecture du repo

```
datapulse/
├── backend/
│   ├── app/
│   │   ├── api/          # routes FastAPI par domaine (health, forecast, anomalies, maintenance, reminders)
│   │   ├── models/        # schémas Pydantic
│   │   ├── ml/              # pipelines ML existants (preprocessing, détection, forecasting)
│   │   ├── db/               # connexion SQLAlchemy, requêtes
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/           # Aperçu, Site Health, Forecast, Anomalies, Maintenance (rappels = notifications, pas une page)
│   │   ├── design-system/ # tokens extraits de Claude Design (couleurs, typo, composants)
│   │   └── api/               # clients HTTP vers le backend
│   └── package.json
└── docs/
    └── fault_catalog_v2.docx
```

**Règle importante** : garder `ml/` (logique de traitement des données/modèles) strictement séparé de `api/` (exposition REST). Le code ML existant est déjà validé — ne pas le réécrire, l'exposer faire ne sorte que l'intégration des modèles ml se fasse fluidement et que ce soit bien documenté 

## 4. État du pipeline ML (déjà validé — ne pas refaire, réutiliser)

### Données
Trois tables sources, fournies en **exports CSV** (PostgreSQL `datacenter_ops` non joignable) : `temp_humidity` (~107k lignes, capteur `SITE01_SALLE_SWITCH`), `scada_logs`, `ups_events`. **Granularité de détection : par salle** (capteur salle switch), pas par unité STULZ individuelle.

### Preprocessing (pipeline complet et validé)
- Déduplication : 242 timestamps dupliqués identifiés, lignes dégradées (humidité NaN) confirmées comme valeurs de repli
- Classification des gaps : seuil >125s = discontinuité (coupures secteur ou pannes de communication SCADA)
- Segmentation via `cumsum()` sur les discontinuités (~1 904 segments)
- Rolling stats multi-échelle : fenêtres 12/36/78 points (~24min/1h12/2h36), choisies par analyse ACF
- Seuils de sévérité directionnels basés sur Tukey IQR : `mild_upper=26.75°C`, `extreme_upper=28.65°C` (valeurs livrées avec le modèle `environmental`, split train — cf. `models/environmental/thresholds.json` du package mlops-api)
- Détection d'épisodes par hystérésis : 201 épisodes bruts → 27-36 épisodes cohérents (`exit_margin=0.5`, `min_exit_duration=5`)



## 5. Design system

Le design system DataPulse est produit séparément via Claude Design (esthétique sobre-technique : base navy/charcoal/gris neutres, accents thermique/énergie/criticité utilisés avec parcimonie, typographie avec chiffres tabulaires, logo DataPulse dédié). tu trouveras le design en fichier html nommé "DataPulse - Identity v2 (standalone)"
## 6. Fonctionnalités clés — spécifications déjà arrêtées

### Aperçu (page d'accueil d'un site)
- Score global + sous-scores (environnement/énergie/batterie) des dernières 24h
- Prochaine panne prédite (la plus proche toutes familles confondues) avec ses détails
- Petit aperçu des 5 dernières lignes de la table des anomalies (lien vers la page complète)
- Prochaine maintenance + nombre de maintenances sur les 7 prochains jours (lien vers le calendrier complet)
- Page d'index du site (route `/`) ; Santé du site déplacée sur `/health`

### Rappels — notifications, pas une page
- Plus de page dédiée : cloche en haut à droite du header (badge = nombre de rappels actifs), popover listant les rappels avec les actions acquitter/reporter
- Backend inchangé (`GET /api/reminders`, `POST .../acknowledge`, `POST .../snooze`) — seule la présentation frontend change

### Maintenance préventive
- Tout en haut : KPI prochaine maintenance (équipement + date + délai) et nombre de maintenances sur les 7 prochains jours
- Formulaire de planification en premier (avant le calendrier) : équipement (sélecteur, parc réel), date de dernière PM, période avant la prochaine (valeur + unité), technicien assigné, notes
- Calcul automatique : date prochaine PM = date dernière PM + période → ajout automatique au calendrier
- Calendrier ensuite, cliquable par jour : affiche le détail du jour sélectionné (PM du jour, avec actions modifier/supprimer)

### Prédiction des pannes / Forecast
- Organisation **par score, pas par équipement**
- Global Health Score Chart = élément dominant de la page (pleine largeur, sélecteur d'horizon 24h/7j/30j visible)
- Sub-scores (par famille d'équipement) en dessous, cards plus petites, clairement subordonnées visuellement

## 7. Contraintes connues

- Le notebook d'origine (Databricks) ne permet pas l'installation de packages externes — **cette contrainte ne s'applique qu'au pipeline ML notebook, pas au backend FastAPI**, qui est libre d'installer ce dont il a besoin.
- Ne pas faire de claims de performance quantitatifs au-delà des métriques livrées avec les modèles (`metadata.json` — ex. F1 anomalie `environmental` = 0.83). Aucun jeu de labels ground-truth externe n'est disponible pour une validation supplémentaire.

## 8. Journal des sessions

À la fin de chaque session de travail, mettre à jour `SESSIONS.md` à la racine : ajouter/compléter l'entrée de la session (date, phases ROADMAP couvertes, réalisations, décisions, points en suspens).

## 9. Ordre de développement

Voir `ROADMAP.md` pour le détail des étapes. En résumé : backend avec données mockées d'abord → frontend branché sur les mocks → intégration progressive du vrai pipeline ML (package `mlops-api` livré) → extension UPS/generator. Architecture des données : `docs/data-architecture.md`.
