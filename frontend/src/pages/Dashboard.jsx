import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Package, ShoppingCart, Boxes, AlertTriangle, PlusCircle, Truck, Receipt, Upload, ChevronDown, Wallet, CheckCircle2, Circle } from 'lucide-react'
import { CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import Topbar from '../components/Topbar.jsx'
import StatCard from '../components/StatCard.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'
import ErrorBox from '../components/ui/ErrorBox.jsx'
import AskAiButton from '../components/AskAiButton.jsx'
import { useAppData } from '../context/AppDataContext.jsx'
import { apiFetch } from '../api/client'
import { num, rupee, shortDate, timeAgo } from '../utils/format'

const ACTION_STYLE = { 'Buy Now': 'bg-accent text-white', 'Buy Limited': 'bg-amber-100 text-amber-800', Wait: 'bg-secondary/15 text-secondary' }
const SEVERITY_DOT = { high: 'bg-accent', medium: 'bg-amber-400', low: 'bg-ink/30' }
const KIND_ICON = { product: PlusCircle, purchase: ShoppingCart, sale: Receipt, supplier: Truck, import: Upload }

function TrendTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const r = payload[0].payload
  return (
    <div className="rounded-[8px] border border-black/10 bg-card p-3 text-[12px] shadow-sm">
      <p className="font-medium text-ink">{shortDate(r.date)}</p>
      {r.market != null && <p className="text-ink/70">Market: {rupee(r.market)}</p>}
      {r.forecast != null && <p className="text-accent">Forecast: {rupee(r.forecast)}</p>}
      {r.bought != null && <p className="text-primary">You paid: {rupee(r.bought)}{r.supplier ? ` (${r.supplier})` : ''}</p>}
    </div>
  )
}

