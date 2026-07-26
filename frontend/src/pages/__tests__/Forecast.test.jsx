import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Forecast from '../Forecast'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    healthForecast: vi.fn(),
    healthOverview: vi.fn(),
  },
}))

const forecast = (horizon) => ({
  horizon,
  points: [
    { timestamp: '2026-07-26T10:00:00Z', value: 24.6, lower: 24.4, upper: 24.8, is_forecast: false },
    { timestamp: '2026-07-26T11:00:00Z', value: 24.8, lower: 24.6, upper: 25.0, is_forecast: false },
    { timestamp: '2026-07-26T12:00:00Z', value: 25.1, lower: 24.6, upper: 25.6, is_forecast: true },
  ],
  threshold_crossings: [],
})

const overview = {
  global_score: 82, status: 'healthy', updated_at: '2026-07-26T10:00:00Z',
  sub_scores: [
    { family: 'stulz', label: 'Climatisation', score: 82, status: 'healthy', trend: 'stable', unit_count: 10 },
  ],
}

beforeEach(() => {
  api.healthForecast.mockImplementation((h) => Promise.resolve(forecast(h)))
  api.healthOverview.mockResolvedValue(overview)
})

describe('Parcours : lire le forecast', () => {
  it('rend le graphique et les sous-scores', async () => {
    render(<Forecast />)
    // le chart SVG est rendu une fois les points chargés
    await waitFor(() => expect(document.querySelector('svg')).toBeInTheDocument())
    expect(await screen.findByText('Climatisation')).toBeInTheDocument()
    expect(api.healthForecast).toHaveBeenCalledWith('24h')
  })

  it('recharge la prévision au changement d’horizon', async () => {
    const user = userEvent.setup()
    render(<Forecast />)
    await waitFor(() => expect(document.querySelector('svg')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: '7 jours' }))
    await waitFor(() => expect(api.healthForecast).toHaveBeenCalledWith('7d'))
  })
})
