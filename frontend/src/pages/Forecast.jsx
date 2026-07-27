import { useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import { useLang } from '../i18n'
import Panel from '../components/Panel'
import TrendChart from '../components/TrendChart'
import EquipmentCard from '../components/EquipmentCard'
import SegmentedControl from '../components/SegmentedControl'

<<<<<<< HEAD
const HORIZONS = ['24h', '7d', '30d']
const HORIZON_KEY = { '24h': 'h24', '7d': 'd7', '30d': 'd30' }
=======
const HORIZON_LABEL = { '24h': '24 h', '7d': '7 jours', '30d': '30 jours' }
const HORIZONS = Object.entries(HORIZON_LABEL).map(([value, label]) => ({ value, label }))
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a

export default function Forecast() {
  const [horizon, setHorizon] = useState('24h')
  const forecast = useApi(() => api.healthForecast(horizon), [horizon])
  const overview = useApi(api.healthOverview)
  const { t } = useLang()
  const hLabel = (h) => t(`forecast.${HORIZON_KEY[h]}`)

  return (
    <div className="flex flex-col gap-6">
      {/* Élément dominant : chart global pleine largeur + sélecteur d'horizon */}
      <Panel
        title={t('forecast.title')}
        subtitle={t('forecast.subtitle', { h: hLabel(horizon) })}
        actions={
<<<<<<< HEAD
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
=======
          <SegmentedControl
            options={HORIZONS}
            value={horizon}
            onChange={setHorizon}
            ariaLabel="Horizon de prévision"
          />
>>>>>>> b9028691a7679fd48982e990d9e01752e3b0c38a
        }
      >
        <ApiState loading={forecast.loading} error={forecast.error}>
          {forecast.data && (
            <>
              <TrendChart
                points={forecast.data.points}
                crossings={forecast.data.threshold_crossings}
              />
              {forecast.data.threshold_crossings.length > 0 && (
                <p style={{ fontSize: 12, color: 'var(--status-critical)', marginTop: 10 }}>
                  {t('forecast.crossings', { n: forecast.data.threshold_crossings.length })}
                </p>
              )}
            </>
          )}
        </ApiState>
      </Panel>

      {/* Sub-scores : cards secondaires, subordonnées visuellement */}
      <section>
        <h2
          className="num"
          style={{
            fontSize: 10,
            letterSpacing: 'var(--tracking-caps)',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
            marginBottom: 12,
          }}
        >
          {t('forecast.subScores')}
        </h2>
        <ApiState loading={overview.loading} error={overview.error}>
          {overview.data && (
            <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              {overview.data.sub_scores.map((s) => (
                <EquipmentCard
                  key={s.family}
                  label={s.label}
                  score={s.score}
                  status={s.status}
                  trend={s.trend}
                  unitCount={s.unit_count}
                  note={s.note}
                />
              ))}
            </div>
          )}
        </ApiState>
      </section>
    </div>
  )
}
