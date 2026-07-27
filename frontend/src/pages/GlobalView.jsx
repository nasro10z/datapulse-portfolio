import { useLang } from '../i18n'
import { SITES, fleet, ranked, worstSite, soonestPM } from '../sites'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'

const statusOf = (score) => (score >= 80 ? 'healthy' : score >= 55 ? 'watch' : 'critical')
const scoreColor = (score) => `var(--status-${statusOf(score)})`

function Kpi({ label, value, suffix, hint }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)' }}>
      <div className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)' }}>{label}</div>
      <div className="num mt-2" style={{ fontSize: 26, fontWeight: 600, lineHeight: 1 }}>
        {value}
        {suffix && <span style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 400 }}> {suffix}</span>}
      </div>
      {hint && <div className="num" style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 6 }}>{hint}</div>}
    </div>
  )
}

// pastilles de répartition (sain / à surveiller / critique)
function Legend({ legend }) {
  const items = [
    { n: legend.healthy, color: 'var(--status-healthy)' },
    { n: legend.watch, color: 'var(--status-watch)' },
    { n: legend.critical, color: 'var(--status-critical)' },
  ]
  return (
    <div className="flex items-center gap-2.5">
      {items.map((it, i) => (
        <span key={i} className="num flex items-center gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: it.color, display: 'inline-block' }} aria-hidden="true" />
          {it.n}
        </span>
      ))}
    </div>
  )
}

/**
 * Vue globale (persona manager) : agrégat de tous les sites + classement par
 * risque. Cliquer un site personnalise l'app sur ce site (onSelectSite).
 */
export default function GlobalView({ onSelectSite }) {
  const { t } = useLang()

  return (
    <div className="flex flex-col gap-6">
      {/* KPIs de flotte */}
      <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
        <Kpi label={t('global.fleetScore')} value={fleet.avg} suffix="/ 100" hint={t('status.' + statusOf(fleet.avg))} />
        <Kpi label={t('global.totalAssets')} value={fleet.assets} hint={`${SITES.length} sites`} />
        <Kpi label={t('global.anomalies7d')} value={fleet.anomalies7d} />
        <Kpi label={t('global.soonestPm')} value={soonestPM.name} hint={t('global.pmIn', { n: soonestPM.nearestPMDays })} />
      </div>

      {/* Insight risque */}
      <div style={{ background: 'var(--status-watch-soft)', border: '1px solid var(--status-watch)', borderRadius: 'var(--radius-md)', padding: '12px 16px', fontSize: 12.5, lineHeight: 1.55 }}>
        <StatusBadge status="watch" /> <span style={{ marginLeft: 6 }}>{t('global.insight', { site: worstSite.name })}</span>
      </div>

      {/* Classement des sites (plus à risque → plus sain) */}
      <Panel title={t('global.ranking')} subtitle={t('global.rankingSub')}>
        <div className="flex flex-col gap-3">
          {ranked.map((s, i) => (
            <button
              key={s.id}
              type="button"
              onClick={() => onSelectSite(s.id)}
              className="flex items-center gap-4"
              style={{ width: '100%', textAlign: 'left', background: 'var(--surface)', border: '1px solid var(--border)', borderLeft: `3px solid ${scoreColor(s.score)}`, borderRadius: 'var(--radius-md)', padding: '14px 16px', color: 'var(--text)', cursor: 'pointer' }}
              aria-label={t('global.openSite') + ' — ' + s.name}
            >
              <span className="num" style={{ fontSize: 12, color: 'var(--text-muted)', width: 18, flex: 'none' }}>#{i + 1}</span>
              <span className="num" style={{ fontSize: 28, fontWeight: 600, color: scoreColor(s.score), width: 44, flex: 'none', lineHeight: 1 }}>{s.score}</span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{s.name}</span>
                  <StatusBadge status={s.status} />
                  {!s.connected && <span className="num" style={{ fontSize: 8.5, color: 'var(--text-muted)', border: '1px solid var(--border)', borderRadius: 'var(--radius-pill)', padding: '1px 6px' }}>{t('layout.demo')}</span>}
                </span>
                <span className="num flex flex-wrap items-center gap-x-4 gap-y-1" style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>
                  <Legend legend={s.legend} />
                  <span>{t('global.anoms', { n: s.anomalies7d })}</span>
                  <span>{t('global.pmIn', { n: s.nearestPMDays })}</span>
                  {s.topFault && <span style={{ color: 'var(--text)' }}>⚠ {s.topFault}</span>}
                </span>
              </span>
              <span aria-hidden="true" style={{ flex: 'none', color: 'var(--text-muted)', fontSize: 18 }}>›</span>
            </button>
          ))}
        </div>
      </Panel>
    </div>
  )
}
