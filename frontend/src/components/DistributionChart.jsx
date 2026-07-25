import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from 'recharts'

/**
 * Barres horizontales pour une répartition catégorielle.
 * Une seule teinte par défaut : l'identité est portée par le libellé d'axe,
 * pas par la couleur. `colors` permet d'utiliser les couleurs de statut
 * réservées quand les catégories SONT des statuts (sévérité).
 */
export default function DistributionChart({ data, colors, height = 132 }) {
  const max = Math.max(...data.map((d) => d.value), 1)

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 2, right: 34, bottom: 2, left: 0 }}
          barCategoryGap={8}
        >
          <XAxis type="number" hide domain={[0, max * 1.12]} />
          <YAxis
            type="category"
            dataKey="label"
            width={104}
            tickLine={false}
            axisLine={false}
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, fill: 'var(--text-muted)' }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={14} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={colors?.[d.key] ?? 'var(--viz-1)'} />
            ))}
            <LabelList
              dataKey="value"
              position="right"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                fontWeight: 600,
                fill: 'var(--text)',
              }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
