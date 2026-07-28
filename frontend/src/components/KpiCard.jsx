/** Petite carte KPI générique : libellé + contenu libre. */
export default function KpiCard({ label, children }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)' }}>
      <div className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
        {label}
      </div>
      <div style={{ marginTop: 8 }}>{children}</div>
    </div>
  )
}
