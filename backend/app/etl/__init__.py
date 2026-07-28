"""ETL DataPulse — orchestration + I/O (lit les sources, appelle `app/ml`, écrit le storage).

Cette couche ne contient PAS les maths (elles vivent dans `app/ml`, package validé
vendorisé) ni la persistance (elle vit dans `app/storage`). Elle sait *dans quel
ordre* enchaîner et *d'où vers où* déplacer la donnée. Voir docs/data-architecture.md.
"""
