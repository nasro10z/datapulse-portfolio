import { useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import StatusBadge from '../components/StatusBadge'

const KIND_LABEL = {
  upcoming_pm: 'Maintenance à venir',
  threshold_approach: 'Seuil approchant',
  unacked_anomaly: 'Anomalie non acquittée',
}

const SEV_COLOR = {
  info: 'var(--info)',
  warning: 'var(--status-watch)',
  critical: 'var(--status-critical)',
}

const SNOOZE = [
  { label: '1 h', hours: 1 },
  { label: '1 j', hours: 24 },
  { label: '7 j', hours: 168 },
]

const actionBtn = {
  fontSize: 10.5,
  fontWeight: 600,
  padding: '4px 9px',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text-muted)',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
}

export default function Reminders() {
  const { data, loading, error, reload } = useApi(api.reminders)
  const [busyId, setBusyId] = useState(null)

  const run = async (id, fn) => {
    setBusyId(id)
    try {
      await fn()
      reload()
    } finally {
      setBusyId(null)
    }
  }

  return (
    <ApiState loading={loading} error={error}>
      {data && data.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-16">
          <div style={{ fontSize: 14, fontWeight: 500 }}>Tout est à jour</div>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>Aucun rappel actif dans cette vue.</div>
        </div>
      )}
      {data && data.length > 0 && (
        <div className="flex flex-col gap-3" style={{ maxWidth: 860 }}>
          {data.map((r) => (
            <article
              key={r.id}
              className="flex items-start gap-4"
              style={{
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderLeft: `3px solid ${SEV_COLOR[r.severity] ?? 'var(--info)'}`,
                borderRadius: 14,
                padding: '16px 18px',
                opacity: busyId === r.id ? 0.55 : 1,
              }}
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span style={{ fontSize: 13.5, fontWeight: 600 }}>{KIND_LABEL[r.kind] ?? r.kind}</span>
                  <span className="num" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{r.equipment}</span>
                  <StatusBadge status={r.severity} />
                </div>
                <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.55 }}>{r.message}</p>
                <div className="num" style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 6 }}>
                  Échéance : {new Date(r.due_at).toLocaleString('fr-FR')}
                </div>
              </div>

              <div className="flex flex-col items-end gap-1.5" style={{ flex: 'none' }}>
                <button
                  style={{ ...actionBtn, color: 'var(--accent-hover)', borderColor: 'var(--accent)', background: 'var(--accent-soft)' }}
                  disabled={busyId === r.id}
                  onClick={() => run(r.id, () => api.acknowledgeReminder(r.id))}
                >
                  Acquitter
                </button>
                <div className="flex items-center gap-1">
                  <span className="num" style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>Reporter</span>
                  {SNOOZE.map((s) => (
                    <button
                      key={s.hours}
                      style={actionBtn}
                      disabled={busyId === r.id}
                      onClick={() => run(r.id, () => api.snoozeReminder(r.id, s.hours))}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </ApiState>
  )
}
