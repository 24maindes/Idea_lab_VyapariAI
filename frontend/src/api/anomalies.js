import { apiFetch } from './client'

// filters: { status: all|unread|read, severity, type, productId }
export const listAlerts = (filters = {}) => {
  const p = new URLSearchParams()
  Object.entries(filters).forEach(([k, v]) => v && v !== 'all' && p.set(k, v))
  const s = p.toString()
  return apiFetch(`/api/alerts${s ? `?${s}` : ''}`)
}
export const getAlertCount = () => apiFetch('/api/alerts/count')
export const scanAlerts = () => apiFetch('/api/alerts/scan', { method: 'POST' })
export const markAlertRead = (id) => apiFetch(`/api/alerts/${id}/read`, { method: 'PATCH' })
export const markAllRead = () => apiFetch('/api/alerts/read-all', { method: 'PATCH' })
