import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithLang as render } from '../../test/utils'
import Maintenance from '../Maintenance'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    maintenanceCalendar: vi.fn(),
    maintenanceEquipmentOptions: vi.fn(),
    scheduleMaintenance: vi.fn(),
    updateMaintenance: vi.fn(),
    deleteMaintenance: vi.fn(),
  },
}))

const entry = {
  id: 'PM-0001', equipment: 'STULZ-05', last_pm_date: '2026-07-01',
  period_value: 3, period_unit: 'months', next_pm_date: '2026-10-01', days_remaining: 67,
  assigned_to: null, notes: null,
}

beforeEach(() => {
  api.maintenanceCalendar.mockResolvedValue([])
  api.maintenanceEquipmentOptions.mockResolvedValue(['STULZ-01', 'STULZ-05', 'UPS-01', 'GEN-01'])
  api.scheduleMaintenance.mockResolvedValue(entry)
})

describe('Parcours : planifier une PM', () => {
  it('soumet le formulaire avec le bon payload et rafraîchit le calendrier', async () => {
    const user = userEvent.setup()
    render(<Maintenance />)

    // le formulaire de planification est présent, en premier (avant le calendrier)
    const equip = await screen.findByLabelText('Équipement')
    await user.selectOptions(equip, 'STULZ-05')
    fireEvent.change(document.querySelector('input[type="date"]'), { target: { value: '2026-07-01' } })
    await user.click(screen.getByRole('button', { name: 'Planifier' }))

    await waitFor(() => expect(api.scheduleMaintenance).toHaveBeenCalledTimes(1))
    expect(api.scheduleMaintenance).toHaveBeenCalledWith({
      equipment: 'STULZ-05',
      last_pm_date: '2026-07-01',
      period_value: 3,
      period_unit: 'months',
      assigned_to: undefined,
      notes: undefined,
    })
    // le calendrier est rechargé après création (1 au montage + 1 après submit)
    await waitFor(() => expect(api.maintenanceCalendar).toHaveBeenCalledTimes(2))
  })

  it('envoie technicien et notes quand renseignés', async () => {
    const user = userEvent.setup()
    render(<Maintenance />)

    const equip = await screen.findByLabelText('Équipement')
    await user.selectOptions(equip, 'UPS-01')
    fireEvent.change(document.querySelector('input[type="date"]'), { target: { value: '2026-07-01' } })
    await user.type(screen.getByLabelText('Technicien assigné'), 'A. B.')
    await user.type(screen.getByLabelText('Notes'), 'Vérifier fluide')
    await user.click(screen.getByRole('button', { name: 'Planifier' }))

    await waitFor(() => expect(api.scheduleMaintenance).toHaveBeenCalledWith(
      expect.objectContaining({ assigned_to: 'A. B.', notes: 'Vérifier fluide' }),
    ))
  })
})

describe('Parcours : calendrier cliquable', () => {
  it('affiche le détail du jour sélectionné', async () => {
    // le calendrier affiche le mois courant par défaut : la PM de test doit y tomber
    const today = new Date()
    const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    const todayEntry = { ...entry, id: 'PM-0002', next_pm_date: todayIso, days_remaining: 0 }
    api.maintenanceCalendar.mockResolvedValue([todayEntry])
    const user = userEvent.setup()
    render(<Maintenance />)

    await screen.findByText('Prochaine maintenance')
    const dayCell = await screen.findByRole('button', { name: new RegExp(`Détail du jour ${todayIso}`) })
    await user.click(dayCell)

    expect(await screen.findByText('STULZ-05')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Modifier' })).toBeInTheDocument()
  })
})
