import { useLang } from '../i18n'

/** Badge « dans N j / en retard de N j / aujourd'hui » pour une échéance de PM. */
export default function DueBadge({ days }) {
  const { t } = useLang()
  const color = days < 0 ? 'var(--status-critical)' : days <= 7 ? 'var(--status-watch)' : 'var(--text-muted)'
  const label = days < 0
    ? t('maintenance.overdueBy', { n: Math.abs(days) })
    : days === 0 ? t('maintenance.dueToday') : t('maintenance.dueIn', { n: days })
  return <span className="num" style={{ fontSize: 12, fontWeight: 600, color }}>{label}</span>
}
