"""Couche de stockage analytique DataPulse — persistance pure (bronze/silver/gold).

Cette couche ne contient AUCUNE logique métier, AUCUN pandas, AUCUN modèle ML :
uniquement des tables (voir `schema/`) et des repositories (voir `repositories/`)
qui exposent lecture/écriture par couche. C'est le contrat stable entre le
stockage, l'ETL (qui écrit) et l'API (qui lit le gold).

Voir `docs/data-architecture.md` pour l'architecture d'ensemble.
"""
