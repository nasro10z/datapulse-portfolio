import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithLang as render } from '../../test/utils'
import Overview from '../Overview'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    healthOverview: vi.fn(),
    predictedFaults: vi.fn(),
    anomalies: vi.fn(),
    maintenanceCalendar: vi.fn(),
  },
}))

const overview = {
  global_score: 79.7, previous_score: 80.3, status: 'watch',
  domain_scores: [
    { domain: 'environment', score: 87, status: 'healthy', previous_score: 85, note: null },
    { domain: 'energy', score: 81, status: 'watch', previous_score: 83, note: null },
    { domain: 'battery', score: 66, status: 'critical', previous_score: 69, note: null },
  ],
  sub_scores: [],
  updated_at: '2026-07-28T09:00:00Z',
}

const faults = {
  horizon: '7d',
  faults: [
    { family: 'stulz', predicted_at: '2026-07-30T22:00:00Z', severity: 'alert', note: 'Basé sur le modèle HMM.' },
    { family: 'socomec', predicted_at: null, severity: null, note: null },
    { family: 'yanan', predicted_at: '2026-08-04T01:00:00Z', severity: 'alert', note: null },
  ],
}

const episode = {
  id: 'EP-0001', equipment: 'STULZ-08', type: 'sequence', severity: 'critical',
  direction: 'low', start: '2026-07-28T04:41:25Z', duration_min: 25, peak_value: 17.7, status: 'open',
  dimension: 'environment',
}

const pm = {
  id: 'PM-0004', equipment: 'GEN-01', last_pm_date: '2026-07-07', period_value: 4, period_unit: 'weeks',
  next_pm_date: '2026-08-04', days_remaining: 7, assigned_to: null, notes: null,
}

beforeEach(() => {
  api.healthOverview.mockResolvedValue(overview)
  api.predictedFaults.mockResolvedValue(faults)
  api.anomalies.mockResolvedValue([episode])
  api.maintenanceCalendar.mockResolvedValue([pm])
})

describe('Parcours : aperçu du site', () => {
  it('affiche le score global, les sous-scores, la prochaine panne, une anomalie et la prochaine PM', async () => {
    render(<Overview />)

    expect(await screen.findByText('79.7')).toBeInTheDocument()
    expect(await screen.findByText('Environnement')).toBeInTheDocument()
    // la panne la plus proche (STULZ, 30/07) est retenue plutôt que YANAN (04/08)
    expect(await screen.findByText(/Estimée autour du/)).toBeInTheDocument()
    expect(await screen.findByText('STULZ-08')).toBeInTheDocument()
    expect(await screen.findByText('GEN-01')).toBeInTheDocument()
    expect(api.predictedFaults).toHaveBeenCalledWith('7d')
  })
})
