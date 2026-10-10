import { apiFetch } from './client'

export const listProducts = ({ q, category } = {}) => {
  const p = new URLSearchParams()
  if (q) p.set('q', q)
  if (category && category !== 'All') p.set('category', category)
  const s = p.toString()
  return apiFetch(`/api/products${s ? `?${s}` : ''}`)
}
export const createProduct = (body) => apiFetch('/api/products', { method: 'POST', body })
export const updateProduct = (id, body) => apiFetch(`/api/products/${id}`, { method: 'PUT', body })
export const deleteProduct = (id) => apiFetch(`/api/products/${id}`, { method: 'DELETE' })
