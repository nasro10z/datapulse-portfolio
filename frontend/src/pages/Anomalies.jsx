import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'
import DistributionChart from '../components/DistributionChart'

const TYPE_LABEL = { collective: 'Collective', duration: 'Durée', sequence: 'Séquence' }
const SEVERITY_LABEL = { alert: 'Alerte', critical: 'Critique' }
const DIRECTION_LABEL = { high: 'Haut', low: 'Bas' }
const SEVERITY_COLOR = {
  alert: 'var(--status-watch)',
  critical: 'var(--status-critical)',
}

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

export default function Anomalies() {
  const stats = useApi(api.anomalyStats)
  const episodes = useApi(() => api.anomalies())

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
                    {['Début', 'Équipement', 'Type', 'Sévérité', 'Direction', 'Durée', 'Pic', 'Statut'].map((h) => (
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
                      <td className="num" style={{ padding: '9px 10px', color: 'var(--text-muted)' }}>{a.status}</td>
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
