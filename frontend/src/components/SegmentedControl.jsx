/**
 * Sélecteur segmenté (horizon de prévision, granularité d'histogramme…).
 * options: [{ value, label }]
 */
export default function SegmentedControl({ options, value, onChange, ariaLabel }) {
  return (
    <div className="flex gap-1" role="group" aria-label={ariaLabel}>
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            aria-pressed={active}
            className="num"
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: '5px 12px',
              borderRadius: 'var(--radius-sm)',
              border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
              background: active ? 'var(--accent-soft)' : 'transparent',
              color: active ? 'var(--accent-hover)' : 'var(--text-muted)',
              cursor: 'pointer',
              transition: 'background var(--transition-fast), color var(--transition-fast)',
            }}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
