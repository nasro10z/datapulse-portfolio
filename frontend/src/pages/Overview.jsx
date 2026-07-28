import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import { useLang } from '../i18n'
import Panel from '../components/Panel'
import StatusBadge from '../components/StatusBadge'
import DeltaTag from '../components/DeltaTag'
import KpiCard from '../components/KpiCard'
import DueBadge from '../components/DueBadge'
import { STATUS_CHART_COLOR, DOMAIN_LABEL_KEY, FAMILY_DOMAIN_LABEL_KEY } from '../constants/domains'
import { maintenanceKpi } from '../utils/maintenanceKpi'

const ANOMALIES_PREVIEW = 5
const FAULT_HORIZON = '7d'

const viewAllStyle = {
  fontSize: 11.5, fontWeight: 600, color: 'var(--accent-hover)', textDecoration: 'none', whiteSpace: 'nowrap',
}

export default function Overview() {
  const { t, locale } = useLang()
  const STATUS_LABEL = { open: t('anomalies.stOpen'), acknowledged: t('anomalies.stAck'), resolved: t('anomalies.stResolved') }
  const overview = useApi(api.healthOverview)
  const faults = useApi(() => api.predictedFaults(FAULT_HORIZON), [])
  const anomalies = useApi(api.anomalies)
  const calendar = useApi(api.maintenanceCalendar)

  const { next: nextPm, thisWeekCount } = useMemo(() => maintenanceKpi(calendar.data ?? []), [calendar.data])

  const nextFault = useMemo(() => {
    const withDate = (faults.data?.faults ?? []).filter((f) => f.predicted_at)
    if (!withDate.length) return null
    return [...withDate].sort((a, b) => new Date(a.predicted_at) - new Date(b.predicted_at))[0]
  }, [faults.data])

  const recentAnomalies = (anomalies.data ?? []).slice(0, ANOMALIES_PREVIEW)

  const fmtDay = (d) => new Date(d).toLocaleDateString(locale, { day: '2-digit', month: 'short', year: 'numeric' })
  const fmtWhen = (iso) => new Date(iso).toLocaleString(locale, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

  return (
    <div className="flex flex-col gap-6">
      {/* Score global + sous-scores — 24 dernières heures */}
      <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        <Panel title={t('overview.scoreTitle')} subtitle={t('overview.last24h')}>
          <ApiState loading={overview.loading} error={overview.error}>
            {overview.data && (() => {
              const o = overview.data
              return (
                <>
                  <div className="flex items-end gap-3">
                    <span className="num" style={{ fontSize: 44, fontWeight: 700, lineHeight: 1, color: STATUS_CHART_COLOR[o.status] }}>{o.global_score.toFixed(1)}</span>
                    <span className="num" style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>/ 100</span>
                    <span style={{ marginBottom: 6, marginLeft: 'auto' }}><StatusBadge status={o.status} /></span>
                  </div>
                  <div style={{ marginTop: 6 }}>
                    <DeltaTag value={o.global_score - o.previous_score} suffix={t('siteHealth.vsLast')} />
                  </div>
                </>
              )
            })()}
          </ApiState>
        </Panel>

        <Panel title={t('overview.subScoresTitle')} subtitle={t('overview.last24h')}>
          <ApiState loading={overview.loading} error={overview.error}>
            {overview.data && (
              <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))' }}>
                {overview.data.domain_scores.map((d) => (
                  <div key={d.domain} style={{ padding: 'var(--space-3)', background: 'var(--surface-inset)', borderRadius: 'var(--radius-md)' }}>
                    <div className="flex items-center justify-between gap-2">
                      <span style={{ fontSize: 12, fontWeight: 600 }}>{t(`siteHealth.${DOMAIN_LABEL_KEY[d.domain]}`)}</span>
                      <StatusBadge status={d.status} />
                    </div>
                    <span className="num" style={{ fontSize: 20, fontWeight: 700, color: STATUS_CHART_COLOR[d.status] }}>{d.score.toFixed(1)}</span>
                    <div style={{ marginTop: 2 }}>
                      <DeltaTag value={d.score - d.previous_score} suffix={t('siteHealth.vsLast')} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ApiState>
        </Panel>
      </div>

      {/* Prochaine panne prédite */}
      <Panel
        title={t('overview.nextFaultTitle')}
        subtitle={t('overview.nextFaultSub')}
        actions={<Link to="/forecast" style={viewAllStyle}>{t('overview.viewAll')} →</Link>}
      >
        <ApiState loading={faults.loading} error={faults.error}>
          {faults.data && (
            nextFault ? (
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>{t(`siteHealth.${FAMILY_DOMAIN_LABEL_KEY[nextFault.family]}`)}</div>
                  <div className="num" style={{ fontSize: 14, fontWeight: 600, marginTop: 6 }}>
                    {t('forecast.predictedAround', { date: fmtWhen(nextFault.predicted_at) })}
                  </div>
                  {nextFault.note && <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.5 }}>{nextFault.note}</p>}
                </div>
                <StatusBadge status={nextFault.severity} />
              </div>
            ) : (
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{t('forecast.noFaultPredicted')}</p>
            )
          )}
        </ApiState>
      </Panel>

      {/* Aperçu des anomalies récentes */}
      <Panel
        title={t('overview.anomaliesTitle')}
        subtitle={t('overview.anomaliesSub', { n: recentAnomalies.length })}
        actions={<Link to="/anomalies" style={viewAllStyle}>{t('overview.viewAll')} →</Link>}
      >
        <ApiState loading={anomalies.loading} error={anomalies.error}>
          {anomalies.data && (
            recentAnomalies.length === 0 ? (
              <p style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{t('anomalies.empty')}</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: 12.5 }}>
                  <thead>
                    <tr className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)', textAlign: 'left' }}>
                      {[t('anomalies.colStart'), t('anomalies.colEquip'), t('anomalies.colSev'), t('anomalies.colStatus')].map((h) => (
                        <th key={h} style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {recentAnomalies.map((a) => (
                      <tr key={a.id} style={{ borderBottom: '1px solid var(--hairline)' }}>
                        <td className="num" style={{ padding: '9px 10px', whiteSpace: 'nowrap' }}>{new Date(a.start).toLocaleString(locale)}</td>
                        <td style={{ padding: '9px 10px' }}>{a.equipment}</td>
                        <td style={{ padding: '9px 10px' }}><StatusBadge status={a.severity === 'critical' ? 'critical' : 'alert'} /></td>
                        <td className="num" style={{ padding: '9px 10px', color: 'var(--text-muted)' }}>{STATUS_LABEL[a.status] ?? a.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </ApiState>
      </Panel>

      {/* Prochaine maintenance + nombre cette semaine */}
      <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <ApiState loading={calendar.loading} error={calendar.error}>
          {calendar.data && (
            <>
              <KpiCard label={t('maintenance.kpiNext')}>
                {nextPm ? (
                  <>
                    <div style={{ fontSize: 20, fontWeight: 700 }}>{nextPm.equipment}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="num" style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fmtDay(nextPm.next_pm_date)}</span>
                      <DueBadge days={nextPm.days_remaining} />
                    </div>
                  </>
                ) : (
                  <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>{t('maintenance.noneScheduled')}</div>
                )}
              </KpiCard>
              <KpiCard label={t('maintenance.kpiWeek')}>
                <div className="flex items-baseline gap-2">
                  <span className="num" style={{ fontSize: 26, fontWeight: 600, lineHeight: 1 }}>{thisWeekCount}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('maintenance.kpiWeekSub')}</span>
                </div>
              </KpiCard>
            </>
          )}
        </ApiState>
      </div>
    </div>
  )
}
