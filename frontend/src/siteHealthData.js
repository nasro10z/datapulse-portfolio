// Données de démonstration de la page Santé du site, alignées sur la référence
// Identity v2 (sous-scores par domaine, pondérés → score global 81).
// Le backend expose les sous-scores par *famille* ; ces sous-scores par *domaine*
// (Environnement / Énergie / Batterie / Alarmes) viennent du design de référence.

export const statusFor = (s) => (s >= 82 ? 'healthy' : s >= 68 ? 'watch' : 'critical')

// couleurs feutrées de statut (chart/badges) — hex exacts du HTML de référence
export const STATUS_COLOR = {
  healthy: 'var(--chart-healthy)',
  watch: 'var(--chart-watch)',
  critical: 'var(--chart-critical)',
}
export const STATUS_HEX = { healthy: '#3FA69C', watch: '#B8823E', critical: '#C1443B' }

export const SUBSCORES = [
  { key: 'env', name: 'Environnement', score: 87, weight: 30, detail: 'Temp 23,4° · HR 46 % · 10 salles dans la plage' },
  { key: 'energy', name: 'Énergie', score: 81, weight: 25, detail: 'Charge onduleur 68 % · FP 0,98 · secteur stable' },
  { key: 'battery', name: 'Batterie', score: 66, weight: 25, detail: '2 chaînes · capacité UPS-2 en dégradation' },
  { key: 'alarms', name: 'Alarmes', score: 90, weight: 20, detail: '4 ouvertes · 0 critique · MTBA 14h' },
].map((s) => ({ ...s, status: statusFor(s.score) }))

export const GLOBAL_SCORE = Math.round(
  SUBSCORES.reduce((a, s) => a + (s.score * s.weight) / 100, 0),
) // = 81

export const LEGEND = { healthy: 9, watch: 3, critical: 2 } // 14 actifs

// Évolution 7 jours (J-6 → J-0), se termine sur les scores courants
export const EVOLUTION = [
  { day: 'J-6', env: 83, energy: 79, battery: 55, alarms: 84 },
  { day: 'J-5', env: 85, energy: 78, battery: 57, alarms: 87 },
  { day: 'J-4', env: 85, energy: 77, battery: 59, alarms: 86 },
  { day: 'J-3', env: 84, energy: 78, battery: 61, alarms: 85 },
  { day: 'J-2', env: 86, energy: 79, battery: 63, alarms: 88 },
  { day: 'J-1', env: 84, energy: 80, battery: 67, alarms: 86 },
  { day: 'J-0', env: 87, energy: 81, battery: 66, alarms: 90 },
]

export const SUBSCORE_LINE_COLOR = {
  env: '#3FA69C',
  energy: '#B8823E',
  battery: '#8FB0FF',
  alarms: '#C1443B',
}

// Par famille d'équipement (mini-tendance + score)
export const FAMILIES = [
  { name: 'STULZ ASD 522 AS · Climatisation', units: 10, score: 84, trend: -1, spark: [82, 85, 83, 86, 84, 87, 84] },
  { name: 'SOCOMEC 200 kVA · Onduleur', units: 2, score: 75, trend: -3, spark: [80, 78, 76, 79, 77, 78, 75] },
  { name: 'YANAN Diesel · Groupes électrogènes', units: 2, score: 83, trend: 0, spark: [81, 82, 84, 82, 83, 84, 83] },
]
