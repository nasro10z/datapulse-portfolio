import { useMemo, useState } from 'react'
import { useLang } from '../i18n'

const W = 800
const H = 200
const PAD = { top: 12, right: 12, bottom: 26, left: 30 }

// sévérités empilées : alerte (bas) puis critique (haut), couleurs sémantiques de statut
const SEV = [
  { key: 'alert', color: 'var(--status-watch)', labelKey: 'anomalies.sevAlert' },
  { key: 'critical', color: 'var(--status-critical)', labelKey: 'anomalies.sevCritical' },
]

const fmtLabel = (iso, bucket, locale) => {
  const d = new Date(iso)
  if (bucket === 'month') return d.toLocaleDateString(locale, { month: 'short', year: '2-digit' })
  return d.toLocaleDateString(locale, { day: '2-digit', month: '2-digit' })
}

/**
 * Histogramme des comptes d'anomalies par période, barres empilées par sévérité.
 * bins: [{ period_start, total, by_severity: { alert, critical } }]
 */
export default function AnomalyHistogram({ bins = [], bucket = 'day' }) {
  const { t, locale } = useLang()
  const [hover, setHover] = useState(null)

  const model = useMemo(() => {
    if (!bins.length) return null
    const vMax = Math.max(1, ...bins.map((b) => b.total))
    const plotW = W - PAD.left - PAD.right
    const plotH = H - PAD.top - PAD.bottom
    const slot = plotW / bins.length
    const barW = Math.max(1, Math.min(slot - 2, 26))
    const y = (v) => PAD.top + (1 - v / vMax) * plotH
    const bars = bins.map((b, i) => {
      const cx = PAD.left + slot * (i + 0.5)
      return { ...b, cx, x: cx - barW / 2 }
    })
    const yTicks = [0, Math.ceil(vMax / 2), vMax].filter((v, idx, a) => a.indexOf(v) === idx)
    const tickEvery = Math.ceil(bins.length / 6)
    return { bars, barW, y, plotH, yTicks, tickEvery }
  }, [bins])

  if (!model) {
    return (
      <div className="num" style={{ color: 'var(--text-muted)', fontSize: 12, padding: 24 }}>
        {t('anomalies.histEmpty')}
      </div>
    )
  }

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }} onMouseLeave={() => setHover(null)}>
        {model.yTicks.map((v) => (
          <g key={v}>
            <line x1={PAD.left} x2={W - PAD.right} y1={model.y(v)} y2={model.y(v)} stroke="var(--hairline)" strokeWidth="1" />
            <text x={PAD.left - 6} y={model.y(v) + 3} textAnchor="end"
              style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}>{v}</text>
          </g>
        ))}

        {model.bars.map((b, i) => {
          let acc = 0
          return (
            <g key={b.period_start} onMouseEnter={() => setHover(b)}>
              {SEV.map((s) => {
                const c = b.by_severity?.[s.key] ?? 0
                if (!c) return null
                const yTop = model.y(acc + c)
                const rect = <rect key={s.key} x={b.x} y={yTop} width={model.barW}
                  height={Math.max(0, model.y(acc) - yTop)} fill={s.color}
                  opacity={hover && hover !== b ? 0.5 : 0.9} rx="1" />
                acc += c
                return rect
              })}
              {i % model.tickEvery === 0 && (
                <text x={b.cx} y={H - 9} textAnchor="middle"
                  style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}>
                  {fmtLabel(b.period_start, bucket, locale)}
                </text>
              )}
            </g>
          )
        })}
      </svg>

      {hover && (
        <div className="num" style={{ marginTop: 4, fontSize: 11, color: 'var(--text-muted)' }}>
          {fmtLabel(hover.period_start, bucket, locale)} — <strong style={{ color: 'var(--text)' }}>{t('anomalies.hoverAnoms', { n: hover.total })}</strong>
          {hover.by_severity?.critical ? ` · ${t('anomalies.hoverCrit', { n: hover.by_severity.critical })}` : ''}
        </div>
      )}

      <div className="flex gap-4" style={{ marginTop: 8 }}>
        {SEV.map((s) => (
          <span key={s.key} className="flex items-center gap-1.5" style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>
            <span style={{ width: 9, height: 9, borderRadius: 2, background: s.color, display: 'inline-block' }} />
            {t(s.labelKey)}
          </span>
        ))}
      </div>
    </div>
  )
}
