import { useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import Panel from '../components/Panel'
import PMCalendar from '../components/PMCalendar'

const UNIT_LABEL = { days: 'jours', weeks: 'semaines', months: 'mois' }
const EMPTY = { equipment: '', last_pm_date: '', period_value: 3, period_unit: 'months' }

const inputStyle = {
  background: 'var(--surface-inset)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text)',
  fontSize: 13,
  padding: '8px 10px',
}

const rowBtn = (danger = false) => ({
  fontSize: 10.5,
  fontWeight: 600,
  padding: '4px 10px',
  borderRadius: 'var(--radius-sm)',
  border: `1px solid var(--border)`,
  background: 'transparent',
  color: danger ? 'var(--status-critical)' : 'var(--text-muted)',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
})

export default function Maintenance() {
  const calendar = useApi(api.maintenanceCalendar)
  const [form, setForm] = useState(EMPTY)
  const [editingId, setEditingId] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const startEdit = (c) => {
    setEditingId(c.id)
    setForm({
      equipment: c.equipment,
      last_pm_date: c.last_pm_date,
      period_value: c.period_value,
      period_unit: c.period_unit,
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setForm(EMPTY)
  }

  const submit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError(null)
    const payload = { ...form, period_value: Number(form.period_value) }
    try {
      if (editingId) await api.updateMaintenance(editingId, payload)
      else await api.scheduleMaintenance(payload)
      cancelEdit()
      calendar.reload()
    } catch (err) {
      setSubmitError(err)
    } finally {
      setSubmitting(false)
    }
  }

  const remove = async (id) => {
    setBusyId(id)
    try {
      await api.deleteMaintenance(id)
      if (editingId === id) cancelEdit()
      calendar.reload()
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Calendrier — élément dominant */}
      <Panel title="Calendrier des maintenances" subtitle="Prochaines PM planifiées, par urgence">
        <ApiState loading={calendar.loading} error={calendar.error}>
          {calendar.data && <PMCalendar entries={calendar.data} />}
        </ApiState>
      </Panel>

      {/* Planning calculé — liste avec édition / suppression */}
      <Panel title="Planning calculé" subtitle="Détail des maintenances — modifiable et supprimable">
        <ApiState loading={calendar.loading} error={calendar.error}>
          {calendar.data && (
            <div style={{ overflowX: 'auto' }}>
              {calendar.data.length === 0 && (
                <p style={{ fontSize: 12.5, color: 'var(--text-muted)', padding: '12px 0' }}>
                  Aucune PM planifiée. Utilisez le formulaire ci-dessous.
                </p>
              )}
              {calendar.data.length > 0 && (
                <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: 12.5 }}>
                  <thead>
                    <tr className="num" style={{ fontSize: 10, letterSpacing: 'var(--tracking-caps)', textTransform: 'uppercase', color: 'var(--text-muted)', textAlign: 'left' }}>
                      {['Équipement', 'Dernière PM', 'Période', 'Prochaine PM', 'Jours restants', ''].map((h, i) => (
                        <th key={i} style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {calendar.data.map((c) => (
                      <tr key={c.id} style={{ borderBottom: '1px solid var(--hairline)', background: editingId === c.id ? 'var(--accent-soft)' : 'transparent' }}>
                        <td style={{ padding: '9px 10px' }}>{c.equipment}</td>
                        <td className="num" style={{ padding: '9px 10px' }}>{c.last_pm_date}</td>
                        <td className="num" style={{ padding: '9px 10px' }}>{c.period_value} {UNIT_LABEL[c.period_unit]}</td>
                        <td className="num" style={{ padding: '9px 10px', fontWeight: 600 }}>{c.next_pm_date}</td>
                        <td className="num" style={{ padding: '9px 10px', color: c.days_remaining < 0 ? 'var(--status-critical)' : c.days_remaining <= 7 ? 'var(--status-watch)' : 'var(--text-muted)' }}>
                          J−{c.days_remaining}
                        </td>
                        <td style={{ padding: '9px 10px' }}>
                          <span className="flex gap-1.5 justify-end">
                            <button className="num" style={rowBtn()} onClick={() => startEdit(c)}>Éditer</button>
                            <button className="num" style={rowBtn(true)} disabled={busyId === c.id} onClick={() => remove(c.id)}>Supprimer</button>
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </ApiState>
      </Panel>

      {/* Formulaire compact — création ou édition */}
      <Panel
        title={editingId ? `Modifier ${editingId}` : 'Planifier une PM'}
        subtitle="Équipement · dernière PM · période → date calculée"
      >
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Équipement
            <input required value={form.equipment} onChange={(e) => setForm({ ...form, equipment: e.target.value })} placeholder="STULZ-03" style={{ ...inputStyle, width: 160 }} />
          </label>
          <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Date de dernière PM
            <input required type="date" value={form.last_pm_date} onChange={(e) => setForm({ ...form, last_pm_date: e.target.value })} style={inputStyle} />
          </label>
          <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Période
            <span className="flex gap-2">
              <input required type="number" min="1" value={form.period_value} onChange={(e) => setForm({ ...form, period_value: e.target.value })} style={{ ...inputStyle, width: 70 }} />
              <select value={form.period_unit} onChange={(e) => setForm({ ...form, period_unit: e.target.value })} style={inputStyle}>
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
              background: 'var(--accent)', color: 'var(--text-on-accent)', border: 'none',
              borderRadius: 'var(--radius-sm)', fontSize: 13, fontWeight: 600, padding: '9px 18px',
              cursor: submitting ? 'wait' : 'pointer',
            }}
          >
            {submitting ? 'Calcul…' : editingId ? 'Mettre à jour' : 'Planifier'}
          </button>
          {editingId && (
            <button type="button" onClick={cancelEdit} style={{ ...rowBtn(), padding: '9px 14px', fontSize: 12 }}>
              Annuler
            </button>
          )}
        </form>
        {submitError && (
          <p style={{ fontSize: 12, color: 'var(--status-critical)', marginTop: 10 }}>
            Échec : {submitError.message}
          </p>
        )}
      </Panel>
    </div>
  )
}
