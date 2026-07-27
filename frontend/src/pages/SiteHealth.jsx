import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, Cell, LabelList, RadialBarChart, RadialBar, PolarAngleAxis, AreaChart, Area,
} from 'recharts'
import { TrendingDown, TrendingUp, Minus } from 'lucide-react'
import { useLang } from '../i18n'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'
import {
  SUBSCORES, GLOBAL_SCORE, LEGEND, EVOLUTION, SUBSCORE_LINE_COLOR, FAMILIES,
  STATUS_HEX, statusFor,
} from '../siteHealthData'

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

// ---- jauge radiale (Recharts) ----
function Gauge({ score, size = 96 }) {
  const color = STATUS_HEX[statusFor(score)]
  return (
    <div style={{ position: 'relative', width: size, height: size, flex: 'none' }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart innerRadius="72%" outerRadius="100%" startAngle={90} endAngle={-270} data={[{ value: score, fill: color }]}>
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar background={{ fill: 'var(--surface-inset)' }} dataKey="value" cornerRadius={10} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="num" style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, fontWeight: 700, color }}>
        {score}
      </div>
    </div>
  )
}

const TrendIcon = ({ v }) => {
  if (v > 0) return <TrendingUp size={14} style={{ color: 'var(--chart-healthy)' }} />
  if (v < 0) return <TrendingDown size={14} style={{ color: 'var(--chart-critical)' }} />
  return <Minus size={14} style={{ color: 'var(--text-muted)' }} />
}

export default function SiteHealth() {
  const { t } = useLang()
  const [range, setRange] = useState('7j')
  const globalStatus = statusFor(GLOBAL_SCORE)

  return (
    <div className="flex flex-col gap-6">
      {/* ---- Hero : score global + répartition des sous-scores ---- */}
      <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        <Card i={0}>
          <CardLabel>{t('siteHealth.title')}</CardLabel>
          <div className="flex items-end gap-3" style={{ marginTop: 10 }}>
            <span className="num" style={{ fontSize: 52, fontWeight: 700, lineHeight: 1, color: STATUS_HEX[globalStatus] }}>{GLOBAL_SCORE}</span>
            <span className="num" style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 6 }}>/ 100</span>
            <span className="num flex items-center gap-1" style={{ marginBottom: 8, marginLeft: 'auto', fontSize: 12, color: 'var(--chart-healthy)' }}><TrendingUp size={14} /> 1.2 · 24h</span>
          </div>
          <div style={{ height: 96, marginTop: 8 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={EVOLUTION} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
                <defs>
                  <linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={STATUS_HEX[globalStatus]} stopOpacity={0.28} />
                    <stop offset="100%" stopColor={STATUS_HEX[globalStatus]} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="env" stroke={STATUS_HEX[globalStatus]} strokeWidth={2} fill="url(#scoreFill)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-4" style={{ marginTop: 8 }}>
            {[['healthy', LEGEND.healthy, t('status.healthy')], ['watch', LEGEND.watch, t('status.watch')], ['critical', LEGEND.critical, t('status.critical')]].map(([k, n, label]) => (
              <span key={k} className="num flex items-center gap-1.5" style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: STATUS_HEX[k], display: 'inline-block' }} /> {n} {label.toLowerCase()}
              </span>
            ))}
          </div>
        </Card>

        <Card i={1}>
          <CardLabel>{t('siteHealth.summary')}</CardLabel>
          <div style={{ height: 190, marginTop: 12 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={SUBSCORES} margin={{ top: 0, right: 34, bottom: 0, left: 0 }} barCategoryGap={14}>
                <XAxis type="number" domain={[0, 100]} hide />
                <YAxis type="category" dataKey="name" width={104} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--text)' }} />
                <Bar dataKey="score" radius={[6, 6, 6, 6]} background={{ fill: 'var(--surface-inset)', radius: 6 }} isAnimationActive>
                  {SUBSCORES.map((s) => <Cell key={s.key} fill={STATUS_HEX[s.status]} />)}
                  <LabelList dataKey="score" position="right" style={{ fill: 'var(--text)', fontSize: 12, fontWeight: 600, fontFamily: 'var(--font-mono)' }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* ---- Évolution du score par sous-score (Recharts) ---- */}
      <Card i={2} hover={false}>
        <div className="flex items-start justify-between gap-3" style={{ marginBottom: 6 }}>
          <div>
            <h2 style={{ fontSize: 'var(--fs-body)', fontWeight: 'var(--fw-semibold)' }}>{t('siteHealth.evolution')}</h2>
          </div>
          <div className="flex gap-1" role="group">
            {['7j', '30j', '90j'].map((r) => (
              <button key={r} onClick={() => setRange(r)} className="num"
                style={{ fontSize: 11, fontWeight: 600, padding: '5px 12px', borderRadius: 'var(--radius-sm)', border: `1px solid ${r === range ? 'var(--accent)' : 'var(--border)'}`, background: r === range ? 'var(--accent-soft)' : 'transparent', color: r === range ? 'var(--accent-hover)' : 'var(--text-muted)', cursor: 'pointer' }}>
                {r}
              </button>
            ))}
          </div>
        </div>
        <div style={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={EVOLUTION} margin={{ top: 10, right: 16, bottom: 4, left: -12 }}>
              <CartesianGrid stroke="var(--hairline)" vertical={false} />
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} />
              <YAxis domain={[40, 100]} ticks={[40, 55, 70, 85, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
              {SUBSCORES.map((s) => (
                <Line key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={SUBSCORE_LINE_COLOR[s.key]} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-wrap gap-4" style={{ marginTop: 10 }}>
          {SUBSCORES.map((s) => (
            <span key={s.key} className="flex items-center gap-1.5" style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
              <span style={{ width: 12, height: 3, borderRadius: 2, background: SUBSCORE_LINE_COLOR[s.key], display: 'inline-block' }} /> {s.name}
            </span>
          ))}
        </div>
      </Card>

      {/* ---- Détail des sous-scores (jauges radiales) ---- */}
      <div>
        <CardLabel>{t('siteHealth.detail')}</CardLabel>
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', marginTop: 12 }}>
          {SUBSCORES.map((s, idx) => (
            <Card key={s.key} i={idx}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{s.name}</div>
                  <div className="num" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{t('siteHealth.weight')} {s.weight}%</div>
                </div>
                <StatusBadge status={s.status} />
              </div>
              <div className="flex items-center gap-4" style={{ marginTop: 12 }}>
                <Gauge score={s.score} />
                <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{s.detail}</p>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* ---- Par famille d'équipement (sparklines) ---- */}
      <div>
        <CardLabel>{t('siteHealth.byFamily')}</CardLabel>
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', marginTop: 12 }}>
          {FAMILIES.map((f, idx) => (
            <Card key={f.name} i={idx}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600 }}>{f.name}</div>
                  <div className="num" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>× {t('common.units', { n: f.units })}</div>
                </div>
                <span className="num" style={{ fontSize: 26, fontWeight: 700, color: STATUS_HEX[statusFor(f.score)] }}>{f.score}</span>
              </div>
              <div style={{ height: 52, marginTop: 8 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={f.spark.map((v, i) => ({ i, v }))} margin={{ top: 6, right: 2, bottom: 0, left: 2 }}>
                    <Line type="monotone" dataKey="v" stroke={STATUS_HEX[statusFor(f.score)]} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="num flex items-center gap-1" style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                <TrendIcon v={f.trend} /> {f.trend > 0 ? '+' : ''}{f.trend} · 24h
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
