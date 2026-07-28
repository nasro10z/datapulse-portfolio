import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, Area,
} from 'recharts'
import { TrendingDown, TrendingUp, Minus } from 'lucide-react'
import { useLang } from '../i18n'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import StatusBadge from '../components/StatusBadge'

const STATUS_CHART_COLOR = {
  healthy: 'var(--chart-healthy)',
  watch: 'var(--chart-watch)',
  critical: 'var(--chart-critical)',
}
const DOMAIN_LINE_COLOR = { environment: 'var(--viz-1)', energy: 'var(--viz-4)', battery: 'var(--viz-5)' }
const DOMAIN_LABEL_KEY = { environment: 'domainEnvironment', energy: 'domainEnergy', battery: 'domainBattery' }
const RANGE_KEY = { '7d': 'd7', '30d': 'd30', '90d': 'd90' }
const RANGES = ['7d', '30d', '90d']

const fmtDelta = (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`

// ---- animations ----
const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.05, duration: 0.4, ease: [0.22, 1, 0.36, 1] } }),
}
const Card = ({ children, i = 0, style, hover = true }) => (
  <motion.div
    variants={fadeUp} initial="hidden" animate="show" custom={i}
    whileHover={hover ? { scale: 1.01 } : undefined}
    style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-card)', padding: 'var(--space-5)', ...style,
    }}
  >
    {children}
  </motion.div>
)

const CardLabel = ({ children }) => (
  <div className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)' }}>{children}</div>
)

const TrendIcon = ({ v }) => {
  if (v > 0) return <TrendingUp size={14} style={{ color: 'var(--chart-healthy)' }} />
  if (v < 0) return <TrendingDown size={14} style={{ color: 'var(--chart-critical)' }} />
  return <Minus size={14} style={{ color: 'var(--text-muted)' }} />
}

const DeltaTag = ({ value, suffix }) => (
  <span
    className="num flex items-center gap-1"
    style={{ fontSize: 12, color: value > 0 ? 'var(--chart-healthy)' : value < 0 ? 'var(--chart-critical)' : 'var(--text-muted)' }}
  >
    <TrendIcon v={value} /> {fmtDelta(value)} {suffix}
  </span>
)

export default function SiteHealth() {
  const { t, locale } = useLang()
  const [range, setRange] = useState('7d')
  const overview = useApi(api.healthOverview)
  const history = useApi(() => api.healthHistory(range), [range])

  const fmtDay = (iso) => new Date(iso).toLocaleDateString(locale, { day: '2-digit', month: '2-digit' })

  return (
    <div className="flex flex-col gap-6">
      <ApiState loading={overview.loading} error={overview.error}>
        {overview.data && (() => {
          const o = overview.data
          const globalDelta = o.global_score - o.previous_score
          return (
            <>
              {/* ---- Hero : score global + sous-scores par domaine ---- */}
              <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
                <Card i={0}>
                  <CardLabel>{t('siteHealth.scoreGlobal')}</CardLabel>
                  <div className="flex items-end gap-3" style={{ marginTop: 10 }}>
                    <span className="num" style={{ fontSize: 52, fontWeight: 700, lineHeight: 1, color: STATUS_CHART_COLOR[o.status] }}>{o.global_score.toFixed(1)}</span>
                    <span className="num" style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 6 }}>/ 100</span>
                    <span style={{ marginBottom: 8, marginLeft: 'auto' }}><StatusBadge status={o.status} /></span>
                  </div>
                  <div style={{ marginTop: 6 }}>
                    <DeltaTag value={globalDelta} suffix={t('siteHealth.vsLast')} />
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5, marginTop: 12 }}>{t('siteHealth.decision')}</p>
                </Card>

                <Card i={1}>
                  <CardLabel>{t('siteHealth.summary')}</CardLabel>
                  <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', marginTop: 12 }}>
                    {o.domain_scores.map((d) => (
                      <div key={d.domain} style={{ padding: 'var(--space-3)', background: 'var(--surface-inset)', borderRadius: 'var(--radius-md)' }}>
                        <div className="flex items-center justify-between gap-2">
                          <span style={{ fontSize: 12.5, fontWeight: 600 }}>{t(`siteHealth.${DOMAIN_LABEL_KEY[d.domain]}`)}</span>
                          <StatusBadge status={d.status} />
                        </div>
                        <div className="flex items-baseline gap-2" style={{ marginTop: 6 }}>
                          <span className="num" style={{ fontSize: 24, fontWeight: 700, color: STATUS_CHART_COLOR[d.status] }}>{d.score.toFixed(1)}</span>
                        </div>
                        <DeltaTag value={d.score - d.previous_score} suffix={t('siteHealth.vsLast')} />
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </>
          )
        })()}
      </ApiState>

      {/* ---- Évolution du score global (élément dominant) ---- */}
      <Card hover={false}>
        <div className="flex items-start justify-between gap-3" style={{ marginBottom: 6 }}>
          <h2 style={{ fontSize: 'var(--fs-body)', fontWeight: 'var(--fw-semibold)' }}>{t('siteHealth.evolutionGlobal')}</h2>
          <div className="flex gap-1" role="group" aria-label={t('siteHealth.rangeLabel')}>
            {RANGES.map((r) => (
              <button key={r} onClick={() => setRange(r)} className="num"
                style={{ fontSize: 11, fontWeight: 600, padding: '5px 12px', borderRadius: 'var(--radius-sm)', border: `1px solid ${r === range ? 'var(--accent)' : 'var(--border)'}`, background: r === range ? 'var(--accent-soft)' : 'transparent', color: r === range ? 'var(--accent-hover)' : 'var(--text-muted)', cursor: 'pointer' }}>
                {t(`siteHealth.${RANGE_KEY[r]}`)}
              </button>
            ))}
          </div>
        </div>
        <ApiState loading={history.loading} error={history.error}>
          {history.data && (
            <div style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history.data.points} margin={{ top: 10, right: 16, bottom: 4, left: -12 }}>
                  <defs>
                    <linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--hairline)" vertical={false} />
                  <XAxis dataKey="timestamp" tickFormatter={fmtDay} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} />
                  <YAxis domain={[40, 100]} ticks={[40, 55, 70, 85, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} />
                  <Tooltip labelFormatter={fmtDay} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
                  <Area type="monotone" dataKey="global_score" name={t('siteHealth.scoreGlobal')} stroke="var(--accent)" strokeWidth={2} fill="url(#scoreFill)" dot={false} activeDot={{ r: 4 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </ApiState>
      </Card>

      {/* ---- Évolution des sous-scores par domaine ---- */}
      <Card hover={false}>
        <h2 style={{ fontSize: 'var(--fs-body)', fontWeight: 'var(--fw-semibold)', marginBottom: 6 }}>{t('siteHealth.evolution')}</h2>
        <ApiState loading={history.loading} error={history.error}>
          {history.data && (
            <>
              <div style={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={history.data.points} margin={{ top: 10, right: 16, bottom: 4, left: -12 }}>
                    <CartesianGrid stroke="var(--hairline)" vertical={false} />
                    <XAxis dataKey="timestamp" tickFormatter={fmtDay} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} />
                    <YAxis domain={[40, 100]} ticks={[40, 55, 70, 85, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} />
                    <Tooltip labelFormatter={fmtDay} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
                    {Object.keys(DOMAIN_LINE_COLOR).map((domain) => (
                      <Line key={domain} type="monotone" dataKey={domain} name={t(`siteHealth.${DOMAIN_LABEL_KEY[domain]}`)} stroke={DOMAIN_LINE_COLOR[domain]} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap gap-4" style={{ marginTop: 10 }}>
                {Object.keys(DOMAIN_LINE_COLOR).map((domain) => (
                  <span key={domain} className="flex items-center gap-1.5" style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                    <span style={{ width: 12, height: 3, borderRadius: 2, background: DOMAIN_LINE_COLOR[domain], display: 'inline-block' }} /> {t(`siteHealth.${DOMAIN_LABEL_KEY[domain]}`)}
                  </span>
                ))}
              </div>
            </>
          )}
        </ApiState>
      </Card>
    </div>
  )
}
