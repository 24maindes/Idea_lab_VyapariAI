// Small formatting helpers shared by many pages.

export const rupee = (n, digits = 2) =>
  n === null || n === undefined || Number.isNaN(n)
    ? '-'
    : '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: digits })

export const pct = (n, digits = 1) =>
  n === null || n === undefined ? '-' : `${n > 0 ? '+' : ''}${Number(n).toFixed(digits)}%`

export const num = (n, digits = 1) =>
  n === null || n === undefined ? '-' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: digits })

// "2026-03-04" -> "4 Mar"
export const shortDate = (iso) =>
  iso ? new Date(String(iso).slice(0, 10) + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '-'

// "2026-03-04" -> "4 Mar 2026"
export const fullDate = (iso) =>
  iso
    ? new Date(String(iso).slice(0, 10) + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
    : '-'

export const todayISO = () => {
  const d = new Date()
  const z = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`   // local date, not UTC
}

// "2 hours ago" for an ISO timestamp (the server sends UTC without a 'Z')
export const timeAgo = (iso) => {
  if (!iso) return ''
  const t = new Date(/Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z').getTime()
  const s = Math.max(0, Math.round((Date.now() - t) / 1000))
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  if (s < 86400 * 30) return `${Math.floor(s / 86400)} d ago`
  return fullDate(iso)
}
