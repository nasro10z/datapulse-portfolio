import { useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import Panel from '../components/Panel'

const UNIT_LABEL = { days: 'jours', weeks: 'semaines', months: 'mois' }

const inputStyle = {
  background: 'var(--surface-inset)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text)',
  fontSize: 13,
  padding: '8px 10px',
}

export default function Maintenance() {
  const calendar = useApi(api.maintenanceCalendar)
  const [form, setForm] = useState({
    equipment: '',
    last_pm_date: '',
    period_value: 3,
    period_unit: 'months',
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError(null)
    try {
      await api.scheduleMaintenance({ ...form, period_value: Number(form.period_value) })
      calendar.reload()
    } catch (err) {
      setSubmitError(err)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Calendrier dominant (liste chronologique en Phase 2, vue calendrier en Phase 6) */}
      <Panel title="Planning calculé" subtitle="Prochaines maintenances préventives">
        <ApiState loading={calendar.loading} error={calendar.error}>
          {calendar.data && (
            <div style={{ overflowX: 'auto' }}>
              <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: 12.5 }}>
                <thead>
                  <tr
                    className="num"
                    style={{
                      fontSize: 10,
                      letterSpacing: 'var(--tracking-caps)',
                      textTransform: 'uppercase',
                      color: 'var(--text-muted)',
                      textAlign: 'left',
                    }}
                  >
                    {['Équipement', 'Dernière PM', 'Période', 'Prochaine PM', 'Jours restants'].map((h) => (
                      <th key={h} style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {calendar.data.map((c) => (
                    <tr key={c.id} style={{ borderBottom: '1px solid var(--hairline)' }}>
                      <td style={{ padding: '9px 10px' }}>{c.equipment}</td>
                      <td className="num" style={{ padding: '9px 10px' }}>{c.last_pm_date}</td>
                      <td className="num" style={{ padding: '9px 10px' }}>
                        {c.period_value} {UNIT_LABEL[c.period_unit]}
                      </td>
                      <td className="num" style={{ padding: '9px 10px', fontWeight: 600 }}>{c.next_pm_date}</td>
                      <td
                        className="num"
                        style={{
                          padding: '9px 10px',
                          color: c.days_remaining <= 7 ? 'var(--status-watch)' : 'var(--text-muted)',
                        }}
                      >
                        J−{c.days_remaining}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ApiState>
      </Panel>

      {/* Formulaire compact, secondaire */}
      <Panel title="Planifier une PM" subtitle="Équipement · dernière PM · période → date calculée">
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Équipement
            <input
              required
              value={form.equipment}
              onChange={(e) => setForm({ ...form, equipment: e.target.value })}
              placeholder="STULZ-03"
              style={{ ...inputStyle, width: 160 }}
            />
          </label>
          <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Date de dernière PM
            <input
              required
              type="date"
              value={form.last_pm_date}
              onChange={(e) => setForm({ ...form, last_pm_date: e.target.value })}
              style={inputStyle}
            />
          </label>
          <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Période
            <span className="flex gap-2">
              <input
                required
                type="number"
                min="1"
                value={form.period_value}
                onChange={(e) => setForm({ ...form, period_value: e.target.value })}
                style={{ ...inputStyle, width: 70 }}
              />
              <select
                value={form.period_unit}
                onChange={(e) => setForm({ ...form, period_unit: e.target.value })}
                style={inputStyle}
              >
                <option value="days">jours</option>
                <option value="weeks">semaines</option>
                <option value="months">mois</option>
              </select>
            </span>
          </label>
          <button
            type="submit"
            disabled={submitting}
            style={{
              background: 'var(--accent)',
              color: 'var(--text-on-accent)',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: 13,
              fontWeight: 600,
              padding: '9px 18px',
              cursor: submitting ? 'wait' : 'pointer',
            }}
          >
            {submitting ? 'Calcul…' : 'Planifier'}
          </button>
        </form>
        {submitError && (
          <p style={{ fontSize: 12, color: 'var(--status-critical)', marginTop: 10 }}>
            Échec de la planification : {submitError.message}
          </p>
        )}
      </Panel>
    </div>
  )
}
