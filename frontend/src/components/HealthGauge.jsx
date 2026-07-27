const STATUS_COLOR = {
  healthy: 'var(--status-healthy)',
  watch: 'var(--status-watch)',
  critical: 'var(--status-critical)',
}

/**
 * Gauge radiale de health score (0–100).
 * Arc de 270° ouvert vers le bas, valeur en chiffres tabulaires.
 */
export default function HealthGauge({ score, status = 'healthy', size = 180, label }) {
  const stroke = size * 0.06
  const r = (size - stroke) / 2
  const cx = size / 2
  const cy = size / 2
  const startAngle = 135
  const sweep = 270
  const clamped = Math.max(0, Math.min(100, score))
  const color = STATUS_COLOR[status] ?? STATUS_COLOR.healthy

  const arc = (angleStart, angleSweep) => {
    const a0 = ((angleStart - 90) * Math.PI) / 180
    const a1 = ((angleStart + angleSweep - 90) * Math.PI) / 180
    const x0 = cx + r * Math.cos(a0)
    const y0 = cy + r * Math.sin(a0)
    const x1 = cx + r * Math.cos(a1)
    const y1 = cy + r * Math.sin(a1)
    const large = angleSweep > 180 ? 1 : 0
    return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`
  }

  return (
    <div
      className="relative inline-flex items-center justify-center"
      role="img"
      aria-label={`Health score ${clamped.toFixed(1)} sur 100 — ${status}`}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size}>
        <path
          d={arc(startAngle, sweep)}
          fill="none"
          stroke="var(--surface-2)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d={arc(startAngle, (sweep * clamped) / 100)}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          style={{ transition: `stroke-dashoffset var(--transition-slow)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="num"
          style={{
            fontSize: size * 0.21,
            fontWeight: 'var(--fw-semibold)',
            letterSpacing: 'var(--tracking-tight)',
            lineHeight: 1,
          }}
        >
          {clamped.toFixed(1)}
        </span>
        {label && (
          <span
            className="num"
            style={{
              fontSize: 10,
              letterSpacing: 'var(--tracking-caps)',
              textTransform: 'uppercase',
              color: 'var(--text-muted)',
              marginTop: 6,
            }}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  )
}
