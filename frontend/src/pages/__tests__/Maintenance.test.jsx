import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
  it('soumet le formulaire et rafraîchit le calendrier', async () => {
    const user = userEvent.setup()
    // calendrier vide au départ, puis contenant la nouvelle PM après reload
    api.maintenanceCalendar.mockResolvedValueOnce([]).mockResolvedValue([entry])
    render(<Maintenance />)

    await screen.findByText(/Aucune PM planifiée/i)

    await user.type(screen.getByPlaceholderText('STULZ-03'), 'STULZ-05')
    fireEvent.change(document.querySelector('input[type="date"]'), { target: { value: '2026-07-01' } })
    await user.click(screen.getByRole('button', { name: 'Planifier' }))

    await waitFor(() => expect(api.scheduleMaintenance).toHaveBeenCalledTimes(1))
    expect(api.scheduleMaintenance).toHaveBeenCalledWith({
      equipment: 'STULZ-05',
      last_pm_date: '2026-07-01',
      period_value: 3,
      period_unit: 'months',
    })
    // la PM créée apparaît après le reload
    expect(await screen.findAllByText('STULZ-05')).not.toHaveLength(0)
  })
})
