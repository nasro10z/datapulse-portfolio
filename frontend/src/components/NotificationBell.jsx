import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { api } from '../api/client'
import useApi from '../hooks/useApi'
import { useLang } from '../i18n'
import StatusBadge from '../components/StatusBadge'

const SNOOZE = [
  { key: 'h1', hours: 1 },
  { key: 'd1', hours: 24 },
  { key: 'd7', hours: 168 },
]

const actionBtn = {
  fontSize: 10,
  fontWeight: 600,
  padding: '3px 8px',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text-muted)',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
}

/** Rappels présentés comme des notifications : cloche + badge de compte en
 * en-tête, popover listant les rappels avec leurs actions (plus de page dédiée). */
export default function NotificationBell() {
  const { t, locale } = useLang()
  const { pathname } = useLocation()
  const { data, reload } = useApi(api.reminders, [pathname])
  const [open, setOpen] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const wrapRef = useRef(null)

  const count = data?.length ?? 0

  useEffect(() => {
    if (!open) return
    const onDown = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false) }
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); window.removeEventListener('keydown', onKey) }
  }, [open])

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
    <div ref={wrapRef} className="relative" style={{ flex: 'none' }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={count > 0 ? t('layout.remindersActive', { n: count }) : t('layout.notifications')}
        style={{
          position: 'relative', width: 38, height: 38, display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'transparent', color: 'var(--text)', cursor: 'pointer',
        }}
      >
        <Bell size={16} aria-hidden="true" />
        {count > 0 && (
          <span className="num" aria-hidden="true"
            style={{
              position: 'absolute', top: -5, right: -5, minWidth: 16, height: 16, padding: '0 4px',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 9.5, fontWeight: 700, borderRadius: 'var(--radius-pill)', background: 'var(--chart-critical)', color: '#fff',
            }}>
            {count}
          </span>
        )}
      </button>

      {open && (
        <div
          role="dialog" aria-label={t('layout.notifications')}
          style={{
            position: 'absolute', top: '100%', right: 0, marginTop: 8, width: 360, maxHeight: 420, overflowY: 'auto',
            background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
            boxShadow: '0 12px 40px -8px rgba(0,0,0,.35)', zIndex: 30, padding: 8,
          }}
        >
          {(!data || data.length === 0) ? (
            <div className="flex flex-col items-center gap-1" style={{ padding: '28px 12px', textAlign: 'center' }}>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{t('reminders.emptyTitle')}</div>
              <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{t('reminders.emptyBody')}</div>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {data.map((r) => (
                <article key={r.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '10px 12px', opacity: busyId === r.id ? 0.55 : 1 }}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span style={{ fontSize: 12.5, fontWeight: 600 }}>{t(`reminders.${r.kind}`)}</span>
                    <span className="num" style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>{r.equipment}</span>
                    <StatusBadge status={r.severity} />
                  </div>
                  <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.45 }}>{r.message}</p>
                  <div className="num" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                    {t('common.dueAt', { date: new Date(r.due_at).toLocaleString(locale) })}
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5" style={{ marginTop: 8 }}>
                    <button
                      style={{ ...actionBtn, color: 'var(--accent-hover)', borderColor: 'var(--accent)', background: 'var(--accent-soft)' }}
                      disabled={busyId === r.id}
                      onClick={() => run(r.id, () => api.acknowledgeReminder(r.id))}
                    >
                      {t('reminders.acknowledge')}
                    </button>
                    {SNOOZE.map((s) => (
                      <button key={s.hours} style={actionBtn} disabled={busyId === r.id} onClick={() => run(r.id, () => api.snoozeReminder(r.id, s.hours))}>
                        {t('reminders.snooze')} {t(`reminders.${s.key}`)}
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
