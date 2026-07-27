import { useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import { useLang } from '../i18n'
import StatusBadge from '../components/StatusBadge'

const SEV_COLOR = {
  info: 'var(--info)',
  warning: 'var(--status-watch)',
  critical: 'var(--status-critical)',
}

const SNOOZE = [
  { key: 'h1', hours: 1 },
  { key: 'd1', hours: 24 },
  { key: 'd7', hours: 168 },
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
  const { t, locale } = useLang()
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
          <div style={{ fontSize: 14, fontWeight: 500 }}>{t('reminders.emptyTitle')}</div>
          <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{t('reminders.emptyBody')}</div>
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
                  <span style={{ fontSize: 13.5, fontWeight: 600 }}>{t(`reminders.${r.kind}`)}</span>
                  <span className="num" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{r.equipment}</span>
                  <StatusBadge status={r.severity} />
                </div>
                <p style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.55 }}>{r.message}</p>
                <div className="num" style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 6 }}>
                  {t('common.dueAt', { date: new Date(r.due_at).toLocaleString(locale) })}
                </div>
              </div>

              <div className="flex flex-col items-end gap-1.5" style={{ flex: 'none' }}>
                <button
                  style={{ ...actionBtn, color: 'var(--accent-hover)', borderColor: 'var(--accent)', background: 'var(--accent-soft)' }}
                  disabled={busyId === r.id}
                  onClick={() => run(r.id, () => api.acknowledgeReminder(r.id))}
                >
                  {t('reminders.acknowledge')}
                </button>
                <div className="flex items-center gap-1">
                  <span className="num" style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>{t('reminders.snooze')}</span>
                  {SNOOZE.map((s) => (
                    <button
                      key={s.hours}
                      style={actionBtn}
                      disabled={busyId === r.id}
                      onClick={() => run(r.id, () => api.snoozeReminder(r.id, s.hours))}
                    >
                      {t(`reminders.${s.key}`)}
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