function Onboarding({ flags }) {
  const steps = [
    { done: flags.hasProducts, text: 'Add your products', to: '/products' },
    { done: flags.hasLinkedCommodities, text: 'Link a market commodity to a product (for fair-price checks and forecasts)', to: '/products' },
    { done: flags.hasSuppliers, text: 'Add your suppliers', to: '/suppliers' },
    { done: flags.hasPurchases, text: 'Record your purchases', to: '/purchases' },
    { done: flags.hasSales, text: 'Record your sales (so we can tell how much to buy)', to: '/sales' },
  ]
  return (
    <div className="mb-6 rounded-card border border-secondary/30 bg-secondary/5 p-5">
      <h2 className="text-[15px] font-semibold text-ink">Welcome! Let's set up your shop</h2>
      <p className="mb-3 text-[12px] text-ink/60">Do these steps once. The advice gets better with every purchase and sale you record.</p>
      <ul className="space-y-2">
        {steps.map((s) => (
          <li key={s.text} className="flex items-center gap-2 text-[13px]">
            {s.done ? <CheckCircle2 size={16} className="text-secondary" /> : <Circle size={16} className="text-ink/30" />}
            <Link to={s.to} className={s.done ? 'text-ink/50 line-through' : 'text-ink hover:text-secondary hover:underline'}>{s.text}</Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { products } = useAppData()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [productId, setProductId] = useState(null)
  const [trend, setTrend] = useState(null)
  const [trendError, setTrendError] = useState('')

  const load = () => {
    setError('')
    apiFetch('/api/dashboard/summary').then(setSummary).catch((e) => setError(e.message))
  }
  useEffect(load, [])

  const linked = useMemo(() => products.filter((p) => p.referenceCommodity), [products])
  useEffect(() => { if (productId === null && linked.length) setProductId(linked[0].id) }, [linked, productId])

  useEffect(() => {
    if (productId === null) return
    setTrend(null); setTrendError('')
    apiFetch(`/api/dashboard/price-trend?productId=${productId}&days=60`).then(setTrend).catch((e) => setTrendError(e.message))
  }, [productId])

  const chart = useMemo(() => {
    if (!trend) return []
    const rows = new Map()
    const row = (d) => { if (!rows.has(d)) rows.set(d, { date: d }); return rows.get(d) }
    trend.history.forEach((h) => { row(h.date).market = h.marketPrice })
    const last = trend.history[trend.history.length - 1]
    if (last && trend.forecast.length) row(last.date).forecast = last.marketPrice
    trend.forecast.forEach((f) => { row(f.date).forecast = f.price })
    trend.purchases.forEach((p) => { const r = row(p.date); r.bought = p.price; r.supplier = p.supplier })
    return [...rows.values()].sort((a, b) => a.date.localeCompare(b.date))
  }, [trend])

  if (error) return (<div><Topbar title="Dashboard" /><ErrorBox message={error} onRetry={load} /></div>)
  if (!summary) return (
    <div><Topbar title="Dashboard" />
      <div className="mb-6 grid grid-cols-4 gap-4">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-20" />)}</div>
      <div className="grid grid-cols-3 gap-4"><Skeleton className="col-span-2 h-72" /><Skeleton className="h-72" /></div>
    </div>
  )

  const o = summary.onboarding
  const incomplete = !(o.hasProducts && o.hasSuppliers && o.hasPurchases && o.hasSales)

  return (
    <div>
      <Topbar title="Dashboard" />
      {incomplete && <Onboarding flags={o} />}

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard icon={Package} label="Total Products" value={summary.totalProducts} tint="primary" />
        <StatCard icon={ShoppingCart} label="Purchases this month" value={`${summary.purchasesThisMonth.count} · ${rupee(summary.purchasesThisMonth.spend, 0)}`} tint="secondary" />
        <StatCard icon={Boxes} label="Stock value" value={rupee(summary.stock.value, 0)} tint="secondary" />
        <button onClick={() => navigate('/alerts')} className="text-left"><StatCard icon={AlertTriangle} label="Unread alerts" value={summary.unreadAlerts} tint="accent" /></button>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-card border border-black/5 bg-card p-4 shadow-sm lg:col-span-2">
          <div className="mb-1 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-[15px] font-semibold text-ink">Price Trend{trend ? ` - ${trend.productName}` : ''}</h2>
              <p className="mb-3 text-[12px] text-ink/50">Last 60 days: market price, 7-day forecast and what you paid{trend ? ` (₹/${trend.unit})` : ''}</p>
            </div>
            {linked.length > 0 && (
              <div className="relative">
                <select value={productId ?? ''} onChange={(e) => setProductId(Number(e.target.value))} aria-label="Product"
                  className="appearance-none rounded-[8px] border border-black/10 bg-card py-1.5 pl-3 pr-8 text-[13px] text-ink">
                  {linked.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <ChevronDown size={14} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-ink/40" />
              </div>
            )}
          </div>
          <div className="h-60">
            {linked.length === 0 ? (
              <div className="flex h-full items-center justify-center text-center text-[12px] text-ink/50">Link a market commodity to a product to see its price trend.</div>
            ) : trendError ? <ErrorBox message={trendError} /> : !trend ? <Skeleton className="h-full" /> : (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chart} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#24323814" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fontSize: 12, fill: '#24323899' }} axisLine={false} tickLine={false} minTickGap={40} />
                  <YAxis domain={['auto', 'auto']} tick={{ fontSize: 12, fill: '#24323899' }} axisLine={false} tickLine={false} tickFormatter={(v) => `₹${v}`} />
                  <Tooltip content={<TrendTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line dataKey="market" name="Market price" stroke="#0F4C5C" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line dataKey="forecast" name="Forecast" stroke="#E9785B" strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                  <Line dataKey="bought" name="You paid" stroke="#2A7F8E" strokeWidth={0} dot={{ r: 4, fill: '#2A7F8E' }} legendType="circle" isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="rounded-card border border-black/5 bg-card p-4 shadow-sm">
          <h2 className="mb-3 text-[15px] font-semibold text-ink">Recent Activity</h2>
          <ul className="space-y-3">
            {summary.recentActivity.map((a) => {
              const Icon = KIND_ICON[a.kind] || CheckCircle2
              return (
                <li key={a.id} className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] bg-secondary/10"><Icon size={15} className="text-secondary" /></div>
                  <div className="min-w-0"><p className="text-[13px] text-ink">{a.text}</p><p className="text-[11px] text-ink/40">{timeAgo(a.createdAt)}</p></div>
                </li>
              )
            })}
            {summary.recentActivity.length === 0 && <li className="text-[12px] text-ink/50">Nothing yet. Your actions will appear here.</li>}
          </ul>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-card border border-black/5 bg-card p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between"><h2 className="text-[15px] font-semibold text-ink">What to buy</h2><Link to="/recommendations" className="text-[12px] text-secondary hover:underline">See all</Link></div>
          {summary.topRecommendations.length === 0 ? (
            <p className="text-[12px] text-ink/50">{summary.totalProducts === 0 ? 'Add products to get buying advice.' : 'Add sales to get quantity advice.'}</p>
          ) : (
            <ul className="space-y-3">
              {summary.topRecommendations.map((r) => (
                <li key={r.productId} className="rounded-[8px] bg-bg p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[13px] font-semibold text-ink">{r.productName}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${ACTION_STYLE[r.action]}`}>{r.action}{r.quantity ? ` ${num(r.quantity, 1)} ${r.unit}` : ''}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[11px] text-ink/60">{r.reason}</p>
                  <div className="mt-1.5"><AskAiButton productId={r.productId} productName={r.productName} questionKey="recommendation" className="!px-2 !py-1 !text-[11px]" /></div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-card border border-black/5 bg-card p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between"><h2 className="text-[15px] font-semibold text-ink">Low stock</h2><Link to="/inventory" className="text-[12px] text-secondary hover:underline">Inventory</Link></div>
          {summary.lowStock.length === 0 ? <p className="text-[12px] text-ink/50">All products have enough stock.</p> : (
            <ul className="space-y-2">
              {summary.lowStock.map((p) => (
                <li key={p.id} className="flex items-center justify-between text-[13px]">
                  <span className="text-ink">{p.name}</span>
                  <span className="text-ink/60">{num(p.stock, 1)} / {num(p.reorderLevel, 0)} {p.unit}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-4 rounded-[8px] bg-bg p-3 text-[12px]">
            <p className="flex items-center gap-1.5 font-medium text-ink"><Wallet size={13} className="text-accent" />Fair price check</p>
            {o.hasPurchases ? (
              <p className="mt-1 text-ink/70">Overpaying on <b>{summary.fairPrice.overpayingProducts}</b> product(s). Possible saving in 90 days: <b>{rupee(summary.fairPrice.potentialSavings90d, 0)}</b>.</p>
            ) : <p className="mt-1 text-ink/60">Record purchases to see fair-price checks.</p>}
          </div>
        </div>

        <div className="rounded-card border border-black/5 bg-card p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between"><h2 className="text-[15px] font-semibold text-ink">Latest alerts</h2><Link to="/alerts" className="text-[12px] text-secondary hover:underline">See all</Link></div>
          {summary.latestAlerts.length === 0 ? <p className="text-[12px] text-ink/50">No alerts. Your purchase prices look normal.</p> : (
            <ul className="space-y-3">
              {summary.latestAlerts.map((a) => (
                <li key={a.id} className="flex items-start gap-2">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${SEVERITY_DOT[a.severity] || SEVERITY_DOT.low}`} />
                  <div><p className={`text-[12px] ${a.isRead ? 'text-ink/50' : 'text-ink'}`}>{a.message}</p><p className="text-[11px] text-ink/40">{timeAgo(a.createdAt)}</p></div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
