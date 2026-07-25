const STATUS = {
  healthy: { label: 'Healthy', color: 'var(--status-healthy)', bg: 'var(--status-healthy-soft)', icon: '●' },
  watch: { label: 'Watch', color: 'var(--status-watch)', bg: 'var(--status-watch-soft)', icon: '◆' },
  critical: { label: 'Critical', color: 'var(--status-critical)', bg: 'var(--status-critical-soft)', icon: '▲' },
  // Sévérités d'anomalie (mêmes familles visuelles, libellés dédiés)
  alert: { label: 'Alerte', color: 'var(--status-watch)', bg: 'var(--status-watch-soft)', icon: '◆' },
  info: { label: 'Info', color: 'var(--info)', bg: 'var(--accent-soft)', icon: '●' },
  warning: { label: 'Warning', color: 'var(--status-watch)', bg: 'var(--status-watch-soft)', icon: '◆' },
}

/**
 * Badge de statut / sévérité. Icône + libellé : l'état n'est jamais
 * porté par la couleur seule.
 */
export default function StatusBadge({ status, label, className = '' }) {
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
      {label ?? s.label}
    </span>
  )
}
