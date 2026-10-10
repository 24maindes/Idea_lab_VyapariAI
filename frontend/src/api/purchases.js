import { apiFetch } from './client'

const qs = (obj) => {
  const p = new URLSearchParams()
  Object.entries(obj).forEach(([k, v]) => v !== undefined && v !== null && v !== '' && p.set(k, v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

// filters: { productId, supplierId, from, to, page, pageSize, sort }
export const listPurchases = (filters = {}) => apiFetch(`/api/purchases${qs(filters)}`)
export const createPurchase = (body) => apiFetch('/api/purchases', { method: 'POST', body })
export const deletePurchase = (id) => apiFetch(`/api/purchases/${id}`, { method: 'DELETE' })
