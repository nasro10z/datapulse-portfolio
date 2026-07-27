// Parc de sites (réseau TelcoNet — cf. design Identity v2). Seul MSC-10 est branché
// au backend ; les résumés ci-dessous alimentent la Vue globale (démonstration).
// MSC-10 est aligné sur le score réel du backend (~82).

export const SITES = [
  {
    id: 'msc10', name: 'MSC-10', operator: 'TelcoNet', assets: 14, connected: true,
    score: 82, status: 'healthy', legend: { healthy: 10, watch: 2, critical: 2 },
    anomalies7d: 4, nearestPMDays: 8, topFault: 'Santé batterie UPS-2',
  },
  {
    id: 'msc03', name: 'MSC-03', operator: 'TelcoNet', assets: 22, connected: false,
    score: 88, status: 'healthy', legend: { healthy: 18, watch: 3, critical: 1 },
    anomalies7d: 2, nearestPMDays: 21, topFault: null,
  },
  {
    id: 'bsc07', name: 'BSC-07', operator: 'TelcoNet', assets: 9, connected: false,
    score: 69, status: 'watch', legend: { healthy: 5, watch: 3, critical: 1 },
    anomalies7d: 6, nearestPMDays: 3, topFault: 'Surchauffe salle switch',
  },
]

export const findSite = (id) => SITES.find((s) => s.id === id)

// Agrégats flotte pour la Vue globale
export const fleet = {
  avg: Math.round(SITES.reduce((a, s) => a + s.score, 0) / SITES.length),
  assets: SITES.reduce((a, s) => a + s.assets, 0),
  anomalies7d: SITES.reduce((a, s) => a + s.anomalies7d, 0),
}

// Classement du plus à risque (score le plus bas) au plus sain
export const ranked = [...SITES].sort((a, b) => a.score - b.score)
export const worstSite = ranked[0]
export const soonestPM = SITES.reduce((m, s) => (s.nearestPMDays < m.nearestPMDays ? s : m), SITES[0])
