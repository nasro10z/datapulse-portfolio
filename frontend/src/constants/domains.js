/** Couleurs/libellés partagés pour les statuts et la décomposition par domaine
 * (environment/energy/battery) — Site Health, Prévision, Aperçu. */

export const STATUS_CHART_COLOR = {
  healthy: 'var(--chart-healthy)',
  watch: 'var(--chart-watch)',
  critical: 'var(--chart-critical)',
}

export const DOMAIN_LABEL_KEY = { environment: 'domainEnvironment', energy: 'domainEnergy', battery: 'domainBattery' }

// Présentation « par domaine » des scores par famille d'équipement (STULZ/SOCOMEC/YANAN)
// — mêmes données, libellé différent (cf. décision session Prévision).
export const FAMILY_DOMAIN_LABEL_KEY = { stulz: 'domainEnvironment', socomec: 'domainEnergy', yanan: 'domainBattery' }
