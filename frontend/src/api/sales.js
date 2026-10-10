import { apiFetch } from './client'

const qs = (obj) => {
  const p = new URLSearchParams()
  Object.entries(obj).forEach(([k, v]) => v !== undefined && v !== null && v !== '' && p.set(k, v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const listSales = (filters = {}) => apiFetch(`/api/sales${qs(filters)}`)
export const createSale = (body) => apiFetch('/api/sales', { method: 'POST', body })
export const deleteSale = (id) => apiFetch(`/api/sales/${id}`, { method: 'DELETE' })
export const getSalesSummary = (days = 30) => apiFetch(`/api/sales/summary?days=${days}`)
