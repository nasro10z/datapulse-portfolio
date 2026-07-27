import { useLang } from '../i18n'

const STATUS = {
  healthy: { color: 'var(--status-healthy)', bg: 'var(--status-healthy-soft)', icon: '●' },
  watch: { color: 'var(--status-watch)', bg: 'var(--status-watch-soft)', icon: '◆' },
  critical: { color: 'var(--status-critical)', bg: 'var(--status-critical-soft)', icon: '▲' },
  // Sévérités d'anomalie (mêmes familles visuelles)
  alert: { color: 'var(--status-watch)', bg: 'var(--status-watch-soft)', icon: '◆' },
  info: { color: 'var(--info)', bg: 'var(--accent-soft)', icon: '●' },
  warning: { color: 'var(--status-watch)', bg: 'var(--status-watch-soft)', icon: '◆' },
}

/**
 * Badge de statut / sévérité. Icône + libellé : l'état n'est jamais
 * porté par la couleur seule.
 */
export default function StatusBadge({ status, label, className = '' }) {
  const { t } = useLang()
  const s = STATUS[status] ?? STATUS.info
  return (
    <span
      className={`num inline-flex items-center gap-1.5 ${className}`}
      style={{
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: 'var(--tracking-wide)',
        textTransform: 'uppercase',
        padding: '3px 9px',
        borderRadius: 'var(--radius-pill)',
        background: s.bg,
        color: s.color,
      }}
    >
      <span aria-hidden="true" style={{ fontSize: 8 }}>{s.icon}</span>
      {label ?? t(`status.${status}`)}
    </span>
  )
}
