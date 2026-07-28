"""Score de santé du site + prévision — portage du notebook `health_scores.ipynb`.

Maths **pures** : ces modules prennent des DataFrames et renvoient des DataFrames.
Aucune I/O, aucun accès base — c'est `etl/score.py` et `etl/forecast.py` qui lisent
le silver et écrivent le gold (cf. `docs/data-architecture.md`).

Découpage :
  - `config.py`      — poids, seuils, mots-clés, dates de PM, versions ;
  - `features.py`    — helpers + construction des features horaires par domaine ;
  - `scoring.py`     — risques de base → scores par domaine → score global ;
  - `forecasting.py` — features de prévision + modèles (régression 6 h, chute).
"""
