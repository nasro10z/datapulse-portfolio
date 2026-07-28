/** Prochaine PM (la plus urgente) + nombre de PM sur les 7 prochains jours.
 * Dérivé de `calendar.data` côté client — mêmes données que le calendrier,
 * pas de calcul serveur dédié. Partagé entre Maintenance et Aperçu. */
export function maintenanceKpi(entries = []) {
  const sorted = [...entries].sort((a, b) => a.days_remaining - b.days_remaining)
  return {
    next: sorted[0] ?? null,
    thisWeekCount: entries.filter((e) => e.days_remaining >= 0 && e.days_remaining <= 7).length,
  }
}
