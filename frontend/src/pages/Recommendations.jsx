import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, ArrowDownRight, ShoppingCart, Truck } from 'lucide-react'
import Topbar from '../components/Topbar.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'
import ErrorBox from '../components/ui/ErrorBox.jsx'
import AskAiButton from '../components/AskAiButton.jsx'
import { getPurchaseRecommendations, getSellingPrices } from '../api/recommendations'
import { num, pct, rupee } from '../utils/format'

const ACTION_STYLE = {
  'Buy Now': 'bg-accent text-white',
  'Buy Limited': 'bg-amber-100 text-amber-800',
  Wait: 'bg-secondary/15 text-secondary',
}
const VERDICT_STYLE = {
  'Great deal': 'bg-secondary/10 text-secondary', Fair: 'bg-secondary/10 text-secondary',
  'Slightly high': 'bg-amber-100 text-amber-800', Overpaying: 'bg-accent text-white',
}
const CONFIDENCE_STYLE = { High: 'bg-secondary/10 text-secondary', Medium: 'bg-amber-100 text-amber-800', Low: 'bg-black/5 text-ink/60' }

function Pill({ className, children }) {
  return <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${className}`}>{children}</span>
}

// ---------------------------------------------------------------- tab 1: what to buy
function BuyTab() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = () => {
    setLoading(true); setError('')
    getPurchaseRecommendations().then(setItems).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  if (error) return <ErrorBox message={error} onRetry={load} />
  if (loading) return <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-56" />)}</div>
  if (items.length === 0) {
    return <div className="rounded-card border border-black/5 bg-card p-10 text-center shadow-sm"><p className="text-[14px] font-medium text-ink">No products yet</p><p className="mt-1 text-[12px] text-ink/60">Add products and record purchases and sales to get recommendations.</p></div>
  }
  const count = (a) => items.filter((i) => i.action === a).length

  return (
    <>
      <div className="mb-4 flex flex-wrap gap-2">
        {['Buy Now', 'Buy Limited', 'Wait'].map((a) => <Pill key={a} className={`!px-3 !py-1 !text-[12px] ${ACTION_STYLE[a]}`}>{count(a)} {a}</Pill>)}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {items.map((r) => {
          const ArrowIcon = r.direction === 'Rising' ? ArrowUpRight : r.direction === 'Falling' ? ArrowDownRight : ArrowRight
          return (
            <div key={r.productId} className="rounded-card border border-black/5 bg-card p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-[15px] font-semibold text-ink">{r.productName} <span className="text-[12px] font-normal text-ink/50">/{r.unit}</span></h3>
                  <p className="mt-0.5 text-[20px] font-semibold text-primary">
                    {r.action === 'Wait' ? `Check again in ${r.checkAgainInDays ?? 5} days` : `Buy ${num(r.quantity, 1)} ${r.unit}`}
                  </p>
                </div>
                <Pill className={`!px-3 !py-1 !text-[13px] ${ACTION_STYLE[r.action]}`}>{r.action}</Pill>
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2 text-[12px]">
                <div className="rounded-[8px] bg-bg p-2"><p className="text-ink/55">Stock left</p><p className="text-[14px] font-semibold text-ink">{r.daysLeft != null ? `${num(r.daysLeft, 1)} days` : '-'}</p><p className="text-ink/50">{num(r.currentStock, 1)} {r.unit}</p></div>
                <div className="rounded-[8px] bg-bg p-2"><p className="text-ink/55">Price now → 7 days</p>
                  <p className="flex items-center gap-1 text-[14px] font-semibold text-ink">{rupee(r.currentMarketPrice)} <ArrowIcon size={14} className={r.direction === 'Rising' ? 'text-accent' : r.direction === 'Falling' ? 'text-secondary' : 'text-ink/40'} /> {rupee(r.forecastPrice7d)}</p>
                  <p className="text-ink/50">{r.changePct != null ? pct(r.changePct) : 'no forecast'}</p></div>
                <div className="rounded-[8px] bg-bg p-2"><p className="text-ink/55">Cheapest supplier</p><p className="flex items-center gap-1 text-[13px] font-semibold text-ink"><Truck size={12} />{r.cheapestSupplier?.name || '-'}</p><p className="text-ink/50">{r.cheapestSupplier ? `avg ${rupee(r.cheapestSupplier.avgPrice)}` : ''}</p></div>
              </div>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {r.fairPriceVerdict && <Pill className={VERDICT_STYLE[r.fairPriceVerdict]}>{r.fairPriceVerdict}</Pill>}
                <Pill className={CONFIDENCE_STYLE[r.confidence]}>{r.confidence} confidence</Pill>
                {r.priceAnomaly && <Pill className="bg-accent/10 text-accent">Unusual last price</Pill>}
              </div>

              <ul className="mt-3 list-disc space-y-1 pl-4 text-[12px] text-ink/75">{r.reasons.map((t, i) => <li key={i}>{t}</li>)}</ul>
              {r.dataQuality !== 'Good' && <p className="mt-2 text-[11px] text-amber-700">Note: {r.dataQuality}</p>}

              <div className="mt-4 flex gap-2">
                <button onClick={() => navigate(`/purchases?productId=${r.productId}`)} className="flex items-center gap-1.5 rounded-[8px] bg-primary px-3 py-1.5 text-[13px] font-medium text-white hover:bg-[#0c3e4a]"><ShoppingCart size={14} />Record purchase</button>
                <AskAiButton productId={r.productId} productName={r.productName} questionKey="recommendation" />
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}

// ---------------------------------------------------------------- tab 2: what to sell at
function RangeBar({ r }) {
  if (r.rangeLow == null || r.rangeHigh == null) return <span className="text-ink/40">-</span>
  const lo = Math.min(r.rangeLow, r.currentPrice ?? r.rangeLow, r.marketPrice ?? r.rangeLow) * 0.97
  const hi = Math.max(r.rangeHigh, r.currentPrice ?? r.rangeHigh, r.marketPrice ?? r.rangeHigh) * 1.03
  const at = (v) => `${((v - lo) / (hi - lo)) * 100}%`
  return (
    <div className="w-44">
      <div className="relative h-2 rounded-full bg-black/10">
        <div className="absolute h-2 rounded-full bg-secondary/60" style={{ left: at(r.rangeLow), width: `calc(${at(r.rangeHigh)} - ${at(r.rangeLow)})` }} />
        <div className="absolute -top-1 h-4 w-1 rounded bg-primary" style={{ left: at(r.recommended) }} title={`Recommended ${rupee(r.recommended)}`} />
        {r.currentPrice != null && <div className="absolute -top-0.5 h-3 w-3 -translate-x-1/2 rounded-full border-2 border-white bg-accent" style={{ left: at(r.currentPrice) }} title={`Your price ${rupee(r.currentPrice)}`} />}
      </div>
      <p className="mt-1 text-[11px] text-ink/60">{rupee(r.rangeLow)} - {rupee(r.rangeHigh)}</p>
    </div>
  )
}

function SellTab() {
  const [margin, setMargin] = useState(null)        // null = the shop's own target margin
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const first = useRef(true)

  const load = (m) => {
    setLoading(true); setError('')
    getSellingPrices(m).then((r) => { setRows(r); if (m === null && r.length) setMargin(r[0].targetMarginPct) }).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(() => {
    if (first.current) { first.current = false; load(null); return undefined }
    const t = window.setTimeout(() => load(margin), 350)            // debounce the slider
    return () => window.clearTimeout(t)
  }, [margin]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-4 rounded-card border border-black/5 bg-card p-4 shadow-sm">
        <label htmlFor="margin" className="text-[13px] font-medium text-ink">Target margin</label>
        <input id="margin" type="range" min="5" max="40" step="1" value={margin ?? 15} onChange={(e) => setMargin(Number(e.target.value))} className="w-64 accent-[#0F4C5C]" />
        <span className="w-12 text-[14px] font-semibold text-primary">{margin ?? 15}%</span>
        <span className="text-[12px] text-ink/50">The recommended price follows the market but stays between your minimum margin and this target.</span>
      </div>
      {error && <ErrorBox message={error} onRetry={() => load(margin)} />}
      {loading && rows.length === 0 ? <Skeleton className="h-64" /> : rows.length === 0 ? (
        <div className="rounded-card border border-black/5 bg-card p-10 text-center shadow-sm"><p className="text-[14px] font-medium text-ink">No products yet</p></div>
      ) : (
        <div className={`overflow-x-auto rounded-card border border-black/5 bg-card shadow-sm ${loading ? 'opacity-70' : ''}`}>
          <table className="w-full text-left text-[13px]">
            <thead className="bg-bg text-[11px] uppercase tracking-wide text-ink/55">
              <tr>{['Product', 'Your cost', 'Market price', 'Your price', 'Recommended range', 'Margin', 'Warnings'].map((h) => <th key={h} className="px-4 py-2.5 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.productId} className="border-t border-black/5 align-top">
                  <td className="px-4 py-3 font-medium text-ink">{r.productName}<span className="ml-1 text-ink/40">/{r.unit}</span></td>
                  <td className="px-4 py-3">{rupee(r.costBasis)}</td>
                  <td className="px-4 py-3">{rupee(r.marketPrice)}</td>
                  <td className="px-4 py-3">{rupee(r.currentPrice)}</td>
                  <td className="px-4 py-3"><p className="mb-1 font-semibold text-primary">{rupee(r.recommended)}</p><RangeBar r={r} /></td>
                  <td className={`px-4 py-3 font-medium ${r.expectedMarginPct != null && r.expectedMarginPct < 5 ? 'text-accent' : 'text-ink'}`}>{r.expectedMarginPct != null ? `${r.expectedMarginPct}%` : '-'}</td>
                  <td className="px-4 py-3">{r.warnings.map((w, i) => <p key={i} className={`text-[11px] ${/below your cost|below the market|skipping/i.test(w) ? 'text-accent' : 'text-amber-700'}`}>{w}</p>)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-2 text-[11px] text-ink/50">In the bar: green band = recommended range, dark tick = recommended price, red dot = your current price.</p>
    </>
  )
}

export default function Recommendations() {
  const [tab, setTab] = useState('buy')
  return (
    <div>
      <Topbar title="Recommendations" />
      <div className="mb-5 inline-flex rounded-[8px] border border-black/10 bg-card p-0.5">
        {[['buy', 'What to buy'], ['sell', 'What to sell at']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} aria-pressed={tab === k} className={`rounded-[6px] px-4 py-1.5 text-[13px] font-medium ${tab === k ? 'bg-primary text-white' : 'text-ink/70 hover:bg-black/5'}`}>{l}</button>
        ))}
      </div>
      {tab === 'buy' ? <BuyTab /> : <SellTab />}
    </div>
  )
}
