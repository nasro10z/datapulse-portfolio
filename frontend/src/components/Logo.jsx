export function LogoMark({ size = 22, accent = 'var(--accent)' }) {
  return (
    <svg
      width={size}
      height={size * (28 / 44)}
      viewBox="0 0 44 28"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M2 14h9l3.5-9 5 18 3.5-9H42"
        stroke={accent}
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="42" cy="14" r="2.6" fill="var(--success)" />
    </svg>
  )
}

export default function Logo({
  mutedColor = 'var(--text-muted)',
  boxBg = 'var(--surface-2)',
  boxBorder = 'var(--border)',
}) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="flex items-center justify-center"
        style={{ width: 36, height: 36, borderRadius: 10, background: boxBg, border: `1px solid ${boxBorder}` }}
      >
        <LogoMark />
      </div>
      <div style={{ lineHeight: 1 }}>
        <div style={{ fontSize: 16, fontWeight: 'var(--fw-semibold)', letterSpacing: 'var(--tracking-tight)' }}>
          DataPulse
        </div>
        <div
          className="num"
          style={{ fontSize: 9.5, letterSpacing: 'var(--tracking-caps)', color: mutedColor, marginTop: 3 }}
        >
          OPS PRÉDICTIVES
        </div>
      </div>
    </div>
  )
}
