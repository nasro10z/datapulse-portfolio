import { useCallback, useEffect, useState } from 'react'

/**
 * Hook de fetch générique : { data, loading, error, reload }.
 * `fn` doit être stable ou dépendre de `deps`.
 */
export default function useApi(fn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fn()
      .then((d) => { if (!cancelled) setData(d) })
      .catch((e) => { if (!cancelled) setError(e) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => load(), [load])

  return { data, loading, error, reload: load }
}

export function ApiState({ loading, error, children }) {
  if (loading) {
    return (
      <div className="num" style={{ color: 'var(--text-muted)', fontSize: 12, padding: 24 }}>
        Chargement…
      </div>
    )
  }
  if (error) {
    return (
      <div
        style={{
          color: 'var(--status-critical)',
          background: 'var(--status-critical-soft)',
          border: '1px solid var(--status-critical)',
          borderRadius: 'var(--radius-sm)',
          fontSize: 12,
          padding: '12px 16px',
        }}
      >
        Erreur de chargement — le backend est-il lancé sur :8000 ? ({error.message})
      </div>
    )
  }
  return children
}
