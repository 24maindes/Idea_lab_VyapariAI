import { apiFetch } from './client'

export const getForecast = (productId, horizon = 7) => apiFetch(`/api/forecast/${productId}?horizon=${horizon}`)
export const getModelTable = (commodity) => apiFetch(`/api/forecast/models${commodity ? `?commodity=${encodeURIComponent(commodity)}` : ''}`)
export const retrainModels = (commodity) => apiFetch(`/api/forecast/retrain${commodity ? `?commodity=${encodeURIComponent(commodity)}` : ''}`, { method: 'POST' })
export const getRetrainStatus = () => apiFetch('/api/forecast/retrain/status')
