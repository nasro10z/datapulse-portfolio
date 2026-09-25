import { useMemo, useRef, useState } from 'react'
import { api } from '../api/client'
import useApi, { ApiState } from '../hooks/useApi'
import { useLang } from '../i18n'
import { useConfig } from '../config'
import Panel from '../components/Panel'
import PMCalendar from '../components/PMCalendar'
import KpiCard from '../components/KpiCard'
import DueBadge from '../components/DueBadge'
import { maintenanceKpi } from '../utils/maintenanceKpi'

const EMPTY = { equipment: '', last_pm_date: '', period_value: 3, period_unit: 'months', assigned_to: '', notes: '' }

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

const todayIso = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function Maintenance() {
  const { t, locale } = useLang()
  const formRef = useRef(null)
  const calendar = useApi(api.maintenanceCalendar)
  const equipmentOptions = useApi(api.maintenanceEquipmentOptions)
  // Instance publique : les plannings sont figés côté API (403 sur les écritures).
  // On le lit ici pour présenter un formulaire désactivé plutôt qu'un échec à la
  // soumission. Valeur par défaut permissive : une page rendue hors provider
  // (test, story) garde le formulaire actif.
  const { pm_read_only: readOnly } = useConfig()
  const [form, setForm] = useState(EMPTY)
  const [editingId, setEditingId] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [selectedDate, setSelectedDate] = useState(todayIso())

  const { next, thisWeekCount } = useMemo(() => maintenanceKpi(calendar.data ?? []), [calendar.data])

  const dayEntries = useMemo(
    () => (calendar.data ?? []).filter((e) => e.next_pm_date === selectedDate),
    [calendar.data, selectedDate],
  )

  const startEdit = (c) => {
    setEditingId(c.id)
    setForm({
      equipment: c.equipment,
      last_pm_date: c.last_pm_date,
      period_value: c.period_value,
      period_unit: c.period_unit,
      assigned_to: c.assigned_to ?? '',
      notes: c.notes ?? '',
    })
    formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setForm(EMPTY)
  }

  const submit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError(null)
    const payload = {
      equipment: form.equipment,
      last_pm_date: form.last_pm_date,
      period_value: Number(form.period_value),
      period_unit: form.period_unit,
      assigned_to: form.assigned_to.trim() || undefined,
      notes: form.notes.trim() || undefined,
    }
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

  const fmtDate = (d) => new Date(d).toLocaleDateString(locale, { day: '2-digit', month: 'short', year: 'numeric' })

  return (
    <div className="flex flex-col gap-6">
      {/* Tout en haut : prochaine maintenance + nombre cette semaine */}
      <ApiState loading={calendar.loading} error={calendar.error}>
        {calendar.data && (
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
            <KpiCard label={t('maintenance.kpiNext')}>
              {next ? (
                <>
                  <div style={{ fontSize: 20, fontWeight: 700 }}>{next.equipment}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="num" style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fmtDate(next.next_pm_date)}</span>
                    <DueBadge days={next.days_remaining} />
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
          </div>
        )}
      </ApiState>

      {/* Formulaire — en premier, détaillé (équipement, dates, période, technicien, notes) */}
      <div ref={formRef}>
        <Panel
          title={editingId ? t('maintenance.formEdit', { id: editingId }) : t('maintenance.formCreate')}
          subtitle={readOnly ? t('maintenance.readOnlySub') : t('maintenance.formSub')}
        >
          {readOnly && (
            <div style={{
              border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
              background: 'var(--surface-inset)', color: 'var(--text-muted)',
              fontSize: 12, padding: '8px 10px', marginBottom: 12,
            }}>
              {t('maintenance.readOnly')}
            </div>
          )}
          {/* fieldset : désactive tous les champs d'un coup, bouton de soumission
              compris, sans dupliquer `disabled` sur chacun. */}
          <form onSubmit={submit}>
            <fieldset disabled={readOnly} className="flex flex-col gap-3"
                      style={{ border: 'none', margin: 0, padding: 0 }}>
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {t('maintenance.equipment')}
                <select
                  required
                  value={form.equipment}
                  onChange={(e) => setForm({ ...form, equipment: e.target.value })}
                  style={{ ...inputStyle, width: 160 }}
                >
                  <option value="" disabled>{t('maintenance.selectEquipment')}</option>
                  {(equipmentOptions.data ?? []).map((eq) => <option key={eq} value={eq}>{eq}</option>)}
                </select>
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
              <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {t('maintenance.assignedTo')}
                <input value={form.assigned_to} onChange={(e) => setForm({ ...form, assigned_to: e.target.value })} placeholder={t('maintenance.assignedToHint')} style={{ ...inputStyle, width: 160 }} />
              </label>
            </div>
            <label className="flex flex-col gap-1" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {t('maintenance.notes')}
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                rows={2}
                style={{ ...inputStyle, width: '100%', resize: 'vertical', fontFamily: 'inherit' }}
              />
            </label>
            <div className="flex items-center gap-3">
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
            </div>
            </fieldset>
          </form>
          {submitError && (
            <p style={{ fontSize: 12, color: 'var(--status-critical)', marginTop: 10 }}>
              {t('maintenance.fail', { msg: submitError.message })}
            </p>
          )}
        </Panel>
      </div>

      {/* Calendrier (cliquable) + détail du jour sélectionné */}
      <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        <Panel title={t('maintenance.calTitle')} subtitle={t('maintenance.calSub')} style={{ flex: '2 1 480px' }}>
          <ApiState loading={calendar.loading} error={calendar.error}>
            {calendar.data && <PMCalendar entries={calendar.data} selectedDate={selectedDate} onDayClick={setSelectedDate} />}
          </ApiState>
        </Panel>

        <Panel title={t('maintenance.dayDetailTitle')} subtitle={selectedDate ? fmtDate(selectedDate) : undefined}>
          {!selectedDate && <p style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{t('maintenance.dayDetailPrompt')}</p>}
          {selectedDate && dayEntries.length === 0 && (
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{t('maintenance.dayDetailEmpty')}</p>
          )}
          <div className="flex flex-col gap-3">
            {dayEntries.map((pm) => (
              <div key={pm.id} style={{ background: 'var(--surface-inset)', borderRadius: 'var(--radius-md)', padding: 'var(--space-3)' }}>
                <div className="flex items-start justify-between gap-2">
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{pm.equipment}</div>
                  <DueBadge days={pm.days_remaining} />
                </div>
                <div className="num" style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4 }}>
                  {t('maintenance.lastPm')} : {fmtDate(pm.last_pm_date)}
                </div>
                {pm.assigned_to && (
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>
                    {t('maintenance.assignedTo')} : {pm.assigned_to}
                  </div>
                )}
                {pm.notes && (
                  <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.5 }}>{pm.notes}</p>
                )}
                <div className="flex gap-1.5 mt-2">
                  <button onClick={() => startEdit(pm)} disabled={readOnly} style={rowBtn()}>{t('maintenance.modifyAction')}</button>
                  <button onClick={() => remove(pm.id)} disabled={readOnly || busyId === pm.id} style={rowBtn(true)}>{t('maintenance.delete')}</button>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  )
}
