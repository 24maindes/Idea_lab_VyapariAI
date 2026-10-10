import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCheck, RefreshCw, BellOff } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader.jsx'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'
import ErrorBox from '../components/ui/ErrorBox.jsx'
import { useToast } from '../components/ui/Toast.jsx'
import { listAlerts, markAlertRead, markAllRead, scanAlerts } from '../api/anomalies'
import { ALERTS_CHANGED } from '../hooks/useUnreadAlerts'
import { pct, rupee, timeAgo } from '../utils/format'

const SEVERITY_BORDER = { high: 'border-l-accent', medium: 'border-l-amber-400', low: 'border-l-ink/20' }
const METHOD_LABEL = { zscore: 'Z-score', isolation_forest: 'Isolation Forest', threshold: 'Threshold' }
const TYPE_LABEL = { price_anomaly: 'Price anomaly', low_stock: 'Low stock', overpaying: 'Overpaying' }

function Chips({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map(([key, label]) => (
        <button key={key} onClick={() => onChange(key)} aria-pressed={value === key}
          className={`rounded-full border px-3 py-1 text-[12px] font-medium transition-colors ${value === key ? 'border-primary bg-primary text-white' : 'border-[#D9DEDA] bg-white text-[#4B5B61] hover:bg-[#F1F2EF]'}`}>
          {label}
        </button>
      ))}
    </div>
  )
}

export default function Alerts() {
  const toast = useToast()
  const [filters, setFilters] = useState({ status: 'all', severity: 'all', type: 'all' })
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [scanning, setScanning] = useState(false)

  const setF = (k) => (v) => setFilters((f) => ({ ...f, [k]: v }))
  const notify = () => window.dispatchEvent(new Event(ALERTS_CHANGED))     // refresh the sidebar badge

  const load = () => {
    setLoading(true)
    setError('')
    listAlerts(filters).then(setAlerts).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [filters]) // eslint-disable-line react-hooks/exhaustive-deps

  const read = async (a) => {
    try { await markAlertRead(a.id); setAlerts((l) => l.map((x) => (x.id === a.id ? { ...x, isRead: true } : x))); notify() }
    catch (e) { toast.error(e.message) }
  }
  const readAll = async () => {
    try { const r = await markAllRead(); toast.success(`${r.updated} alert${r.updated === 1 ? '' : 's'} marked as read`); load(); notify() }
    catch (e) { toast.error(e.message) }
  }
  const scan = async () => {
    setScanning(true)
    try {
      const r = await scanAlerts()
      toast.success(r.newAlerts ? `Scan finished: ${r.newAlerts} new alert${r.newAlerts === 1 ? '' : 's'}` : 'Scan finished: nothing new')
      load(); notify()
    } catch (e) { toast.error(e.message) } finally { setScanning(false) }
  }

  return (
    <div>
      <PageHeader title="Alerts" subtitle="Unusual purchase prices, low stock and suppliers that overcharge."
        action={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={readAll}><CheckCheck className="h-4 w-4" />Mark all read</Button>
            <Button variant="primary" onClick={scan} disabled={scanning}><RefreshCw className={`h-4 w-4 ${scanning ? 'animate-spin' : ''}`} />{scanning ? 'Scanning...' : 'Scan now'}</Button>
          </div>
        } />

      <div className="mb-5 flex flex-wrap items-center gap-x-6 gap-y-3">
        <Chips value={filters.status} onChange={setF('status')} options={[['all', 'All'], ['unread', 'Unread']]} />
        <Chips value={filters.severity} onChange={setF('severity')} options={[['all', 'Any severity'], ['high', 'High'], ['medium', 'Medium'], ['low', 'Low']]} />
        <Chips value={filters.type} onChange={setF('type')} options={[['all', 'All types'], ['price_anomaly', 'Price anomaly'], ['low_stock', 'Low stock'], ['overpaying', 'Overpaying']]} />
      </div>

      {error && <ErrorBox message={error} onRetry={load} />}
      {loading ? (
        <div className="space-y-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      ) : alerts.length === 0 ? (
        <Card className="p-12 text-center">
          <BellOff className="mx-auto mb-3 text-[#9AA5A8]" size={28} />
          <p className="text-[14px] font-medium text-text">No alerts - your purchase prices look normal</p>
          <p className="mt-1 text-[12px] text-[#8A9599]">Click "Scan now" to check all your purchases again.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {alerts.map((a) => (
            <Card key={a.id} className={`border-l-4 p-4 ${SEVERITY_BORDER[a.severity] || SEVERITY_BORDER.low} ${a.isRead ? 'opacity-70' : ''}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[14px] font-semibold text-text">{a.productName || 'Product'}</span>
                    <span className="rounded-full bg-[#EAEEF0] px-2 py-0.5 text-[11px] text-[#4B5B61]">{TYPE_LABEL[a.type] || a.type}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${a.severity === 'high' ? 'bg-accent text-white' : a.severity === 'medium' ? 'bg-amber-100 text-amber-800' : 'bg-ink/10 text-ink/70'}`}>{a.severity}</span>
                    {!a.isRead && <span className="h-2 w-2 rounded-full bg-accent" title="Unread" />}
                  </div>
                  <p className="mt-1.5 text-[13px] text-[#4B5B61]">{a.message}</p>
                  {a.pricePaid != null && (
                    <p className="mt-2 text-[12px] text-[#6B7A7E]">
                      {a.supplierName && <>{a.supplierName} · </>}Paid <b className="text-text">{rupee(a.pricePaid)}</b>
                      {a.referencePrice != null && <> vs market <b className="text-text">{rupee(a.referencePrice)}</b> ({pct(a.deviationPct, 0)})</>}
                    </p>
                  )}
                  {a.methods.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {a.methods.map((m) => <span key={m} className="rounded-full bg-[#EAF2F1] px-2 py-0.5 text-[11px] text-secondary">{METHOD_LABEL[m] || m}</span>)}
                    </div>
                  )}
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  <span className="text-[12px] text-[#8A9599]">{timeAgo(a.createdAt)}</span>
                  <div className="flex gap-2">
                    {a.productId && <Link to={`/price-analysis?productId=${a.productId}`} className="rounded-[8px] border border-[#D9DEDA] px-2.5 py-1 text-[12px] font-medium text-secondary hover:bg-[#EEF3F3]">View price analysis</Link>}
                    {!a.isRead && <button onClick={() => read(a)} className="rounded-[8px] border border-[#D9DEDA] px-2.5 py-1 text-[12px] font-medium text-[#4B5B61] hover:bg-[#F1F2EF]">Mark as read</button>}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
