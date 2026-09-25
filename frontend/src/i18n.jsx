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
      overview: 'Aperçu', overviewSub: 'Vue d’ensemble',
      siteHealth: 'Santé du site', siteHealthSub: 'Score & sous-scores',
      forecast: 'Prévision', forecastSub: 'Prédiction des pannes',
      anomalies: 'Anomalies', anomaliesSub: 'Détection',
      maintenance: 'Maintenance', maintenanceSub: 'Préventive',
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
      notifications: 'Notifications',
    },
    siteHealth: {
      title: 'Santé globale du site', subtitle: 'Score agrégé — {site}',
      scoreGlobal: 'Score global',
      decision: 'Couche d’aide à la décision : ce score synthétise l’état des familles d’équipement, il ne déclenche aucune action automatique.',
      summary: 'Sous-scores par domaine', evolutionGlobal: 'Évolution du score global',
      evolution: 'Évolution du score par sous-score',
      vsLast: 'vs. dernière mesure', rangeLabel: 'Fenêtre temporelle',
      d7: '7 j', d30: '30 j', d90: '90 j',
      domainEnvironment: 'Environnement', domainEnergy: 'Énergie', domainBattery: 'Batterie',
    },
    overview: {
      last24h: '24 dernières heures',
      scoreTitle: 'Score global', subScoresTitle: 'Sous-scores',
      nextFaultTitle: 'Prochaine panne prédite', nextFaultSub: 'Sur les 7 prochains jours',
      anomaliesTitle: 'Anomalies récentes', anomaliesSub: '{n} dernières entrées',
      viewAll: 'Voir tout',
    },
    forecast: {
      title: 'Global Health Score', subtitle: 'Historique + prévision — horizon {h}',
      horizonLabel: 'Horizon de prévision',
      h24: '24 h', d7: '7 jours', d30: '30 jours',
      crossings: '▲ {n} franchissement(s) de seuil prévu(s) sur cet horizon.',
      subScores: 'Prévision des sous-scores',
      nextFault: 'Prédiction des prochaines pannes',
      nextFaultSub: 'Fenêtre de risque estimée par famille — horizon {h}, à titre indicatif',
      noFaultPredicted: 'Aucune panne prévue',
      predictedAround: 'Estimée autour du {date}',
    },
    anomalies: {
      total: 'Total anomalies', rate: 'Taux d’anomalies', mtba: 'MTBA', top: 'Top contributeur',
      overview: 'Vue d’ensemble',
      windowLabel: 'Fenêtre', w24h: '24 h', w7d: '7 jours', vsPrevious: 'vs. période précédente',
      windowUpTo: '{w} — jusqu’au {d} (fin des données observées)',
      noneInWindow: 'Aucune anomalie détectée sur cette fenêtre. L’historique complet reste consultable ci-dessous.',
      rateWindow: 'Taux d’anomalies (fenêtre)', topFamily: 'Famille la plus contributrice',
      pieTitle: 'Répartition par modèle de détection', pieSub: 'Quel modèle génère le plus d’anomalies — fenêtre {w}',
      byDimension: 'Par dimension', dimEnvironment: 'Environnemental (HMM)', dimScada: 'Alarmes SCADA (IsolationForest)',
      familyStulz: 'Environnement', familySocomec: 'Énergie', familyYanan: 'Batterie', familyUnknown: '—',
      histTitle: 'Anomalies dans le temps', histSub: 'Comptes par période, empilés par sévérité',
      distTitle: 'Répartitions', distSub: 'Par type, sévérité, direction et statut',
      byType: 'Par type', bySeverity: 'Par sévérité', byDirection: 'Par direction', byStatus: 'Par statut',
      episodes: 'Épisodes récents', episodesSub: 'Détection par hystérésis — seuils Tukey 26.75 / 28.65 °C',
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
      kpiNext: 'Prochaine maintenance', kpiWeek: 'Maintenances cette semaine', kpiWeekSub: '7 prochains jours',
      noneScheduled: 'Aucune PM planifiée',
      overdueBy: 'En retard de {n} j', dueIn: 'Dans {n} j', dueToday: 'Aujourd’hui',
      calTitle: 'Calendrier des maintenances', calSub: 'Prochaines PM planifiées, par urgence — cliquer un jour pour voir le détail',
      formCreate: 'Planifier une PM', formEdit: 'Modifier {id}',
      readOnly: 'Démonstration en lecture seule',
      readOnlySub: 'Le formulaire est présenté à titre d’illustration : l’instance publique ne modifie pas le calendrier, que tous les visiteurs partagent.',
      formSub: 'Équipement · dernière PM · période · technicien · notes → date calculée',
      equipment: 'Équipement', selectEquipment: '— Choisir un équipement —',
      lastPm: 'Date de dernière PM', period: 'Période',
      assignedTo: 'Technicien assigné', assignedToHint: 'Nom du technicien', notes: 'Notes',
      days: 'jours', weeks: 'semaines', months: 'mois',
      compute: 'Calcul…', schedule: 'Planifier', update: 'Mettre à jour', delete: 'Supprimer', cancel: 'Annuler',
      fail: 'Échec : {msg}',
      editPmAria: 'Modifier la PM {equip} du {date}',
      dayDetailTitle: 'Détail du jour', dayDetailPrompt: 'Cliquez un jour du calendrier pour voir le détail.',
      dayDetailEmpty: 'Aucune PM planifiée ce jour.', modifyAction: 'Modifier',
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
      overview: 'Overview', overviewSub: 'At a glance',
      siteHealth: 'Site Health', siteHealthSub: 'Score & sub-scores',
      forecast: 'Forecast', forecastSub: 'Failure prediction',
      anomalies: 'Anomalies', anomaliesSub: 'Detection',
      maintenance: 'Maintenance', maintenanceSub: 'Preventive',
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
      notifications: 'Notifications',
    },
    siteHealth: {
      title: 'Overall site health', subtitle: 'Aggregate score — {site}',
      scoreGlobal: 'Global score',
      decision: 'Decision-support layer: this score summarizes the state of the equipment families; it triggers no automatic action.',
      summary: 'Sub-scores by domain', evolutionGlobal: 'Global score evolution',
      evolution: 'Score evolution by sub-score',
      vsLast: 'vs. last reading', rangeLabel: 'Time window',
      d7: '7 d', d30: '30 d', d90: '90 d',
      domainEnvironment: 'Environment', domainEnergy: 'Energy', domainBattery: 'Battery',
    },
    overview: {
      last24h: 'Last 24 hours',
      scoreTitle: 'Global score', subScoresTitle: 'Sub-scores',
      nextFaultTitle: 'Next predicted fault', nextFaultSub: 'Over the next 7 days',
      anomaliesTitle: 'Recent anomalies', anomaliesSub: 'Last {n} entries',
      viewAll: 'View all',
    },
    forecast: {
      title: 'Global Health Score', subtitle: 'History + forecast — {h} horizon',
      horizonLabel: 'Forecast horizon',
      h24: '24 h', d7: '7 days', d30: '30 days',
      crossings: '▲ {n} predicted threshold crossing(s) over this horizon.',
      subScores: 'Sub-score forecast',
      nextFault: 'Predicted upcoming faults',
      nextFaultSub: 'Estimated risk window by family — {h} horizon, indicative only',
      noFaultPredicted: 'No fault predicted',
      predictedAround: 'Estimated around {date}',
    },
    anomalies: {
      total: 'Total anomalies', rate: 'Anomaly rate', mtba: 'MTBA', top: 'Top contributor',
      overview: 'Overview',
      windowLabel: 'Window', w24h: '24 h', w7d: '7 days', vsPrevious: 'vs. previous period',
      windowUpTo: '{w} — up to {d} (end of observed data)',
      noneInWindow: 'No anomaly detected in this window. The full history is still available below.',
      rateWindow: 'Anomaly rate (window)', topFamily: 'Top contributing family',
      pieTitle: 'Breakdown by detection model', pieSub: 'Which model generates the most anomalies — {w} window',
      byDimension: 'By dimension', dimEnvironment: 'Environmental (HMM)', dimScada: 'SCADA alarms (IsolationForest)',
      familyStulz: 'Environment', familySocomec: 'Energy', familyYanan: 'Battery', familyUnknown: '—',
      histTitle: 'Anomalies over time', histSub: 'Counts per period, stacked by severity',
      distTitle: 'Distributions', distSub: 'By type, severity, direction and status',
      byType: 'By type', bySeverity: 'By severity', byDirection: 'By direction', byStatus: 'By status',
      episodes: 'Recent episodes', episodesSub: 'Hysteresis detection — Tukey thresholds 26.75 / 28.65 °C',
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
      kpiNext: 'Next maintenance', kpiWeek: 'Maintenance this week', kpiWeekSub: 'Next 7 days',
      noneScheduled: 'No PM scheduled',
      overdueBy: 'Overdue by {n}d', dueIn: 'In {n}d', dueToday: 'Today',
      calTitle: 'Maintenance calendar', calSub: 'Upcoming scheduled PMs, by urgency — click a day to see the detail',
      formCreate: 'Schedule a PM', formEdit: 'Edit {id}',
      readOnly: 'Read-only demonstration',
      readOnlySub: 'The form is shown for illustration: the public instance does not change the calendar, which every visitor shares.',
      formSub: 'Equipment · last PM · period · technician · notes → computed date',
      equipment: 'Equipment', selectEquipment: '— Choose equipment —',
      lastPm: 'Last PM date', period: 'Period',
      assignedTo: 'Assigned technician', assignedToHint: 'Technician name', notes: 'Notes',
      days: 'days', weeks: 'weeks', months: 'months',
      compute: 'Computing…', schedule: 'Schedule', update: 'Update', delete: 'Delete', cancel: 'Cancel',
      fail: 'Failed: {msg}',
      editPmAria: 'Edit the {equip} PM on {date}',
      dayDetailTitle: 'Day detail', dayDetailPrompt: 'Click a day on the calendar to see its detail.',
      dayDetailEmpty: 'No PM scheduled this day.', modifyAction: 'Edit',
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
