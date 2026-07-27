import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import { useLang } from '../i18n'
import Panel from '../components/Panel'
import HealthGauge from '../components/HealthGauge'
import EquipmentCard from '../components/EquipmentCard'
import StatusBadge from '../components/StatusBadge'

export default function SiteHealth() {
  const { data, loading, error } = useApi(api.healthOverview)
  const { t, locale } = useLang()

  return (
    <ApiState loading={loading} error={error}>
      {data && (
        <div className="flex flex-col gap-6">
          <Panel title={t('siteHealth.title')} subtitle={t('siteHealth.subtitle', { site: 'MSC-10' })}>
            <div className="flex flex-wrap items-center gap-8">
              <HealthGauge score={data.global_score} status={data.status} label={t('siteHealth.scoreGlobal')} />
              <div>
                <StatusBadge status={data.status} />
                <p className="num mt-3" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {t('common.updatedAt', { date: new Date(data.updated_at).toLocaleString(locale) })}
                </p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 420, marginTop: 8 }}>
                  {t('siteHealth.decision')}
                </p>
              </div>
            </div>
          </Panel>

          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
            {data.sub_scores.map((s) => (
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
        </div>
      )}
    </ApiState>
  )
}
