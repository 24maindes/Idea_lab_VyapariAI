import { apiFetch } from './client'

// { message, language: 'en'|'hi'|'mr', productId? } -> { answer, language, usedFallback, sources, matchedProducts }
export const sendChat = (body) => apiFetch('/api/advisor/chat', { method: 'POST', body })
export const getHistory = (limit = 30) => apiFetch(`/api/advisor/history?limit=${limit}`)
export const clearHistory = () => apiFetch('/api/advisor/history', { method: 'DELETE' })
