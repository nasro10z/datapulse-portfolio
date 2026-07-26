import { useMemo, useState } from 'react'

const WEEKDAYS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
const MONTHS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

// couleur du marqueur selon l'urgence (jours restants)
const urgencyColor = (days) =>
  days < 0 ? 'var(--status-critical)' : days <= 7 ? 'var(--status-watch)' : 'var(--accent)'

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

/**
 * Calendrier mensuel des prochaines PM — élément dominant de la page Maintenance.
 * entries: [{ id, equipment, next_pm_date, days_remaining }]
 */
export default function PMCalendar({ entries = [] }) {
  const today = new Date()
  const [view, setView] = useState({ year: today.getFullYear(), month: today.getMonth() })

  const byDate = useMemo(() => {
    const m = {}
    for (const e of entries) (m[e.next_pm_date] ??= []).push(e)
    return m
  }, [entries])

  const { cells } = useMemo(() => {
    const first = new Date(view.year, view.month, 1)
    const lead = (first.getDay() + 6) % 7 // lundi = 0
    const daysInMonth = new Date(view.year, view.month + 1, 0).getDate()
    const out = []
    for (let i = 0; i < lead; i++) out.push(null)
    for (let d = 1; d <= daysInMonth; d++) out.push(new Date(view.year, view.month, d))
    while (out.length % 7 !== 0) out.push(null)
    return { cells: out }
  }, [view])

  const shift = (delta) => {
    const m = view.month + delta
    setView({ year: view.year + Math.floor(m / 12), month: ((m % 12) + 12) % 12 })
  }

  const todayIso = iso(today)

  return (
    <div>
      <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 15, fontWeight: 600 }}>
          {MONTHS[view.month]} <span className="num" style={{ color: 'var(--text-muted)' }}>{view.year}</span>
        </div>
        <div className="flex gap-1">
          {[['‹', -1], ['Aujourd’hui', 0], ['›', 1]].map(([label, delta]) => (
            <button
              key={label}
              onClick={() => (delta === 0 ? setView({ year: today.getFullYear(), month: today.getMonth() }) : shift(delta))}
              className="num"
              style={{
                fontSize: 12, fontWeight: 600, padding: '5px 11px', borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6 }}>
        {WEEKDAYS.map((w) => (
          <div key={w} className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)', textAlign: 'center', paddingBottom: 4 }}>
            {w}
          </div>
        ))}
        {cells.map((d, i) => {
          if (!d) return <div key={i} />
          const key = iso(d)
          const pms = byDate[key] ?? []
          const isToday = key === todayIso
          return (
            <div
              key={i}
              style={{
                minHeight: 74,
                border: `1px solid ${isToday ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-sm)',
                background: isToday ? 'var(--accent-soft)' : 'var(--surface)',
                padding: '6px 7px',
                display: 'flex', flexDirection: 'column', gap: 4,
              }}
            >
              <div className="num" style={{ fontSize: 11, color: isToday ? 'var(--accent-hover)' : 'var(--text-muted)', fontWeight: isToday ? 600 : 400 }}>
                {d.getDate()}
              </div>
              {pms.map((pm) => (
                <div
                  key={pm.id}
                  title={`${pm.equipment} — PM ${key} (J−${pm.days_remaining})`}
                  className="num"
                  style={{
                    fontSize: 10, fontWeight: 600, lineHeight: 1.3,
                    padding: '2px 5px', borderRadius: 4,
                    background: 'var(--surface-inset)',
                    borderLeft: `3px solid ${urgencyColor(pm.days_remaining)}`,
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}
                >
                  {pm.equipment}
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
