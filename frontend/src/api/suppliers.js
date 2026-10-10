import { apiFetch } from './client'

export const listSuppliers = () => apiFetch('/api/suppliers')
export const createSupplier = (body) => apiFetch('/api/suppliers', { method: 'POST', body })
export const updateSupplier = (id, body) => apiFetch(`/api/suppliers/${id}`, { method: 'PUT', body })
export const deleteSupplier = (id) => apiFetch(`/api/suppliers/${id}`, { method: 'DELETE' })
