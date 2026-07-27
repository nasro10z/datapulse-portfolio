<<<<<<< HEAD
import { useMemo, useState } from 'react'
=======
import { useCallback, useState } from 'react'
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import { useLang } from '../i18n'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'
<<<<<<< HEAD
import AnomalyHistogram from '../components/AnomalyHistogram'

const BUCKETS = ['day', 'week', 'month']

const selectStyle = {
  background: 'var(--surface-inset)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text)',
  fontSize: 12.5,
  padding: '6px 9px',
}
=======
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
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a

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

<<<<<<< HEAD
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
=======
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
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a
    </button>
  )
}

export default function Anomalies() {
<<<<<<< HEAD
  const { t, locale } = useLang()
  const TYPE_LABEL = { collective: t('anomalies.typeCollective'), duration: t('anomalies.typeDuration'), sequence: t('anomalies.typeSequence') }
  const DIR_LABEL = { high: t('anomalies.dirHigh'), low: t('anomalies.dirLow') }
  const SEV_LABEL = { alert: t('anomalies.sevAlert'), critical: t('anomalies.sevCritical') }
  const STATUS_LABEL = { open: t('anomalies.stOpen'), acknowledged: t('anomalies.stAck'), resolved: t('anomalies.stResolved') }
  const BUCKET_LABEL = { day: t('anomalies.bucketDay'), week: t('anomalies.bucketWeek'), month: t('anomalies.bucketMonth') }

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
=======
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
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a

  return (
    <div className="flex flex-col gap-6">
      {/* Stat cards */}
      <ApiState loading={stats.loading} error={stats.error}>
        {stats.data && (
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <Stat label={t('anomalies.total')} value={stats.data.total} />
            <Stat label={t('anomalies.rate')} value={stats.data.anomaly_rate_pct.toFixed(2)} suffix="%" />
            <Stat label={t('anomalies.mtba')} value={stats.data.mtba_hours.toFixed(1)} suffix="h" />
            <Stat label={t('anomalies.top')} value={stats.data.top_equipment} suffix={`× ${stats.data.top_equipment_count}`} />
          </div>
        )}
      </ApiState>

<<<<<<< HEAD
      {/* Histogramme temporel + sélecteur de granularité */}
      <Panel
        title={t('anomalies.histTitle')}
        subtitle={t('anomalies.histSub')}
        actions={
          <div className="flex gap-1" role="group" aria-label={t('anomalies.bucketGroup')}>
            {BUCKETS.map((b) => (
              <button
                key={b}
                onClick={() => setBucket(b)}
                className="num"
                style={{
                  fontSize: 11, fontWeight: 600, padding: '5px 12px', borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${b === bucket ? 'var(--accent)' : 'var(--border)'}`,
                  background: b === bucket ? 'var(--accent-soft)' : 'transparent',
                  color: b === bucket ? 'var(--accent-hover)' : 'var(--text-muted)', cursor: 'pointer',
                }}
              >
                {BUCKET_LABEL[b]}
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
      <Panel title={t('anomalies.distTitle')} subtitle={t('anomalies.distSub')}>
        <ApiState loading={stats.loading} error={stats.error}>
          {stats.data && (
            <div className="grid gap-8" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              <Distribution title={t('anomalies.byType')} data={stats.data.by_type} labels={TYPE_LABEL} />
              <Distribution title={t('anomalies.bySeverity')} data={stats.data.by_severity} labels={SEV_LABEL} />
              <Distribution title={t('anomalies.byDirection')} data={stats.data.by_direction} labels={DIR_LABEL} />
              <Distribution title={t('anomalies.byStatus')} data={stats.data.by_status} labels={STATUS_LABEL} color="var(--viz-2)" />
            </div>
          )}
        </ApiState>
      </Panel>

      {/* Table + filtres + actions */}
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
=======
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
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a
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
