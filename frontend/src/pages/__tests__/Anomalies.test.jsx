import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithLang as render } from '../../test/utils'
import Anomalies from '../Anomalies'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    anomalyStats: vi.fn(),
    anomalies: vi.fn(),
    anomalyWindowStats: vi.fn(),
    updateAnomalyStatus: vi.fn(),
  },
}))

const openEpisode = {
  id: 'EP-0001', equipment: 'STULZ-08', type: 'sequence', severity: 'critical',
  direction: 'high', start: '2026-07-25T17:41:00Z', duration_min: 25, peak_value: 31.2, status: 'open',
  dimension: 'environment',
}

const stats = {
  total: 1, anomaly_rate_pct: 2.63, mtba_hours: 48.5,
  by_type: { collective: 0, duration: 0, sequence: 1 },
  by_severity: { alert: 0, critical: 1 },
  by_direction: { high: 1, low: 0 },
  by_status: { open: 1, acknowledged: 0, resolved: 0 },
  top_equipment: 'STULZ-08', top_equipment_count: 1,
}

const windowStats = {
  window: '24h', total: 1, previous_total: 0, rate_pct: 1.5,
  top_family: 'stulz', top_family_count: 1,
  by_dimension: { environment: 1, scada: 0 },
}

beforeEach(() => {
  api.anomalyStats.mockResolvedValue(stats)
  api.anomalies.mockResolvedValue([openEpisode])
  api.anomalyWindowStats.mockImplementation((w) => Promise.resolve({ ...windowStats, window: w }))
  api.updateAnomalyStatus.mockResolvedValue({ ...openEpisode, status: 'acknowledged' })
})

describe('Parcours : consulter et acquitter une anomalie', () => {
  it('affiche le KPI de fenêtre et un épisode', async () => {
    render(<Anomalies />)
    expect(await screen.findByText('Total anomalies')).toBeInTheDocument()
    // STULZ-08 apparaît dans la ligne du tableau et dans le filtre équipement
    expect((await screen.findAllByText('STULZ-08')).length).toBeGreaterThan(0)
  })

  it('acquitte un épisode ouvert via le bouton Acquitter', async () => {
    const user = userEvent.setup()
    render(<Anomalies />)
    const ackBtn = await screen.findByRole('button', { name: 'Acquitter' })
    await user.click(ackBtn)

    await waitFor(() => expect(api.updateAnomalyStatus).toHaveBeenCalledWith('EP-0001', 'acknowledged'))
    // stats rechargées après l'action (1 au montage + 1 au reload)
    await waitFor(() => expect(api.anomalyStats).toHaveBeenCalledTimes(2))
  })

  it('filtre par sévérité via le sélecteur', async () => {
    const user = userEvent.setup()
    render(<Anomalies />)
    await screen.findByText('STULZ-08')
    await user.selectOptions(screen.getByLabelText('Filtrer par sévérité'), 'critical')
    // le filtre déclenche un nouvel appel avec le paramètre severity
    await waitFor(() =>
      expect(api.anomalies).toHaveBeenCalledWith(expect.objectContaining({ severity: 'critical' })),
    )
  })

  it('recharge au changement de fenêtre 24h/7j', async () => {
    const user = userEvent.setup()
    render(<Anomalies />)
    await screen.findByText('STULZ-08')
    expect(api.anomalyWindowStats).toHaveBeenCalledWith('24h')
    await user.click(screen.getByRole('button', { name: '7 jours' }))
    await waitFor(() => expect(api.anomalyWindowStats).toHaveBeenCalledWith('7d'))
  })
})
