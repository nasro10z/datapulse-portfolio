import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from 'recharts'

const STATUS_COLOR = {
  healthy: 'var(--status-healthy)',
  watch: 'var(--status-watch)',
  critical: 'var(--status-critical)',
}

/**
 * Gauge radiale de health score (0–100), Recharts.
 * Arc de 270° ouvert vers le bas, valeur en chiffres tabulaires au centre.
 */
export default function HealthGauge({ score, status = 'healthy', size = 190, label }) {
  const clamped = Math.max(0, Math.min(100, Number(score) || 0))
  const color = STATUS_COLOR[status] ?? STATUS_COLOR.healthy
  const data = [{ name: 'score', value: clamped }]

  return (
    <div
      className="relative"
      role="img"
      aria-label={`Health score ${clamped.toFixed(1)} sur 100 — ${status}`}
      style={{ width: size, height: size }}
    >
      <ResponsiveContainer>
        <RadialBarChart
          data={data}
          startAngle={225}
          endAngle={-45}
          innerRadius="78%"
          outerRadius="100%"
          barSize={size * 0.075}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar
            background={{ fill: 'var(--chart-track)' }}
            dataKey="value"
            cornerRadius={size}
            fill={color}
            angleAxisId={0}
            isAnimationActive={false}
          />
        </RadialBarChart>
      </ResponsiveContainer>

      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="num"
          style={{
            fontSize: size * 0.2,
            fontWeight: 'var(--fw-semibold)',
            letterSpacing: 'var(--tracking-tight)',
            lineHeight: 1,
            color: 'var(--text)',
          }}
        >
          {clamped.toFixed(1)}
        </span>
        {label && (
          <span
            className="num"
            style={{
              fontSize: 9.5,
              letterSpacing: 'var(--tracking-caps)',
              textTransform: 'uppercase',
              color: 'var(--text-muted)',
              marginTop: 7,
            }}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  )
}
