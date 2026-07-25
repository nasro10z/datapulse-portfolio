import StatusBadge from './StatusBadge'

const TREND = {
  up: { glyph: '↗', color: 'var(--status-healthy)', text: 'en hausse' },
  stable: { glyph: '→', color: 'var(--text-muted)', text: 'stable' },
  down: { glyph: '↘', color: 'var(--status-critical)', text: 'en baisse' },
}

/**
 * Card d'équipement / famille d'équipement : score, tendance, statut.
 */
export default function EquipmentCard({ label, score, status, trend, unitCount, note }) {
  const t = TREND[trend] ?? TREND.stable
  return (
    <article
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-4)',
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div style={{ fontSize: 'var(--fs-body-sm)', fontWeight: 'var(--fw-medium)' }}>
            {label}
          </div>
          {unitCount != null && (
            <div
              className="num"
              style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}
            >
              {unitCount} unité{unitCount > 1 ? 's' : ''}
            </div>
          )}
        </div>
        <StatusBadge status={status} />
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span
          className="num"
          style={{
            fontSize: 28,
            fontWeight: 'var(--fw-semibold)',
            letterSpacing: 'var(--tracking-tight)',
            lineHeight: 1,
          }}
        >
          {Number(score).toFixed(1)}
        </span>
        <span
          aria-label={`Tendance : ${t.text}`}
          style={{ color: t.color, fontSize: 15 }}
        >
          {t.glyph}
        </span>
      </div>

      {note && (
        <p style={{ fontSize: 'var(--fs-micro)', color: 'var(--text-muted)', marginTop: 8, lineHeight: 'var(--lh-normal)' }}>
          {note}
        </p>
      )}
    </article>
  )
}
