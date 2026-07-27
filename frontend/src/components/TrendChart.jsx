import { useMemo } from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const fmtAxis = (ts, spanHours) => {
  const d = new Date(ts)
  if (spanHours <= 20) return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  if (spanHours <= 72)
    return `${d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })} ${d.getHours()}h`
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
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
        {new Date(label).toLocaleString('fr-FR')}
        {p.is_forecast ? ' · prévision' : ' · historique'}
      </div>
      <div className="num" style={{ fontSize: 13, fontWeight: 600, marginTop: 3, color: 'var(--text)' }}>
        {p.value?.toFixed(1)}
      </div>
      {p.is_forecast && p.lower != null && (
        <div className="num" style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 2 }}>
          Intervalle : {p.lower.toFixed(1)} – {p.upper.toFixed(1)}
        </div>
      )}
    </div>
  )
}

/**
 * Courbe de score + bande de confiance (Recharts).
 * Historique en trait plein, prévision en pointillé, bande de confiance
 * uniquement sur la partie prévue. Un seul axe Y.
 */
export default function TrendChart({ points = [], crossings = [], height = 300 }) {
  const { data, spanHours, marks, yDomain } = useMemo(() => {
    if (!points.length) return { data: [], spanHours: 0, marks: [], yDomain: [0, 1] }
    const rows = points.map((p) => ({
      t: new Date(p.timestamp).getTime(),
      value: p.value,
      lower: p.lower,
      upper: p.upper,
      is_forecast: p.is_forecast,
      // Recharts empile la bande : base = lower, hauteur = upper - lower.
      // Restreinte à la prévision — pas d'incertitude sur du déjà mesuré.
      bandBase: p.is_forecast ? p.lower : null,
      bandSize: p.is_forecast ? p.upper - p.lower : null,
      histValue: p.is_forecast ? null : p.value,
      fcstValue: p.is_forecast ? p.value : null,
    }))
    // Raccorde visuellement l'historique et la prévision
    const firstFcst = rows.findIndex((r) => r.is_forecast)
    if (firstFcst > 0) rows[firstFcst - 1].fcstValue = rows[firstFcst - 1].value

    const span = (rows[rows.length - 1].t - rows[0].t) / 3.6e6
    const marks = crossings.map((c) => ({ t: new Date(c.timestamp).getTime(), y: c.threshold }))

    // Domaine Y explicite : la bande est empilée, l'auto-domaine de Recharts
    // repartirait de 0 et écraserait la courbe.
    const vals = rows
      .flatMap((r) => [r.value, r.lower, r.upper])
      .concat(marks.map((m) => m.y))
      .filter((v) => v != null)
    const lo = Math.min(...vals)
    const hi = Math.max(...vals)
    const pad = Math.max((hi - lo) * 0.15, 0.5)

    return {
      data: rows,
      spanHours: span,
      marks,
      yDomain: [Math.floor(lo - pad), Math.ceil(hi + pad)],
    }
  }, [points, crossings])

  if (!data.length) {
    return (
      <div className="num" style={{ color: 'var(--text-muted)', fontSize: 12, padding: 24 }}>
        Aucune donnée
      </div>
    )
  }

  const axisStyle = { fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--chart-axis)' }

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -8 }}>
          <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(t) => fmtAxis(t, spanHours)}
            tick={axisStyle}
            stroke="var(--border)"
            tickLine={false}
            minTickGap={44}
          />
          <YAxis
            tick={axisStyle}
            stroke="var(--border)"
            tickLine={false}
            axisLine={false}
            width={46}
            domain={yDomain}
            allowDataOverflow
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'var(--border-strong)', strokeWidth: 1 }} />
          <Legend
            verticalAlign="top"
            align="right"
            height={28}
            iconType="plainline"
            wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--text-muted)' }}
          />

          {/* Bande de confiance : base invisible + hauteur teintée */}
          <Area
            dataKey="bandBase"
            stackId="band"
            stroke="none"
            fill="none"
            legendType="none"
            isAnimationActive={false}
          />
          <Area
            dataKey="bandSize"
            stackId="band"
            stroke="none"
            fill="var(--viz-1)"
            fillOpacity={0.18}
            name="Intervalle de confiance"
            legendType="rect"
            isAnimationActive={false}
          />

          <Line
            dataKey="histValue"
            stroke="var(--viz-1)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: 'var(--surface)' }}
            name="Historique"
            connectNulls
            isAnimationActive={false}
          />
          <Line
            dataKey="fcstValue"
            stroke="var(--viz-1)"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: 'var(--surface)' }}
            name="Prévision"
            connectNulls
            isAnimationActive={false}
          />

          {marks.map((m, i) => (
            <ReferenceLine
              key={`l${i}`}
              x={m.t}
              stroke="var(--status-critical)"
              strokeDasharray="2 4"
              strokeOpacity={0.6}
            />
          ))}
          {marks.map((m, i) => (
            <ReferenceDot
              key={`d${i}`}
              x={m.t}
              y={m.y}
              r={5}
              fill="var(--surface)"
              stroke="var(--status-critical)"
              strokeWidth={2}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
