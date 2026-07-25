import { useCallback, useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'
import DistributionChart from '../components/DistributionChart'
import AnomalyHistogram from '../components/AnomalyHistogram'
import SegmentedControl from '../components/SegmentedControl'

const TYPE_LABEL = { collective: 'Collective', duration: 'Durée', sequence: 'Séquence' }
const SEVERITY_LABEL = { alert: 'Alerte', critical: 'Critique' }
const DIRECTION_LABEL = { high: 'Haut', low: 'Bas' }
const SEVERITY_COLOR = {
  alert: 'var(--status-watch)',
  critical: 'var(--status-critical)',
}
const STATUS_LABEL = { open: 'Ouverte', acknowledged: 'Acquittée', resolved: 'Résolue' }
const BUCKETS = [
  { value: 'day', label: 'Jour' },
  { value: 'week', label: 'Semaine' },
  { value: 'month', label: 'Mois' },
]

const toRows = (obj = {}, labels) =>
  Object.entries(obj).map(([key, value]) => ({ key, label: labels[key] ?? key, value }))
const DIR_GLYPH = { high: '↑ haut', low: '↓ bas' }

function Stat({ label, value, suffix }) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-4)',
      }}
    >
      <div
        className="num"
        style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)' }}
      >
        {label}
      </div>
      <div className="num mt-2" style={{ fontSize: 26, fontWeight: 600, lineHeight: 1 }}>
        {value}
        {suffix && <span style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 400 }}> {suffix}</span>}
      </div>
    </div>
  )
}

function RowAction({ children, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="num"
      style={{
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: 'var(--tracking-wide)',
        padding: '4px 9px',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border)',
        background: 'transparent',
        color: disabled ? 'var(--text-muted)' : 'var(--accent-hover)',
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </button>
  )
}

export default function Anomalies() {
  const [bucket, setBucket] = useState('day')
  const [pending, setPending] = useState(null)
  const [actionError, setActionError] = useState(null)

  const stats = useApi(api.anomalyStats)
  const episodes = useApi(() => api.anomalies())
  const histogram = useApi(() => api.anomalyHistogram(bucket), [bucket])

  const changeStatus = useCallback(
    async (id, status) => {
      setPending(id)
      setActionError(null)
      try {
        await api.updateAnomalyStatus(id, status)
        episodes.reload()
      } catch (err) {
        setActionError(err)
      } finally {
        setPending(null)
      }
    },
    [episodes],
  )

  return (
    <div className="flex flex-col gap-6">
      <ApiState loading={stats.loading} error={stats.error}>
        {stats.data && (
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <Stat label="Total anomalies" value={stats.data.total} />
            <Stat label="Taux d’anomalies" value={stats.data.anomaly_rate_pct.toFixed(2)} suffix="%" />
            <Stat label="MTBA" value={stats.data.mtba_hours.toFixed(1)} suffix="h" />
            <Stat
              label="Top contributeur"
              value={stats.data.top_equipment}
              suffix={`× ${stats.data.top_equipment_count}`}
            />
          </div>
        )}
      </ApiState>

      <Panel
        title="Épisodes dans le temps"
        subtitle={`Comptes par ${bucket === 'day' ? 'jour' : bucket === 'week' ? 'semaine' : 'mois'}, empilés par sévérité`}
        actions={<SegmentedControl options={BUCKETS} value={bucket} onChange={setBucket} ariaLabel="Granularité" />}
      >
        <ApiState loading={histogram.loading} error={histogram.error}>
          {histogram.data && <AnomalyHistogram bins={histogram.data.bins} bucket={bucket} />}
        </ApiState>
      </Panel>

      <ApiState loading={stats.loading} error={stats.error}>
        {stats.data && (
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
            <Panel title="Par type" subtitle="Nature de l’épisode détecté">
              <DistributionChart data={toRows(stats.data.by_type, TYPE_LABEL)} />
            </Panel>
            <Panel title="Par sévérité" subtitle="Alerte / critique">
              <DistributionChart
                data={toRows(stats.data.by_severity, SEVERITY_LABEL)}
                colors={SEVERITY_COLOR}
                height={100}
              />
            </Panel>
            <Panel title="Par direction" subtitle="Dépassement haut / bas">
              <DistributionChart data={toRows(stats.data.by_direction, DIRECTION_LABEL)} height={100} />
            </Panel>
          </div>
        )}
      </ApiState>

      <Panel title="Épisodes récents" subtitle="Détection par hystérésis — seuils Tukey 27.85 / 30.40 °C">
        {actionError && (
          <p style={{ fontSize: 12, color: 'var(--status-critical)', marginBottom: 10 }}>
            Échec de la mise à jour : {actionError.message}
          </p>
        )}
        <ApiState loading={episodes.loading} error={episodes.error}>
          {episodes.data && (
            <div style={{ overflowX: 'auto' }}>
              <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: 12.5 }}>
                <thead>
                  <tr
                    className="num"
                    style={{
                      fontSize: 10,
                      letterSpacing: 'var(--tracking-caps)',
                      textTransform: 'uppercase',
                      color: 'var(--text-muted)',
                      textAlign: 'left',
                    }}
                  >
                    {['Début', 'Équipement', 'Type', 'Sévérité', 'Direction', 'Durée', 'Pic', 'Statut', 'Actions'].map((h) => (
                      <th key={h} style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {episodes.data.map((a) => (
                    <tr key={a.id} style={{ borderBottom: '1px solid var(--hairline)' }}>
                      <td className="num" style={{ padding: '9px 10px', whiteSpace: 'nowrap' }}>
                        {new Date(a.start).toLocaleString('fr-FR')}
                      </td>
                      <td style={{ padding: '9px 10px' }}>{a.equipment}</td>
                      <td style={{ padding: '9px 10px' }}>{TYPE_LABEL[a.type] ?? a.type}</td>
                      <td style={{ padding: '9px 10px' }}>
                        <StatusBadge status={a.severity === 'critical' ? 'critical' : 'alert'} />
                      </td>
                      <td className="num" style={{ padding: '9px 10px' }}>{DIR_GLYPH[a.direction] ?? a.direction}</td>
                      <td className="num" style={{ padding: '9px 10px' }}>{a.duration_min.toFixed(0)} min</td>
                      <td className="num" style={{ padding: '9px 10px' }}>{a.peak_value.toFixed(1)} °C</td>
                      <td className="num" style={{ padding: '9px 10px', color: 'var(--text-muted)' }}>
                        {STATUS_LABEL[a.status] ?? a.status}
                      </td>
                      <td style={{ padding: '9px 10px' }}>
                        <span className="flex gap-1.5">
                          <RowAction
                            onClick={() => changeStatus(a.id, 'acknowledged')}
                            disabled={pending === a.id || a.status !== 'open'}
                          >
                            Acquitter
                          </RowAction>
                          <RowAction
                            onClick={() => changeStatus(a.id, 'resolved')}
                            disabled={pending === a.id || a.status === 'resolved'}
                          >
                            Résoudre
                          </RowAction>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ApiState>
      </Panel>
    </div>
  )
}
