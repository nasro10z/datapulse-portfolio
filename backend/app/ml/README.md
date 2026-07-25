# app/ml — pipelines ML

Ce package accueillera le pipeline validé (preprocessing, segmentation, détection
PELT, forecasting) lors de la Phase 8. Règle du projet : `ml/` (logique
données/modèles) reste strictement séparé de `api/` (exposition REST). Les routes
appellent des fonctions de `ml/` (ou `mocks/` en attendant), jamais l'inverse.
