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
  // 204 No Content (DELETE, snooze/acknowledge) : pas de corps à parser
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Health
  healthOverview: () => request('/api/health/overview'),
  healthForecast: (horizon = '24h') => request(`/api/health/forecast?horizon=${horizon}`),
  healthHistory: (range = '7d') => request(`/api/health/history?range=${range}`),
  predictedFaults: (horizon = '24h') => request(`/api/health/predicted-faults?horizon=${horizon}`),
  subScoreForecast: (horizon = '24h') => request(`/api/health/forecast/sub-scores?horizon=${horizon}`),

  // Anomalies
  anomalies: (params = {}) => {
    const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v))
    const qs = new URLSearchParams(clean).toString()
    return request(`/api/anomalies${qs ? `?${qs}` : ''}`)
  },
  anomalyStats: () => request('/api/anomalies/stats'),
  anomalyHistogram: (bucket = 'day') => request(`/api/anomalies/histogram?bucket=${bucket}`),
  anomalyWindowStats: (window = '24h') => request(`/api/anomalies/window-stats?window=${window}`),
  updateAnomalyStatus: (id, status) =>
    request(`/api/anomalies/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),

  // Maintenance
  scheduleMaintenance: (payload) =>
    request('/api/maintenance/schedule', { method: 'POST', body: JSON.stringify(payload) }),
  updateMaintenance: (id, payload) =>
    request(`/api/maintenance/schedule/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteMaintenance: (id) =>
    request(`/api/maintenance/schedule/${id}`, { method: 'DELETE' }),
  maintenanceCalendar: () => request('/api/maintenance/calendar'),
  maintenanceEquipmentOptions: () => request('/api/maintenance/equipment'),

  // Reminders
  reminders: () => request('/api/reminders'),
  remindersCount: () => request('/api/reminders/count'),
  acknowledgeReminder: (id) =>
    request(`/api/reminders/${id}/acknowledge`, { method: 'POST' }),
  snoozeReminder: (id, hours) =>
    request(`/api/reminders/${id}/snooze`, { method: 'POST', body: JSON.stringify({ hours }) }),
}
