import { apiFetch } from './client'

export const listCommodities = () => apiFetch('/api/reference/commodities')
