import { apiFetch } from './client'

export const getInventory = () => apiFetch('/api/inventory')
export const getActivity = (limit = 10) => apiFetch(`/api/activity?limit=${limit}`)
