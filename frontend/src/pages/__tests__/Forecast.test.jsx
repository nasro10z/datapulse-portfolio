import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithLang as render } from '../../test/utils'
import Forecast from '../Forecast'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    healthForecast: vi.fn(),
    predictedFaults: vi.fn(),
    subScoreForecast: vi.fn(),
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

const faults = (horizon) => ({
  horizon,
  faults: [
    { family: 'stulz', label: 'Climatisation', predicted_at: null, severity: null, note: 'Aucun franchissement prévu.' },
    { family: 'socomec', label: 'Onduleurs', predicted_at: null, severity: null, note: 'Aucune dégradation prévue.' },
    { family: 'yanan', label: 'Groupes électrogènes', predicted_at: '2026-07-27T12:00:00Z', severity: 'alert', note: 'Baseline indicative.' },
  ],
})

const subScoreForecast = (horizon) => ({
  horizon,
  series: [
    { family: 'stulz', label: 'Climatisation', points: forecast(horizon).points },
    { family: 'socomec', label: 'Onduleurs', points: forecast(horizon).points },
    { family: 'yanan', label: 'Groupes électrogènes', points: forecast(horizon).points },
  ],
})

beforeEach(() => {
  api.healthForecast.mockImplementation((h) => Promise.resolve(forecast(h)))
  api.predictedFaults.mockImplementation((h) => Promise.resolve(faults(h)))
  api.subScoreForecast.mockImplementation((h) => Promise.resolve(subScoreForecast(h)))
})

describe('Parcours : lire le forecast', () => {
  it('rend les pannes prédites, le graphique global et les sous-scores', async () => {
    render(<Forecast />)
    await waitFor(() => expect(document.querySelector('svg')).toBeInTheDocument())
    expect(await screen.findAllByText('Climatisation')).toHaveLength(2) // carte panne + carte forecast
    expect(screen.getByText('Aucune panne prévue')).toBeInTheDocument()
    expect(api.healthForecast).toHaveBeenCalledWith('24h')
    expect(api.predictedFaults).toHaveBeenCalledWith('24h')
    expect(api.subScoreForecast).toHaveBeenCalledWith('24h')
  })

  it('recharge tout au changement d’horizon', async () => {
    const user = userEvent.setup()
    render(<Forecast />)
    await waitFor(() => expect(document.querySelector('svg')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: '7 jours' }))
    await waitFor(() => expect(api.healthForecast).toHaveBeenCalledWith('7d'))
    expect(api.predictedFaults).toHaveBeenCalledWith('7d')
    expect(api.subScoreForecast).toHaveBeenCalledWith('7d')
  })
})
