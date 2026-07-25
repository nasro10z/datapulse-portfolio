import { useMemo, useRef, useState } from 'react'

const W = 800
const H = 260
const PAD = { top: 16, right: 16, bottom: 28, left: 40 }

const fmtTime = (iso, spanHours) => {
  const d = new Date(iso)
  if (spanHours <= 20) return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  if (spanHours <= 72)
    return `${d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })} ${d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
}

/**
 * Courbe de score + bande de confiance (SVG).
 * Historique en trait plein, prévision en pointillé, bande de confiance
 * en aplat translucide. Survol : crosshair + tooltip au point le plus proche.
 *
 * points: [{ timestamp, value, lower, upper, is_forecast }]
 * crossings: [{ timestamp, threshold, severity }]
 */
export default function TrendChart({ points = [], crossings = [], color = 'var(--viz-1)' }) {
  const wrapRef = useRef(null)
  const [hover, setHover] = useState(null)

  const model = useMemo(() => {
    if (!points.length) return null
    const ts = points.map((p) => new Date(p.timestamp).getTime())
    const t0 = Math.min(...ts)
    const t1 = Math.max(...ts)
    const values = points.flatMap((p) => [p.lower, p.upper, p.value])
    const vMin = Math.floor(Math.min(...values) - 2)
    const vMax = Math.ceil(Math.max(...values) + 2)
    const x = (t) => PAD.left + ((t - t0) / (t1 - t0 || 1)) * (W - PAD.left - PAD.right)
    const y = (v) => PAD.top + (1 - (v - vMin) / (vMax - vMin || 1)) * (H - PAD.top - PAD.bottom)
    const pts = points.map((p, i) => ({ ...p, t: ts[i], px: x(ts[i]), py: y(p.value) }))
    const spanHours = (t1 - t0) / 3.6e6

    const line = (arr) => arr.map((p, i) => `${i ? 'L' : 'M'}${p.px.toFixed(1)} ${p.py.toFixed(1)}`).join(' ')
    const histEnd = pts.findLastIndex((p) => !p.is_forecast)
    const hist = pts.slice(0, histEnd + 1)
    // La prévision repart du dernier point historique pour éviter un trou visuel
    const fcst = pts.slice(Math.max(histEnd, 0))

    const band = fcst.length > 1
      ? fcst.map((p, i) => `${i ? 'L' : 'M'}${p.px.toFixed(1)} ${y(p.upper).toFixed(1)}`).join(' ') +
        [...fcst].reverse().map((p) => `L${p.px.toFixed(1)} ${y(p.lower).toFixed(1)}`).join('') + 'Z'
      : null

    const yTicks = [vMin, (vMin + vMax) / 2, vMax]
    const xTicks = [pts[0], pts[Math.floor(pts.length / 2)], pts[pts.length - 1]]
    const marks = crossings.map((c) => ({ ...c, px: x(new Date(c.timestamp).getTime()), py: y(c.threshold) }))
    return { pts, hist, fcst, band, line, x, y, yTicks, xTicks, spanHours, marks }
  }, [points, crossings])

  if (!model) {
    return (
      <div className="num" style={{ color: 'var(--text-muted)', fontSize: 12, padding: 24 }}>
        Aucune donnée
      </div>
    )
  }

  const onMove = (e) => {
    const rect = wrapRef.current.getBoundingClientRect()
    const px = ((e.clientX - rect.left) / rect.width) * W
    let best = model.pts[0]
    for (const p of model.pts) if (Math.abs(p.px - px) < Math.abs(best.px - px)) best = p
    setHover(best)
  }

  return (
    <div ref={wrapRef} className="relative" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
        {/* grille + axe Y */}
        {model.yTicks.map((v) => (
          <g key={v}>
            <line
              x1={PAD.left} x2={W - PAD.right} y1={model.y(v)} y2={model.y(v)}
              stroke="var(--hairline)" strokeWidth="1"
            />
            <text
              x={PAD.left - 8} y={model.y(v) + 3} textAnchor="end"
              style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-muted)' }}
            >
              {v.toFixed(0)}
            </text>
          </g>
        ))}
        {/* axe X */}
        {model.xTicks.map((p, i) => (
          <text
            key={i}
            x={p.px} y={H - 8}
            textAnchor={i === 0 ? 'start' : i === model.xTicks.length - 1 ? 'end' : 'middle'}
            style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-muted)' }}
          >
            {fmtTime(p.timestamp, model.spanHours)}
          </text>
        ))}

        {/* bande de confiance (prévision) */}
        {model.band && <path d={model.band} fill={color} opacity="0.13" />}

        {/* historique plein, prévision pointillée */}
        <path d={model.line(model.hist)} fill="none" stroke={color} strokeWidth="2" />
        {model.fcst.length > 1 && (
          <path d={model.line(model.fcst)} fill="none" stroke={color} strokeWidth="2" strokeDasharray="5 5" />
        )}

        {/* franchissements de seuil prévus */}
        {model.marks.map((m, i) => (
          <g key={i}>
            <circle cx={m.px} cy={m.py} r="5" fill="var(--surface)" stroke="var(--status-critical)" strokeWidth="2" />
            <line x1={m.px} x2={m.px} y1={PAD.top} y2={H - PAD.bottom} stroke="var(--status-critical)" strokeWidth="1" strokeDasharray="2 4" opacity="0.5" />
          </g>
        ))}

        {/* crosshair */}
        {hover && (
          <g>
            <line x1={hover.px} x2={hover.px} y1={PAD.top} y2={H - PAD.bottom} stroke="var(--border-strong)" strokeWidth="1" />
            <circle cx={hover.px} cy={hover.py} r="4.5" fill={color} stroke="var(--surface)" strokeWidth="2" />
          </g>
        )}
      </svg>

      {hover && (
        <div
          className="pointer-events-none absolute"
          style={{
            left: `${(hover.px / W) * 100}%`,
            top: 0,
            transform: hover.px > W * 0.6 ? 'translateX(calc(-100% - 10px))' : 'translateX(10px)',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '8px 10px',
            fontSize: 11,
            whiteSpace: 'nowrap',
            zIndex: 5,
          }}
        >
          <div className="num" style={{ color: 'var(--text-muted)', fontSize: 10 }}>
            {new Date(hover.timestamp).toLocaleString('fr-FR')}
            {hover.is_forecast ? ' · prévision' : ''}
          </div>
          <div className="num" style={{ fontWeight: 600, marginTop: 2 }}>
            {hover.value.toFixed(1)}
            {hover.is_forecast && (
              <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
                {' '}[{hover.lower.toFixed(1)} – {hover.upper.toFixed(1)}]
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
