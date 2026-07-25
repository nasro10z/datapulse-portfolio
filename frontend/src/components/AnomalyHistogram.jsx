import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const fmtBucket = (ts, bucket) => {
  const d = new Date(ts)
  if (bucket === 'month') return d.toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })
  if (bucket === 'week') return `sem. ${d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}`
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })
}

function HistogramTooltip({ active, payload, label, bucket }) {
  if (!active || !payload?.length) return null
  const bin = payload[0].payload
  return (
    <div
      style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-sm)',
        padding: '9px 11px',
        boxShadow: '0 8px 24px -10px rgba(0,0,0,.45)',
      }}
    >
      <div className="num" style={{ fontSize: 10, color: 'var(--text-muted)' }}>
        {fmtBucket(label, bucket)}
      </div>
      <div className="num" style={{ fontSize: 13, fontWeight: 600, marginTop: 3, color: 'var(--text)' }}>
        {bin.total} épisode{bin.total > 1 ? 's' : ''}
      </div>
      <div className="num" style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 2 }}>
        {bin.alert} alerte{bin.alert > 1 ? 's' : ''} · {bin.critical} critique{bin.critical > 1 ? 's' : ''}
      </div>
    </div>
  )
}

/**
 * Histogramme des épisodes dans le temps, empilé par sévérité.
 * Les couleurs de statut sont réservées : ici les catégories SONT des
 * sévérités, leur usage est donc légitime.
 */
export default function AnomalyHistogram({ bins = [], bucket = 'day', height = 240 }) {
  if (!bins.length) {
    return (
      <div className="num" style={{ color: 'var(--text-muted)', fontSize: 12, padding: 24 }}>
        Aucune donnée
      </div>
    )
  }

  const data = bins.map((b) => ({ ...b, t: new Date(b.period_start).getTime() }))
  const axisStyle = { fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--chart-axis)' }

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -12 }} barCategoryGap="18%">
          <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
          <XAxis
            dataKey="t"
            tickFormatter={(t) => fmtBucket(t, bucket)}
            tick={axisStyle}
            stroke="var(--border)"
            tickLine={false}
            minTickGap={26}
          />
          <YAxis
            tick={axisStyle}
            stroke="var(--border)"
            tickLine={false}
            axisLine={false}
            width={40}
            allowDecimals={false}
          />
          <Tooltip
            content={<HistogramTooltip bucket={bucket} />}
            cursor={{ fill: 'var(--accent-soft)' }}
          />
          <Legend
            verticalAlign="top"
            align="right"
            height={26}
            iconType="square"
            wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--text-muted)' }}
          />
          {/* stroke couleur surface = filet de séparation entre segments empilés */}
          <Bar
            dataKey="alert"
            stackId="sev"
            name="Alerte"
            fill="var(--status-watch)"
            stroke="var(--surface)"
            strokeWidth={1}
            isAnimationActive={false}
          />
          <Bar
            dataKey="critical"
            stackId="sev"
            name="Critique"
            fill="var(--status-critical)"
            stroke="var(--surface)"
            strokeWidth={1}
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
