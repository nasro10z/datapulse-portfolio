import { useState } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import { useLang } from '../i18n'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'
import TrendChart from '../components/TrendChart'

const HORIZONS = ['24h', '7d', '30d']
const HORIZON_KEY = { '24h': 'h24', '7d': 'd7', '30d': 'd30' }
const FAMILY_COLOR = { stulz: 'var(--viz-2)', socomec: 'var(--viz-4)', yanan: 'var(--viz-3)' }
// Présentation « par domaine » (environnement/énergie/batterie) des scores par
// famille d'équipement — mêmes données (STULZ/SOCOMEC/YANAN), libellé différent.
const FAMILY_DOMAIN_LABEL_KEY = { stulz: 'domainEnvironment', socomec: 'domainEnergy', yanan: 'domainBattery' }

export default function Forecast() {
  const [horizon, setHorizon] = useState('24h')
  const { t, locale } = useLang()
  const hLabel = (h) => t(`forecast.${HORIZON_KEY[h]}`)

  const faults = useApi(() => api.predictedFaults(horizon), [horizon])
  const forecast = useApi(() => api.healthForecast(horizon), [horizon])
  const subScores = useApi(() => api.subScoreForecast(horizon), [horizon])

  const fmtWhen = (iso) =>
    new Date(iso).toLocaleString(locale, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

  const horizonSelector = (
    <div className="flex gap-1" role="group" aria-label={t('forecast.horizonLabel')}>
      {HORIZONS.map((h) => (
        <button
          key={h}
          onClick={() => setHorizon(h)}
          className="num"
          style={{
            fontSize: 11,
            fontWeight: 600,
            padding: '5px 12px',
            borderRadius: 'var(--radius-sm)',
            border: `1px solid ${h === horizon ? 'var(--accent)' : 'var(--border)'}`,
            background: h === horizon ? 'var(--accent-soft)' : 'transparent',
            color: h === horizon ? 'var(--accent-hover)' : 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          {hLabel(h)}
        </button>
      ))}
    </div>
  )

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Prédiction des prochaines pannes — élément d'entrée de page */}
      <Panel
        title={t('forecast.nextFault')}
        subtitle={t('forecast.nextFaultSub', { h: hLabel(horizon) })}
        actions={horizonSelector}
      >
        <ApiState loading={faults.loading} error={faults.error}>
          {faults.data && (
            <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
              {faults.data.faults.map((f) => (
                <article
                  key={f.family}
                  style={{ background: 'var(--surface-inset)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)' }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div style={{ fontSize: 13.5, fontWeight: 600 }}>{t(`siteHealth.${FAMILY_DOMAIN_LABEL_KEY[f.family]}`)}</div>
                    {f.severity ? (
                      <StatusBadge status={f.severity} />
                    ) : (
                      <span
                        className="num flex items-center gap-1"
                        style={{
                          fontSize: 10, fontWeight: 600, letterSpacing: 'var(--tracking-wide)',
                          textTransform: 'uppercase', color: 'var(--status-healthy)',
                        }}
                      >
                        <CheckCircle2 size={12} /> {t('forecast.noFaultPredicted')}
                      </span>
                    )}
                  </div>
                  {f.predicted_at && (
                    <div className="num" style={{ fontSize: 14, fontWeight: 600, marginTop: 10 }}>
                      {t('forecast.predictedAround', { date: fmtWhen(f.predicted_at) })}
                    </div>
                  )}
                  {f.note && (
                    <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.5 }}>{f.note}</p>
                  )}
                </article>
              ))}
            </div>
          )}
        </ApiState>
      </Panel>

      {/* 2. Global Health Score Chart — élément dominant, pleine largeur */}
      <Panel title={t('forecast.title')} subtitle={t('forecast.subtitle', { h: hLabel(horizon) })}>
        <ApiState loading={forecast.loading} error={forecast.error}>
          {forecast.data && (
            <>
              <TrendChart points={forecast.data.points} crossings={forecast.data.threshold_crossings} />
              {forecast.data.threshold_crossings.length > 0 && (
                <p style={{ fontSize: 12, color: 'var(--status-critical)', marginTop: 10 }}>
                  {t('forecast.crossings', { n: forecast.data.threshold_crossings.length })}
                </p>
              )}
            </>
          )}
        </ApiState>
      </Panel>

      {/* 3. Prévision des sous-scores par famille d'équipement */}
      <section>
        <h2
          className="num"
          style={{
            fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase',
            color: 'var(--text-muted)', marginBottom: 12,
          }}
        >
          {t('forecast.subScores')}
        </h2>
        <ApiState loading={subScores.loading} error={subScores.error}>
          {subScores.data && (
            <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
              {subScores.data.series.map((s) => (
                <div
                  key={s.family}
                  style={{
                    background: 'var(--surface)', border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-card)', padding: 'var(--space-4)',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>{t(`siteHealth.${FAMILY_DOMAIN_LABEL_KEY[s.family]}`)}</div>
                  <TrendChart points={s.points} color={FAMILY_COLOR[s.family]} />
                </div>
              ))}
            </div>
          )}
        </ApiState>
      </section>
    </div>
  )
}
