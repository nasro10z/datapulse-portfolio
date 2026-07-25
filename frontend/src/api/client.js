/** Client HTTP minimal vers le backend FastAPI (proxy Vite /api → :8000). */

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`API ${res.status} ${res.statusText} — ${path}${body ? ` : ${body}` : ''}`)
  }
  return res.json()
}

export const api = {
  // Health
  healthOverview: () => request('/api/health/overview'),
  healthForecast: (horizon = '24h') => request(`/api/health/forecast?horizon=${horizon}`),

  // Anomalies
  anomalies: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/anomalies${qs ? `?${qs}` : ''}`)
  },
  anomalyStats: () => request('/api/anomalies/stats'),
  anomalyHistogram: (bucket = 'day') => request(`/api/anomalies/histogram?bucket=${bucket}`),
  updateAnomalyStatus: (id, status) =>
    request(`/api/anomalies/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),

  // Maintenance
  scheduleMaintenance: (payload) =>
    request('/api/maintenance/schedule', { method: 'POST', body: JSON.stringify(payload) }),
  maintenanceCalendar: () => request('/api/maintenance/calendar'),

  // Reminders
  reminders: () => request('/api/reminders'),
}
