import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithLang as render } from '../../test/utils'
import Maintenance from '../Maintenance'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    maintenanceCalendar: vi.fn(),
    scheduleMaintenance: vi.fn(),
    updateMaintenance: vi.fn(),
    deleteMaintenance: vi.fn(),
  },
}))

const entry = {
  id: 'PM-0001', equipment: 'STULZ-05', last_pm_date: '2026-07-01',
  period_value: 3, period_unit: 'months', next_pm_date: '2026-10-01', days_remaining: 67,
}

beforeEach(() => {
  api.maintenanceCalendar.mockResolvedValue([])
  api.scheduleMaintenance.mockResolvedValue(entry)
})

describe('Parcours : planifier une PM', () => {
  it('soumet le formulaire avec le bon payload et rafraîchit le calendrier', async () => {
    const user = userEvent.setup()
    render(<Maintenance />)

    // le formulaire de planification est présent
    const equip = await screen.findByPlaceholderText('STULZ-03')
    await user.type(equip, 'STULZ-05')
    fireEvent.change(document.querySelector('input[type="date"]'), { target: { value: '2026-07-01' } })
    await user.click(screen.getByRole('button', { name: 'Planifier' }))

    await waitFor(() => expect(api.scheduleMaintenance).toHaveBeenCalledTimes(1))
    expect(api.scheduleMaintenance).toHaveBeenCalledWith({
      equipment: 'STULZ-05',
      last_pm_date: '2026-07-01',
      period_value: 3,
      period_unit: 'months',
    })
    // le calendrier est rechargé après création (1 au montage + 1 après submit)
    await waitFor(() => expect(api.maintenanceCalendar).toHaveBeenCalledTimes(2))
  })
})
