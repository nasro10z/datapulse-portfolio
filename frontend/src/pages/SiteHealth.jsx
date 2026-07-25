import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import Panel from '../components/Panel'
import HealthGauge from '../components/HealthGauge'
import EquipmentCard from '../components/EquipmentCard'
import StatusBadge from '../components/StatusBadge'

export default function SiteHealth() {
  const { data, loading, error } = useApi(api.healthOverview)

  return (
    <ApiState loading={loading} error={error}>
      {data && (
        <div className="flex flex-col gap-6">
          <Panel title="Health score du site" subtitle="Score agrégé — MSC-10">
            <div className="flex flex-wrap items-center gap-8">
              <HealthGauge score={data.global_score} status={data.status} label="Score global" />
              <div>
                <StatusBadge status={data.status} />
                <p className="num mt-3" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Mis à jour : {new Date(data.updated_at).toLocaleString('fr-FR')}
                </p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 420, marginTop: 8 }}>
                  Couche d’aide à la décision : ce score synthétise l’état des familles
                  d’équipement, il ne déclenche aucune action automatique.
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
