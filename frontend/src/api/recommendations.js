import { apiFetch } from './client'

export const getPurchaseRecommendations = () => apiFetch('/api/recommendations/purchase')
export const getSellingPrices = (targetMarginPct) =>
  apiFetch(`/api/recommendations/selling-price${targetMarginPct !== undefined && targetMarginPct !== null ? `?targetMarginPct=${targetMarginPct}` : ''}`)
