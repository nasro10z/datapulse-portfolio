import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const STORAGE_KEY = 'datapulse-lang'
export const LANGS = ['fr', 'en']

// Chaînes de l'interface. Le contenu servi par l'API (libellés de familles,
// messages de rappels…) reste dans sa langue source (i18n backend hors périmètre).
const DICT = {
  fr: {
    common: {
      loading: 'Chargement…',
      loadError: 'Erreur de chargement — le backend est-il lancé sur :8000 ? ({msg})',
      updatedAt: 'Mis à jour : {date}',
      dueAt: 'Échéance : {date}',
      units: '{n} actifs',
      today: 'Aujourd’hui',
    },
    nav: {
      section: 'Surveillance',
      siteHealth: 'Santé du site', siteHealthSub: 'Vue d’ensemble',
      forecast: 'Prévision', forecastSub: 'Prédiction des pannes',
      anomalies: 'Anomalies', anomaliesSub: 'Détection',
      maintenance: 'Maintenance', maintenanceSub: 'Préventive',
      reminders: 'Rappels', remindersSub: 'Rappels actifs',
    },
    layout: {
      openMenu: 'Ouvrir le menu', closeMenu: 'Fermer le menu',
      toLight: 'Basculer en mode clair', toDark: 'Basculer en mode sombre',
      light: 'CLAIR', dark: 'SOMBRE',
      language: 'Langue', changeLanguage: 'Changer de langue',
      siteActive: 'Site actif : {name}. Changer de site',
      chooseSite: 'Choisir un site', demo: 'DÉMO',
      siteComingTitle: '{name} — intégration à venir',
      siteComingBody: 'Ce site fait partie du réseau {operator} ({assets} actifs) mais n’est pas encore branché au pipeline de données. Sélectionnez MSC-10 pour la démonstration.',
      remindersActive: '{n} rappel(s) actif(s)', synced: 'SYNCHRONISÉ',
    },
    siteHealth: {
      title: 'Santé globale du site', subtitle: 'Score agrégé — {site}',
      scoreGlobal: 'Score global',
      decision: 'Couche d’aide à la décision : ce score synthétise l’état des familles d’équipement, il ne déclenche aucune action automatique.',
      summary: 'Résumé des sous-scores', evolution: 'Évolution du score par sous-score',
      weight: 'Poids', detail: 'Détail des sous-scores', byFamily: 'Par famille d’équipement',
    },
    forecast: {
      title: 'Global Health Score', subtitle: 'Historique + prévision — horizon {h}',
      horizonLabel: 'Horizon de prévision',
      h24: '24 h', d7: '7 jours', d30: '30 jours',
      crossings: '▲ {n} franchissement(s) de seuil prévu(s) sur cet horizon.',
      subScores: 'Sous-scores par famille d’équipement',
    },
    anomalies: {
      total: 'Total anomalies', rate: 'Taux d’anomalies', mtba: 'MTBA', top: 'Top contributeur',
      histTitle: 'Anomalies dans le temps', histSub: 'Comptes par période, empilés par sévérité',
      distTitle: 'Répartitions', distSub: 'Par type, sévérité, direction et statut',
      byType: 'Par type', bySeverity: 'Par sévérité', byDirection: 'Par direction', byStatus: 'Par statut',
      episodes: 'Épisodes récents', episodesSub: 'Détection par hystérésis — seuils Tukey 27.85 / 30.40 °C',
      allEquip: 'Tous équipements', allSev: 'Toutes sévérités',
      filterEquip: 'Filtrer par équipement', filterSev: 'Filtrer par sévérité',
      empty: 'Aucun épisode pour ces filtres.',
      acknowledge: 'Acquitter', resolve: 'Résoudre',
      bucketDay: 'Jour', bucketWeek: 'Semaine', bucketMonth: 'Mois', bucketGroup: 'Granularité de l’histogramme',
      histEmpty: 'Aucune donnée sur la fenêtre.', sevAlert: 'Alerte', sevCritical: 'Critique',
      hoverAnoms: '{n} anomalie(s)', hoverCrit: '{n} critique(s)',
      colStart: 'Début', colEquip: 'Équipement', colType: 'Type', colSev: 'Sévérité',
      colDir: 'Direction', colDur: 'Durée', colPeak: 'Pic', colStatus: 'Statut',
      typeCollective: 'Collective', typeDuration: 'Durée', typeSequence: 'Séquence',
      dirHigh: '↑ Haut', dirLow: '↓ Bas',
      stOpen: 'Ouverte', stAck: 'Acquittée', stResolved: 'Résolue',
    },
    maintenance: {
      calTitle: 'Calendrier des maintenances', calSub: 'Prochaines PM planifiées, par urgence — cliquer une PM pour la modifier',
      formCreate: 'Planifier une PM', formEdit: 'Modifier {id}', formSub: 'Équipement · dernière PM · période → date calculée',
      equipment: 'Équipement', lastPm: 'Date de dernière PM', period: 'Période',
      days: 'jours', weeks: 'semaines', months: 'mois',
      compute: 'Calcul…', schedule: 'Planifier', update: 'Mettre à jour', delete: 'Supprimer', cancel: 'Annuler',
      fail: 'Échec : {msg}',
      editPmAria: 'Modifier la PM {equip} du {date}',
    },
    reminders: {
      upcoming_pm: 'Maintenance à venir', threshold_approach: 'Seuil approchant', unacked_anomaly: 'Anomalie non acquittée',
      emptyTitle: 'Tout est à jour', emptyBody: 'Aucun rappel actif dans cette vue.',
      acknowledge: 'Acquitter', snooze: 'Reporter', h1: '1 h', d1: '1 j', d7: '7 j',
    },
    status: { healthy: 'Sain', watch: 'À surveiller', critical: 'Critique', alert: 'Alerte', info: 'Info', warning: 'Alerte' },
    trend: { up: 'en hausse', stable: 'stable', down: 'en baisse', label: 'Tendance : {t}' },
    global: {
      title: 'Vue globale', sub: '{n} sites · réseau TelcoNet', option: 'Vue globale',
      fleetScore: 'Score de flotte', totalAssets: 'Actifs surveillés', anomalies7d: 'Anomalies (7 j)', soonestPm: 'PM la plus proche',
      ranking: 'Classement des sites', rankingSub: 'Du plus à risque au plus sain',
      insight: '{site} présente la santé de flotte la plus basse et la maintenance planifiée la plus proche — à prioriser.',
      topFault: 'Défaut principal', pmIn: 'PM dans {n} j', anoms: '{n} anomalies / 7 j',
      openSite: 'Ouvrir le site', backToGlobal: 'Retour à la vue globale', demoNote: 'Données de démonstration',
    },
  },
  en: {
    common: {
      loading: 'Loading…',
      loadError: 'Failed to load — is the backend running on :8000? ({msg})',
      updatedAt: 'Updated: {date}',
      dueAt: 'Due: {date}',
      units: '{n} assets',
      today: 'Today',
    },
    nav: {
      section: 'Monitoring',
      siteHealth: 'Site Health', siteHealthSub: 'Overview',
      forecast: 'Forecast', forecastSub: 'Failure prediction',
      anomalies: 'Anomalies', anomaliesSub: 'Detection',
      maintenance: 'Maintenance', maintenanceSub: 'Preventive',
      reminders: 'Reminders', remindersSub: 'Active reminders',
    },
    layout: {
      openMenu: 'Open menu', closeMenu: 'Close menu',
      toLight: 'Switch to light mode', toDark: 'Switch to dark mode',
      light: 'LIGHT', dark: 'DARK',
      language: 'Language', changeLanguage: 'Change language',
      siteActive: 'Active site: {name}. Change site',
      chooseSite: 'Choose a site', demo: 'DEMO',
      siteComingTitle: '{name} — integration coming soon',
      siteComingBody: 'This site belongs to the {operator} network ({assets} assets) but is not yet connected to the data pipeline. Select MSC-10 for the demo.',
      remindersActive: '{n} active reminder(s)', synced: 'SYNCED',
    },
    siteHealth: {
      title: 'Overall site health', subtitle: 'Aggregate score — {site}',
      scoreGlobal: 'Global score',
      decision: 'Decision-support layer: this score summarizes the state of the equipment families; it triggers no automatic action.',
      summary: 'Sub-score summary', evolution: 'Score evolution by sub-score',
      weight: 'Weight', detail: 'Sub-score detail', byFamily: 'By equipment family',
    },
    forecast: {
      title: 'Global Health Score', subtitle: 'History + forecast — {h} horizon',
      horizonLabel: 'Forecast horizon',
      h24: '24 h', d7: '7 days', d30: '30 days',
      crossings: '▲ {n} predicted threshold crossing(s) over this horizon.',
      subScores: 'Sub-scores by equipment family',
    },
    anomalies: {
      total: 'Total anomalies', rate: 'Anomaly rate', mtba: 'MTBA', top: 'Top contributor',
      histTitle: 'Anomalies over time', histSub: 'Counts per period, stacked by severity',
      distTitle: 'Distributions', distSub: 'By type, severity, direction and status',
      byType: 'By type', bySeverity: 'By severity', byDirection: 'By direction', byStatus: 'By status',
      episodes: 'Recent episodes', episodesSub: 'Hysteresis detection — Tukey thresholds 27.85 / 30.40 °C',
      allEquip: 'All equipment', allSev: 'All severities',
      filterEquip: 'Filter by equipment', filterSev: 'Filter by severity',
      empty: 'No episode for these filters.',
      acknowledge: 'Acknowledge', resolve: 'Resolve',
      bucketDay: 'Day', bucketWeek: 'Week', bucketMonth: 'Month', bucketGroup: 'Histogram granularity',
      histEmpty: 'No data in the window.', sevAlert: 'Alert', sevCritical: 'Critical',
      hoverAnoms: '{n} anomaly(ies)', hoverCrit: '{n} critical',
      colStart: 'Start', colEquip: 'Equipment', colType: 'Type', colSev: 'Severity',
      colDir: 'Direction', colDur: 'Duration', colPeak: 'Peak', colStatus: 'Status',
      typeCollective: 'Collective', typeDuration: 'Duration', typeSequence: 'Sequence',
      dirHigh: '↑ High', dirLow: '↓ Low',
      stOpen: 'Open', stAck: 'Acknowledged', stResolved: 'Resolved',
    },
    maintenance: {
      calTitle: 'Maintenance calendar', calSub: 'Upcoming scheduled PMs, by urgency — click a PM to edit it',
      formCreate: 'Schedule a PM', formEdit: 'Edit {id}', formSub: 'Equipment · last PM · period → computed date',
      equipment: 'Equipment', lastPm: 'Last PM date', period: 'Period',
      days: 'days', weeks: 'weeks', months: 'months',
      compute: 'Computing…', schedule: 'Schedule', update: 'Update', delete: 'Delete', cancel: 'Cancel',
      fail: 'Failed: {msg}',
      editPmAria: 'Edit the {equip} PM on {date}',
    },
    reminders: {
      upcoming_pm: 'Upcoming maintenance', threshold_approach: 'Threshold approaching', unacked_anomaly: 'Unacknowledged anomaly',
      emptyTitle: 'All caught up', emptyBody: 'No active reminder in this view.',
      acknowledge: 'Acknowledge', snooze: 'Snooze', h1: '1 h', d1: '1 d', d7: '7 d',
    },
    status: { healthy: 'Healthy', watch: 'Watch', critical: 'Critical', alert: 'Alert', info: 'Info', warning: 'Warning' },
    trend: { up: 'rising', stable: 'stable', down: 'falling', label: 'Trend: {t}' },
    global: {
      title: 'Global view', sub: '{n} sites · TelcoNet network', option: 'Global view',
      fleetScore: 'Fleet score', totalAssets: 'Monitored assets', anomalies7d: 'Anomalies (7d)', soonestPm: 'Nearest PM',
      ranking: 'Site ranking', rankingSub: 'From most at-risk to healthiest',
      insight: '{site} has the lowest fleet health and the nearest scheduled maintenance — prioritize it.',
      topFault: 'Top fault', pmIn: 'PM in {n}d', anoms: '{n} anomalies / 7d',
      openSite: 'Open site', backToGlobal: 'Back to global view', demoNote: 'Demonstration data',
    },
  },
}

const LangContext = createContext(null)

function initialLang() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'fr'
  } catch {
    return 'fr'
  }
}

function resolve(dict, key) {
  return key.split('.').reduce((o, k) => (o == null ? undefined : o[k]), dict)
}

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(initialLang)

  useEffect(() => {
    document.documentElement.setAttribute('lang', lang)
    try {
      localStorage.setItem(STORAGE_KEY, lang)
    } catch {
      // stockage indisponible
    }
  }, [lang])

  const t = useCallback(
    (key, vars) => {
      let str = resolve(DICT[lang], key)
      if (str == null) str = resolve(DICT.fr, key) ?? key
      if (vars) for (const [k, v] of Object.entries(vars)) str = str.replaceAll(`{${k}}`, v)
      return str
    },
    [lang],
  )

  const setLang = useCallback((l) => setLangState(LANGS.includes(l) ? l : 'fr'), [])

  const locale = lang === 'en' ? 'en-GB' : 'fr-FR'

  return <LangContext.Provider value={{ lang, setLang, t, locale }}>{children}</LangContext.Provider>
}

export function useLang() {
  const ctx = useContext(LangContext)
  if (!ctx) throw new Error('useLang doit être utilisé dans <LangProvider>')
  return ctx
}
