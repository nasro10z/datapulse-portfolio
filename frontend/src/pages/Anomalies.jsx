import { useMemo, useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'
import AnomalyHistogram from '../components/AnomalyHistogram'

const TYPE_LABEL = { collective: 'Collective', duration: 'Durée', sequence: 'Séquence' }
const DIR_LABEL = { high: '↑ Haut', low: '↓ Bas' }
const SEV_LABEL = { alert: 'Alerte', critical: 'Critique' }
const STATUS_LABEL = { open: 'Ouverte', acknowledged: 'Acquittée', resolved: 'Résolue' }
const BUCKETS = [
  { key: 'day', label: 'Jour' },
  { key: 'week', label: 'Semaine' },
  { key: 'month', label: 'Mois' },
]

const selectStyle = {
  background: 'var(--surface-inset)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text)',
  fontSize: 12.5,
  padding: '6px 9px',
}

function Stat({ label, value, suffix }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)' }}>
      <div className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
        {label}
      </div>
      <div className="num mt-2" style={{ fontSize: 26, fontWeight: 600, lineHeight: 1 }}>
        {value}
        {suffix && <span style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 400 }}> {suffix}</span>}
      </div>
    </div>
  )
}

/** Répartition : lignes de barres proportionnelles pour une ventilation catégorielle. */
function Distribution({ title, data, labels, color = 'var(--viz-1)' }) {
  const entries = Object.entries(data ?? {})
  const max = Math.max(1, ...entries.map(([, v]) => v))
  return (
    <div>
      <div className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10 }}>
        {title}
      </div>
      <div className="flex flex-col gap-2">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-center gap-3">
            <span style={{ fontSize: 12, width: 88, flex: 'none', color: 'var(--text-muted)' }}>{labels[k] ?? k}</span>
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
  const stats = useApi(api.anomalyStats)
  const [bucket, setBucket] = useState('day')
  const histogram = useApi(() => api.anomalyHistogram(bucket), [bucket])
  const [filters, setFilters] = useState({ equipment: '', severity: '' })
  const episodes = useApi(() => api.anomalies(filters), [filters.equipment, filters.severity])
  const options = useApi(api.anomalies) // liste complète, pour peupler le filtre équipement
  const [busyId, setBusyId] = useState(null)

  const equipmentOptions = useMemo(
    () => [...new Set((options.data ?? []).map((e) => e.equipment))].sort(),
    [options.data],
  )

  const act = async (id, status) => {
    setBusyId(id)
    try {
      await api.updateAnomalyStatus(id, status)
      episodes.reload()
      stats.reload()
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Stat cards */}
      <ApiState loading={stats.loading} error={stats.error}>
        {stats.data && (
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <Stat label="Total anomalies" value={stats.data.total} />
            <Stat label="Taux d’anomalies" value={stats.data.anomaly_rate_pct.toFixed(2)} suffix="%" />
            <Stat label="MTBA" value={stats.data.mtba_hours.toFixed(1)} suffix="h" />
            <Stat label="Top contributeur" value={stats.data.top_equipment} suffix={`× ${stats.data.top_equipment_count}`} />
          </div>
        )}
      </ApiState>

      {/* Histogramme temporel + sélecteur de granularité */}
      <Panel
        title="Anomalies dans le temps"
        subtitle="Comptes par période, empilés par sévérité"
        actions={
          <div className="flex gap-1" role="group" aria-label="Granularité de l’histogramme">
            {BUCKETS.map((b) => (
              <button
                key={b.key}
                onClick={() => setBucket(b.key)}
                className="num"
                style={{
                  fontSize: 11, fontWeight: 600, padding: '5px 12px', borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${b.key === bucket ? 'var(--accent)' : 'var(--border)'}`,
                  background: b.key === bucket ? 'var(--accent-soft)' : 'transparent',
                  color: b.key === bucket ? 'var(--accent-hover)' : 'var(--text-muted)', cursor: 'pointer',
                }}
              >
                {b.label}
              </button>
            ))}
          </div>
        }
      >
        <ApiState loading={histogram.loading} error={histogram.error}>
          {histogram.data && <AnomalyHistogram bins={histogram.data.bins} bucket={histogram.data.bucket} />}
        </ApiState>
      </Panel>

      {/* Répartitions */}
      <Panel title="Répartitions" subtitle="Par type, sévérité, direction et statut">
        <ApiState loading={stats.loading} error={stats.error}>
          {stats.data && (
            <div className="grid gap-8" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              <Distribution title="Par type" data={stats.data.by_type} labels={TYPE_LABEL} />
              <Distribution title="Par sévérité" data={stats.data.by_severity} labels={SEV_LABEL} />
              <Distribution title="Par direction" data={stats.data.by_direction} labels={DIR_LABEL} />
              <Distribution title="Par statut" data={stats.data.by_status} labels={STATUS_LABEL} color="var(--viz-2)" />
            </div>
          )}
        </ApiState>
      </Panel>

      {/* Table + filtres + actions */}
      <Panel
        title="Épisodes récents"
        subtitle="Détection par hystérésis — seuils Tukey 27.85 / 30.40 °C"
        actions={
          <div className="flex gap-2">
            <select aria-label="Filtrer par équipement" style={selectStyle}
              value={filters.equipment} onChange={(e) => setFilters({ ...filters, equipment: e.target.value })}>
              <option value="">Tous équipements</option>
              {equipmentOptions.map((eq) => <option key={eq} value={eq}>{eq}</option>)}
            </select>
            <select aria-label="Filtrer par sévérité" style={selectStyle}
              value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })}>
              <option value="">Toutes sévérités</option>
              <option value="alert">Alerte</option>
              <option value="critical">Critique</option>
            </select>
          </div>
        }
      >
        <ApiState loading={episodes.loading} error={episodes.error}>
          {episodes.data && (
            <div style={{ overflowX: 'auto' }}>
              {episodes.data.length === 0 && (
                <p style={{ fontSize: 12.5, color: 'var(--text-muted)', padding: '12px 0' }}>
                  Aucun épisode pour ces filtres.
                </p>
              )}
              {episodes.data.length > 0 && (
                <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: 12.5 }}>
                  <thead>
                    <tr className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)', textAlign: 'left' }}>
                      {['Début', 'Équipement', 'Type', 'Sévérité', 'Direction', 'Durée', 'Pic', 'Statut', ''].map((h, i) => (
                        <th key={i} style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {episodes.data.map((a) => (
                      <tr key={a.id} style={{ borderBottom: '1px solid var(--hairline)' }}>
                        <td className="num" style={{ padding: '9px 10px', whiteSpace: 'nowrap' }}>{new Date(a.start).toLocaleString('fr-FR')}</td>
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
                              <ActionButton label="Acquitter" busy={busyId === a.id} onClick={() => act(a.id, 'acknowledged')} />
                            )}
                            {a.status !== 'resolved' && (
                              <ActionButton label="Résoudre" variant="solid" busy={busyId === a.id} onClick={() => act(a.id, 'resolved')} />
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
