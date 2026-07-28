"""Parc réel du site MSC-10.

Seuils Tukey directionnels livrés avec le modèle `environmental` (split train,
capteur SALLE_SWITCH — cf. `models/environmental/thresholds.json` du package
mlops-api). Les mocks doivent rester cohérents avec eux.
"""

MILD_UPPER = 26.75   # °C — seuil "alerte"   (q3 + 0.5·IQR)
EXTREME_UPPER = 28.65  # °C — seuil "critique" (q3 + 1.5·IQR)

STULZ_UNITS = [f"STULZ-{i:02d}" for i in range(1, 11)]      # 10× ASD 522 AS (2019)
SOCOMEC_UNITS = ["UPS-01", "UPS-02"]                        # 2× 200kVA (2020)
YANAN_UNITS = ["GEN-01", "GEN-02"]                          # 2× groupes (2025, baseline en cours)

ALL_UNITS = STULZ_UNITS + SOCOMEC_UNITS + YANAN_UNITS
