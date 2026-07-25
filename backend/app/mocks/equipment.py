"""Parc réel du site MSC-10.

Seuils Tukey directionnels du pipeline validé (temp_humidity,
SITE01_SALLE_SWITCH) — les mocks doivent rester cohérents avec eux.
"""

MILD_UPPER = 27.85   # °C — seuil "alerte"
EXTREME_UPPER = 30.40  # °C — seuil "critique"

STULZ_UNITS = [f"STULZ-{i:02d}" for i in range(1, 11)]      # 10× ASD 522 AS (2019)
SOCOMEC_UNITS = ["UPS-01", "UPS-02"]                        # 2× 200kVA (2020)
YANAN_UNITS = ["GEN-01", "GEN-02"]                          # 2× groupes (2025, baseline en cours)

ALL_UNITS = STULZ_UNITS + SOCOMEC_UNITS + YANAN_UNITS
