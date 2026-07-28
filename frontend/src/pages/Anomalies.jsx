import { useMemo, useState } from 'react'
import { PieChart, Pie, Cell, Legend, Tooltip as ReTooltip, ResponsiveContainer } from 'recharts'
import { TrendingDown, TrendingUp, Minus } from 'lucide-react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import { useLang } from '../i18n'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'

const WINDOWS = ['24h', '7d']
const WINDOW_KEY = { '24h': 'w24h', '7d': 'w7d' }
const FAMILY_LABEL_KEY = { stulz: 'familyStulz', socomec: 'familySocomec', yanan: 'familyYanan' }
const DIM_LABEL_KEY = { environment: 'dimEnvironment', scada: 'dimScada' }
const DIM_COLOR = { environment: 'var(--viz-1)', scada: 'var(--viz-4)' }

const selectStyle = {
  background: 'var(--surface-inset)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text)',
  fontSize: 12.5,
  padding: '6px 9px',
}

function Stat({ label, value, suffix, children }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)' }}>
      <div className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
        {label}
      </div>
      <div className="num mt-2" style={{ fontSize: 26, fontWeight: 600, lineHeight: 1 }}>
        {value}
        {suffix && <span style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 400 }}> {suffix}</span>}
      </div>
      {children && <div style={{ marginTop: 6 }}>{children}</div>}
    </div>
  )
}

/** Delta d'anomalies vs période précédente — plus d'anomalies = pire (inverse du sens santé). */
function AnomalyTrend({ current, previous, label }) {
  const delta = current - previous
  const Icon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus
  const color = delta > 0 ? 'var(--chart-critical)' : delta < 0 ? 'var(--chart-healthy)' : 'var(--text-muted)'
  return (
    <span className="num flex items-center gap-1" style={{ fontSize: 12, color }}>
      <Icon size={13} /> {delta > 0 ? '+' : ''}{delta} {label}
    </span>
  )
}

/** Répartition : lignes de barres proportionnelles pour une ventilation catégorielle. */
function Distribution({ title, data, labels, color = 'var(--viz-1)' }) {
  const entries = Object.entries(data ?? {})
  const max = Math.max(1, ...entries.map(([, v]) => v))
  return (
    <div>
      {title && (
        <div className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10 }}>
          {title}
        </div>
      )}
      <div className="flex flex-col gap-2">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-center gap-3">
            <span style={{ fontSize: 12, width: 160, flex: 'none', color: 'var(--text-muted)' }}>{labels[k] ?? k}</span>
            <div style={{ flex: 1, height: 8, background: 'var(--surface-inset)', borderRadius: 'var(--radius-pill)', overflow: 'hidden' }}>
              <div style={{ width: `${(v / max) * 100}%`, height: '100%', background: color, borderRadius: 'var(--radius-pill)' }} />
            </div>
            <span className="num" style={{ fontSize: 12.5, fontWeight: 600, width: 24, textAlign: 'right' }}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ActionButton({ label, onClick, busy, variant = 'ghost' }) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      className="num"
      style={{
        fontSize: 10.5,
        fontWeight: 600,
        padding: '4px 10px',
        borderRadius: 'var(--radius-sm)',
        border: `1px solid ${variant === 'solid' ? 'var(--accent)' : 'var(--border)'}`,
        background: variant === 'solid' ? 'var(--accent-soft)' : 'transparent',
        color: variant === 'solid' ? 'var(--accent-hover)' : 'var(--text-muted)',
        cursor: busy ? 'wait' : 'pointer',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </button>
  )
}

