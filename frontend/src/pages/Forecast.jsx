import { useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import Panel from '../components/Panel'
import TrendChart from '../components/TrendChart'
import EquipmentCard from '../components/EquipmentCard'

const HORIZONS = ['24h', '7d', '30d']
const HORIZON_LABEL = { '24h': '24 h', '7d': '7 jours', '30d': '30 jours' }

export default function Forecast() {
  const [horizon, setHorizon] = useState('24h')
  const forecast = useApi(() => api.healthForecast(horizon), [horizon])
  const overview = useApi(api.healthOverview)

  return (
    <div className="flex flex-col gap-6">
      {/* Élément dominant : chart global pleine largeur + sélecteur d'horizon */}
      <Panel
        title="Global Health Score"
        subtitle={`Historique + prévision — horizon ${HORIZON_LABEL[horizon]}`}
        actions={
          <div className="flex gap-1" role="group" aria-label="Horizon de prévision">
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
                {HORIZON_LABEL[h]}
              </button>
            ))}
          </div>
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
                  ▲ {forecast.data.threshold_crossings.length} franchissement(s) de seuil prévu(s)
                  sur cet horizon.
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
          Sub-scores par famille d’équipement
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
