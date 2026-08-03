import { TrendingDown, TrendingUp, Minus } from 'lucide-react'

const fmtDelta = (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`

/** Flèche + valeur signée, colorée vert/rouge/neutre — delta d'un score (hausse = mieux). */
export default function DeltaTag({ value, suffix }) {
  const Icon = value > 0 ? TrendingUp : value < 0 ? TrendingDown : Minus
  const color = value > 0 ? 'var(--chart-healthy)' : value < 0 ? 'var(--chart-critical)' : 'var(--text-muted)'
  return (
    <span className="num flex items-center gap-1" style={{ fontSize: 12, color }}>
      <Icon size={14} /> {fmtDelta(value)} {suffix}
    </span>
  )
}
