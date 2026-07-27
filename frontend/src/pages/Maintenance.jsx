import { useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import { useLang } from '../i18n'
import Panel from '../components/Panel'
import PMCalendar from '../components/PMCalendar'

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
  const { t } = useLang()
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
      {/* Calendrier — élément dominant. Cliquer une PM la charge dans le formulaire. */}
      <Panel title={t('maintenance.calTitle')} subtitle={t('maintenance.calSub')}>
        <ApiState loading={calendar.loading} error={calendar.error}>
          {calendar.data && <PMCalendar entries={calendar.data} onSelect={startEdit} />}
        </ApiState>
      </Panel>

      {/* Formulaire compact — création ou édition */}
      <Panel
        title={editingId ? t('maintenance.formEdit', { id: editingId }) : t('maintenance.formCreate')}
        subtitle={t('maintenance.formSub')}
      >
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {t('maintenance.equipment')}
            <input required value={form.equipment} onChange={(e) => setForm({ ...form, equipment: e.target.value })} placeholder="STULZ-03" style={{ ...inputStyle, width: 160 }} />
          </label>
          <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {t('maintenance.lastPm')}
            <input required type="date" value={form.last_pm_date} onChange={(e) => setForm({ ...form, last_pm_date: e.target.value })} style={inputStyle} />
          </label>
          <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {t('maintenance.period')}
            <span className="flex gap-2">
              <input required type="number" min="1" value={form.period_value} onChange={(e) => setForm({ ...form, period_value: e.target.value })} style={{ ...inputStyle, width: 70 }} />
              <select value={form.period_unit} onChange={(e) => setForm({ ...form, period_unit: e.target.value })} style={inputStyle}>
                <option value="days">{t('maintenance.days')}</option>
                <option value="weeks">{t('maintenance.weeks')}</option>
                <option value="months">{t('maintenance.months')}</option>
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
            {submitting ? t('maintenance.compute') : editingId ? t('maintenance.update') : t('maintenance.schedule')}
          </button>
          {editingId && (
            <>
              <button
                type="button"
                onClick={() => remove(editingId)}
                disabled={busyId === editingId}
                style={{ ...rowBtn(true), padding: '9px 14px', fontSize: 12 }}
              >
                {t('maintenance.delete')}
              </button>
              <button type="button" onClick={cancelEdit} style={{ ...rowBtn(), padding: '9px 14px', fontSize: 12 }}>
                {t('maintenance.cancel')}
              </button>
            </>
          )}
        </form>
        {submitError && (
          <p style={{ fontSize: 12, color: 'var(--status-critical)', marginTop: 10 }}>
            {t('maintenance.fail', { msg: submitError.message })}
          </p>
        )}
      </Panel>
    </div>
  )
}
