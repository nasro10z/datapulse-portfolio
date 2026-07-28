"""Repositories — seule surface d'accès aux couches du stockage analytique.

L'ETL (écriture) et l'API (lecture gold) passent par ces fonctions, jamais par du
SQL en direct. C'est le contrat stable : changer la techno de stockage n'impacte
que ces modules. Voir `docs/data-architecture.md` §5.
"""
