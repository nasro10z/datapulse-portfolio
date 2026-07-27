/** Conteneur carte standard : surface, bordure, rayon du design system. */
export default function Panel({ title, subtitle, actions, children, className = '', style }) {
  return (
    <section
      className={className}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-card)',
        padding: 'var(--space-5)',
        ...style,
      }}
    >
      {(title || actions) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && (
              <h2
                style={{
                  fontSize: 'var(--fs-body)',
                  fontWeight: 'var(--fw-semibold)',
                  letterSpacing: 'var(--tracking-tight)',
                }}
              >
                {title}
              </h2>
            )}
            {subtitle && (
              <div
                className="num"
                style={{
                  fontSize: 10,
                  letterSpacing: 'var(--tracking-caps)',
                  textTransform: 'uppercase',
                  color: 'var(--text-muted)',
                  marginTop: 3,
                }}
              >
                {subtitle}
              </div>
            )}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  )
}