export default function Anomalies() {
  const { t, locale } = useLang()
  const TYPE_LABEL = { collective: t('anomalies.typeCollective'), duration: t('anomalies.typeDuration'), sequence: t('anomalies.typeSequence') }
  const DIR_LABEL = { high: t('anomalies.dirHigh'), low: t('anomalies.dirLow') }
  const SEV_LABEL = { alert: t('anomalies.sevAlert'), critical: t('anomalies.sevCritical') }
  const STATUS_LABEL = { open: t('anomalies.stOpen'), acknowledged: t('anomalies.stAck'), resolved: t('anomalies.stResolved') }
  const wLabel = (w) => t(`anomalies.${WINDOW_KEY[w]}`)

  const [window_, setWindow] = useState('24h')
  const windowStats = useApi(() => api.anomalyWindowStats(window_), [window_])
  const stats = useApi(api.anomalyStats)
  const [filters, setFilters] = useState({ equipment: '', severity: '' })
  const episodes = useApi(() => api.anomalies(filters), [filters.equipment, filters.severity])
  const options = useApi(api.anomalies) // liste complète, pour peupler le filtre équipement
  const [busyId, setBusyId] = useState(null)

  const equipmentOptions = useMemo(
    () => [...new Set((options.data ?? []).map((e) => e.equipment))].sort(),
    [options.data],
  )

  // La fenêtre se termine à la fin des DONNÉES observées, pas à l'heure courante
  // (export historique figé) : sans cette date affichée, un « 0 anomalie » se lit
  // comme une page cassée au lieu de « rien à signaler sur la période ».
  const windowSubtitle = windowStats.data?.reference_at
    ? t('anomalies.windowUpTo', {
        w: wLabel(window_),
        d: new Date(windowStats.data.reference_at).toLocaleString(locale),
      })
    : wLabel(window_)

  const pieData = useMemo(() => {
    if (!windowStats.data) return []
    return Object.entries(windowStats.data.by_dimension).map(([k, v]) => ({
      key: k, name: t(`anomalies.${DIM_LABEL_KEY[k]}`), value: v,
    }))
  }, [windowStats.data, t])

  const act = async (id, status) => {
    setBusyId(id)
    try {
      await api.updateAnomalyStatus(id, status)
      episodes.reload()
      stats.reload()
      windowStats.reload()
    } finally {
      setBusyId(null)
    }
  }

  const windowSelector = (
    <div className="flex gap-1" role="group" aria-label={t('anomalies.windowLabel')}>
      {WINDOWS.map((w) => (
        <button
          key={w}
          onClick={() => setWindow(w)}
          className="num"
          style={{
            fontSize: 11, fontWeight: 600, padding: '5px 12px', borderRadius: 'var(--radius-sm)',
            border: `1px solid ${w === window_ ? 'var(--accent)' : 'var(--border)'}`,
            background: w === window_ ? 'var(--accent-soft)' : 'transparent',
            color: w === window_ ? 'var(--accent-hover)' : 'var(--text-muted)', cursor: 'pointer',
          }}
        >
          {wLabel(w)}
        </button>
      ))}
    </div>
  )

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Total (fenêtre) + tendance, taux, famille la plus contributrice */}
      <Panel title={t('anomalies.overview')} subtitle={windowSubtitle} actions={windowSelector}>
        <ApiState loading={windowStats.loading} error={windowStats.error}>
          {windowStats.data && (
            <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
              <Stat label={t('anomalies.total')} value={windowStats.data.total}>
                <AnomalyTrend current={windowStats.data.total} previous={windowStats.data.previous_total} label={t('anomalies.vsPrevious')} />
              </Stat>
              <Stat label={t('anomalies.rateWindow')} value={windowStats.data.rate_pct.toFixed(2)} suffix="%" />
              <Stat
                label={t('anomalies.topFamily')}
                value={windowStats.data.top_family ? t(`anomalies.${FAMILY_LABEL_KEY[windowStats.data.top_family] ?? 'familyUnknown'}`) : t('anomalies.familyUnknown')}
                suffix={windowStats.data.top_family ? `× ${windowStats.data.top_family_count}` : undefined}
              />
            </div>
          )}
        </ApiState>
      </Panel>

      {/* 2. Pie chart : quel modèle génère le plus d'anomalies sur la fenêtre */}
      <Panel title={t('anomalies.pieTitle')} subtitle={t('anomalies.pieSub', { w: wLabel(window_) })}>
        <ApiState loading={windowStats.loading} error={windowStats.error}>
          {/* Total nul : un donut vide n'affiche qu'une légende orpheline —
              on dit explicitement qu'il n'y a rien à répartir. */}
          {windowStats.data && windowStats.data.total === 0 && (
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.6, padding: '24px 0' }}>
              {t('anomalies.noneInWindow')}
            </p>
          )}
          {windowStats.data && windowStats.data.total > 0 && (
            <div style={{ height: 240 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={3}>
                    {pieData.map((d) => <Cell key={d.key} fill={DIM_COLOR[d.key]} />)}
                  </Pie>
                  <ReTooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </ApiState>
      </Panel>

      {/* 3. Distribution par dimension (environnement / SCADA) */}
      <Panel title={t('anomalies.byDimension')} subtitle={wLabel(window_)}>
        <ApiState loading={windowStats.loading} error={windowStats.error}>
          {windowStats.data && (
            <Distribution
              data={windowStats.data.by_dimension}
              labels={{ environment: t('anomalies.dimEnvironment'), scada: t('anomalies.dimScada') }}
            />
          )}
        </ApiState>
      </Panel>

      {/* 4. Distribution par sévérité */}
      <Panel title={t('anomalies.bySeverity')} subtitle={t('anomalies.distSub')}>
        <ApiState loading={stats.loading} error={stats.error}>
          {stats.data && (
            <Distribution data={stats.data.by_severity} labels={SEV_LABEL} color="var(--viz-2)" />
          )}
        </ApiState>
      </Panel>

      {/* 5. Table détaillée + filtres + actions */}
      <Panel
        title={t('anomalies.episodes')}
        subtitle={t('anomalies.episodesSub')}
        actions={
          <div className="flex gap-2">
            <select aria-label={t('anomalies.filterEquip')} style={selectStyle}
              value={filters.equipment} onChange={(e) => setFilters({ ...filters, equipment: e.target.value })}>
              <option value="">{t('anomalies.allEquip')}</option>
              {equipmentOptions.map((eq) => <option key={eq} value={eq}>{eq}</option>)}
            </select>
            <select aria-label={t('anomalies.filterSev')} style={selectStyle}
              value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })}>
              <option value="">{t('anomalies.allSev')}</option>
              <option value="alert">{t('anomalies.sevAlert')}</option>
              <option value="critical">{t('anomalies.sevCritical')}</option>
            </select>
          </div>
        }
      >
        <ApiState loading={episodes.loading} error={episodes.error}>
          {episodes.data && (
            <div style={{ overflowX: 'auto' }}>
              {episodes.data.length === 0 && (
                <p style={{ fontSize: 12.5, color: 'var(--text-muted)', padding: '12px 0' }}>
                  {t('anomalies.empty')}
                </p>
              )}
              {episodes.data.length > 0 && (
                <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: 12.5 }}>
                  <thead>
                    <tr className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)', textAlign: 'left' }}>
                      {[t('anomalies.colStart'), t('anomalies.colEquip'), t('anomalies.colType'), t('anomalies.colSev'), t('anomalies.colDir'), t('anomalies.colDur'), t('anomalies.colPeak'), t('anomalies.colStatus'), ''].map((h, i) => (
                        <th key={i} style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {episodes.data.map((a) => (
                      <tr key={a.id} style={{ borderBottom: '1px solid var(--hairline)' }}>
                        <td className="num" style={{ padding: '9px 10px', whiteSpace: 'nowrap' }}>{new Date(a.start).toLocaleString(locale)}</td>
                        <td style={{ padding: '9px 10px' }}>{a.equipment}</td>
                        <td style={{ padding: '9px 10px' }}>{TYPE_LABEL[a.type] ?? a.type}</td>
                        <td style={{ padding: '9px 10px' }}>
                          <StatusBadge status={a.severity === 'critical' ? 'critical' : 'alert'} />
                        </td>
                        <td className="num" style={{ padding: '9px 10px' }}>{DIR_LABEL[a.direction] ?? a.direction}</td>
                        <td className="num" style={{ padding: '9px 10px' }}>{a.duration_min.toFixed(0)} min</td>
                        <td className="num" style={{ padding: '9px 10px' }}>{a.peak_value.toFixed(1)} °C</td>
                        <td className="num" style={{ padding: '9px 10px', color: 'var(--text-muted)' }}>{STATUS_LABEL[a.status] ?? a.status}</td>
                        <td style={{ padding: '9px 10px' }}>
                          <span className="flex gap-1.5 justify-end">
                            {a.status === 'open' && (
                              <ActionButton label={t('anomalies.acknowledge')} busy={busyId === a.id} onClick={() => act(a.id, 'acknowledged')} />
                            )}
                            {a.status !== 'resolved' && (
                              <ActionButton label={t('anomalies.resolve')} variant="solid" busy={busyId === a.id} onClick={() => act(a.id, 'resolved')} />
                            )}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </ApiState>
      </Panel>
    </div>
  )
}
