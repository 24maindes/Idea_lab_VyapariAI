// Price Analysis: "Am I paying a fair price compared with the market?"
// Data comes from the backend (/api/analysis/fair-price). Loading, error, empty and
// "no market data" states are all handled.
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Topbar from '../components/Topbar.jsx'
import { getFairPriceDetail, getFairPriceSummary } from '../api/analysis.js'
import AskAiButton from '../components/AskAiButton.jsx'

// ---------------------------------------------------------------- helpers
const rupee = (n, digits = 2) =>
  n === null || n === undefined
    ? '-'
    : '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: digits })

const pct = (n) => (n === null || n === undefined ? '-' : `${n > 0 ? '+' : ''}${n.toFixed(1)}%`)

const shortDate = (iso) =>
  new Date(iso + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

// Verdict colours use only the brand colours: secondary (good) and accent (bad).
const VERDICT_STYLE = {
  'Great deal': { badge: 'bg-secondary/10 text-secondary', banner: 'bg-secondary/5 border-secondary/20 text-secondary' },
  Fair: { badge: 'bg-secondary/10 text-secondary', banner: 'bg-secondary/5 border-secondary/20 text-secondary' },
  'Slightly high': { badge: 'bg-accent/10 text-accent', banner: 'bg-accent/5 border-accent/20 text-accent' },
  Overpaying: { badge: 'bg-accent text-white', banner: 'bg-accent/10 border-accent/40 text-accent' },
}

const VERDICT_TEXT = {
  'Great deal': 'Great deal - you paid clearly less than the market price.',
  Fair: 'Fair price - you paid about the market price.',
  'Slightly high': 'Slightly high - you paid a little more than the market price.',
  Overpaying: 'Overpaying - you paid much more than the market price. Compare suppliers before the next order.',
}

// one colour per supplier (brand colours first)
const SUPPLIER_COLORS = ['#0F4C5C', '#E9785B', '#2A7F8E', '#C9A227', '#7C6FB0', '#6B7280']

// ---------------------------------------------------------------- small pieces
function VerdictBadge({ verdict, hasMarketData = true }) {
  if (!hasMarketData || !verdict) {
    return <span className="rounded-full bg-black/5 px-2 py-0.5 text-[11px] font-medium text-ink/50">No market data</span>
  }
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${VERDICT_STYLE[verdict].badge}`}>{verdict}</span>
}

function InfoCard({ label, value, hint, tone = 'text-ink' }) {
  return (
    <div className="bg-card border border-black/5 rounded-card shadow-sm p-4">
      <p className="text-[12px] text-ink/60 mb-1">{label}</p>
      <p className={`text-[20px] font-semibold ${tone}`}>{value}</p>
      {hint && <p className="mt-1 text-[11px] text-ink/50">{hint}</p>}
    </div>
  )
}

function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-[8px] bg-black/5 ${className}`} />
}

function ErrorBox({ message, onRetry }) {
  return (
    <div className="mb-5 flex items-start gap-3 rounded-card border border-accent/30 bg-accent/5 p-4 text-[13px] text-ink">
      <AlertCircle size={18} className="mt-0.5 shrink-0 text-accent" />
      <div className="flex-1">
        <p className="font-medium">Something went wrong</p>
        <p className="text-[12px] text-ink/70">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1 rounded-[8px] border border-black/10 bg-card px-3 py-1.5 text-[12px] font-medium"
        >
          <RefreshCw size={12} /> Retry
        </button>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- chart
// ONE row per date: the market price, plus on purchase dates one price per supplier.
function buildChartData(detail) {
  const rows = new Map()
  const row = (date) => {
    if (!rows.has(date)) rows.set(date, { date })
    return rows.get(date)
  }
  detail.series.forEach((s) => {
    row(s.date).reference = s.referencePrice
  })
  const suppliers = [...new Set(detail.points.map((p) => p.supplier))]
  detail.points.forEach((p) => {
    const r = row(p.date)
    r[`price_${p.supplier}`] = p.price
    r.buys = [...(r.buys || []), p] // used by the tooltip
  })
  const data = [...rows.values()].sort((a, b) => a.date.localeCompare(b.date))
  return { data, suppliers }
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const row = payload[0].payload
  return (
    <div className="rounded-[8px] border border-black/10 bg-card p-3 text-[12px] shadow-sm">
      <p className="font-medium text-ink">{shortDate(row.date)}</p>
      {row.reference !== undefined && <p className="text-ink/60">Market price: {rupee(row.reference)}</p>}
      {(row.buys || []).map((b, i) => (
        <div key={i} className="mt-1.5 border-t border-black/5 pt-1.5">
          <p className="font-medium text-ink">{b.supplier}</p>
          <p className="text-ink/70">
            Paid {rupee(b.price)} ({b.quantity} units)
          </p>
          <p className={b.variancePct > 3 ? 'text-accent' : 'text-secondary'}>Variance {pct(b.variancePct)}</p>
        </div>
      ))}
    </div>
  )
}

function PriceChart({ detail }) {
  const { data, suppliers } = useMemo(() => buildChartData(detail), [detail])
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#24323814" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            tick={{ fontSize: 12, fill: '#24323899' }}
            axisLine={false}
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#24323899' }}
            axisLine={false}
            tickLine={false}
            domain={['auto', 'auto']}
            tickFormatter={(v) => `₹${v}`}
          />
          <Tooltip content={<ChartTooltip />} />
          <Legend wrapperStyle={{ fontSize: 13 }} />
          {/* market price line */}
          <Line
            type="monotone"
            dataKey="reference"
            name="Market price"
            stroke="#243238"
            strokeOpacity={0.55}
            strokeDasharray="4 3"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
          {/* your purchases: one set of dots per supplier (line width 0, only the dots show) */}
          {suppliers.map((name, i) => (
            <Line
              key={name}
              dataKey={`price_${name}`}
              name={name}
              stroke={SUPPLIER_COLORS[i % SUPPLIER_COLORS.length]}
              strokeWidth={0}
              legendType="circle"
              connectNulls={false}
              dot={{ r: 5, fill: SUPPLIER_COLORS[i % SUPPLIER_COLORS.length], strokeWidth: 0 }}
              activeDot={{ r: 7 }}
              isAnimationActive={false}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------- page
export default function PriceAnalysis() {
  const [searchParams] = useSearchParams()
  const wanted = Number(searchParams.get('productId')) || null     // ?productId= preselects the product
  const [rows, setRows] = useState([]) // summary of all products
  const [loadingRows, setLoadingRows] = useState(true)
  const [rowsError, setRowsError] = useState('')

  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detailError, setDetailError] = useState('')

  // 1) summary list (once)
  const loadRows = () => {
    setLoadingRows(true)
    setRowsError('')
    getFairPriceSummary()
      .then((data) => {
        setRows(data)
        // start with the first product that has market data
        setSelectedId((cur) => cur ?? (data.find((r) => r.productId === wanted) || data.find((r) => r.hasMarketData) || data[0])?.productId ?? null)
      })
      .catch((e) => setRowsError(e.message))
      .finally(() => setLoadingRows(false))
  }
  useEffect(loadRows, [])

  // 2) detail of the selected product
  const loadDetail = () => {
    if (selectedId === null) return
    setLoadingDetail(true)
    setDetailError('')
    getFairPriceDetail(selectedId)
      .then(setDetail)
      .catch((e) => setDetailError(e.message))
      .finally(() => setLoadingDetail(false))
  }
  useEffect(loadDetail, [selectedId])

  // ---------- page-level states
  if (loadingRows) {
    return (
      <div>
        <Topbar title="Price Analysis" />
        <div className="grid grid-cols-4 gap-4 mb-5">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-72" />
      </div>
    )
  }
  if (rowsError) {
    return (
      <div>
        <Topbar title="Price Analysis" />
        <ErrorBox message={rowsError} onRetry={loadRows} />
      </div>
    )
  }
  if (rows.length === 0) {
    return (
      <div>
        <Topbar title="Price Analysis" />
        <div className="bg-card border border-black/5 rounded-card shadow-sm p-10 text-center">
          <p className="text-[14px] font-medium text-ink">No products yet</p>
          <p className="mt-1 text-[12px] text-ink/60">
            Add products and record purchases to see how your prices compare with the market.
          </p>
        </div>
      </div>
    )
  }

  const selectedRow = rows.find((r) => r.productId === selectedId)
  const hasMarket = detail ? detail.hasMarketData : selectedRow?.hasMarketData
  const verdict = detail?.verdict
  const unit = detail?.unit || selectedRow?.unit || 'unit'
  const isHigher = detail?.variancePct > 3

  return (
    <div>
      <Topbar title="Price Analysis" />

      <div className="flex items-center justify-between mb-5">
        <p className="text-[13px] text-ink/55">
          Compare what you paid your suppliers with the market price (₹ per {unit}).
        </p>

        <div className="flex items-center gap-2">
          <div className="relative">
            <select
              value={selectedId ?? ''}
              onChange={(e) => setSelectedId(Number(e.target.value))}
              className="appearance-none bg-card border border-black/10 rounded-[8px] pl-3 pr-9 py-2 text-[14px] text-ink shadow-sm focus:outline-none focus:ring-2 focus:ring-secondary/40"
            >
              {rows.map((r) => (
                <option key={r.productId} value={r.productId}>
                  {r.productName}
                </option>
              ))}
            </select>
            <ChevronDown size={15} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/40 pointer-events-none" />
          </div>

          {selectedRow && <AskAiButton productId={selectedId} productName={selectedRow.productName} questionKey="price" label="Explain with AI" />}
        </div>
      </div>

      {detailError && <ErrorBox message={detailError} onRetry={loadDetail} />}

      {/* 4 stat cards */}
      <div className="grid grid-cols-4 gap-4 mb-5">
        {loadingDetail || !detail ? (
          [1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)
        ) : (
          <>
            <InfoCard
              label="Your Last Price"
              value={detail.lastPurchasePrice === null ? '-' : `${rupee(detail.lastPurchasePrice)}/${unit}`}
              hint={detail.lastPurchaseDate ? `on ${shortDate(detail.lastPurchaseDate)}` : 'No purchases yet'}
            />
            <InfoCard
              label="Reference Market Price"
              value={hasMarket && detail.referencePrice !== null ? `${rupee(detail.referencePrice)}/${unit}` : '-'}
              hint={hasMarket ? 'same date as your last purchase' : 'No market data linked'}
            />
            <InfoCard
              label="Difference"
              value={pct(detail.variancePct)}
              tone={detail.variancePct === null ? 'text-ink' : isHigher ? 'text-accent' : 'text-secondary'}
              hint="vs market price"
            />
            <InfoCard
              label="Potential Savings"
              value={hasMarket ? rupee(detail.potentialSavings, 0) : '-'}
              hint={hasMarket ? `last ${detail.days} days · ${rupee(detail.overspend90Days, 0)} in last 90` : ''}
            />
          </>
        )}
      </div>

      {/* verdict banner */}
      {detail && !loadingDetail && hasMarket && verdict && (
        <div className={`flex items-center gap-2.5 rounded-card border px-4 py-3 mb-5 text-[13px] ${VERDICT_STYLE[verdict].banner}`}>
          {verdict === 'Great deal' || verdict === 'Fair' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
          <span className="font-medium">{VERDICT_TEXT[verdict]}</span>
        </div>
      )}

      {/* chart */}
      <div className="bg-card border border-black/5 rounded-card shadow-sm p-4 mb-5">
        <h2 className="text-[15px] font-semibold text-ink mb-1">Price Comparison</h2>
        <p className="text-[12px] text-ink/50 mb-3">
          Your purchase prices (dots, by supplier) vs the market price (dashed line)
        </p>
        {loadingDetail || !detail ? (
          <Skeleton className="h-72" />
        ) : !hasMarket ? (
          <div className="flex h-72 flex-col items-center justify-center text-center">
            <p className="text-[14px] font-medium text-ink">No market data linked</p>
            <p className="max-w-xs text-[12px] text-ink/60">
              This product is not linked to a market commodity, so it cannot be compared. Your own purchase prices are
              still saved.
            </p>
          </div>
        ) : detail.points.length === 0 ? (
          <div className="flex h-72 items-center justify-center text-[12px] text-ink/60">
            No purchases in the last {detail.days} days.
          </div>
        ) : (
          <PriceChart detail={detail} />
        )}

        {/* supplier comparison */}
        {detail && !loadingDetail && hasMarket && detail.supplierBreakdown.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {detail.supplierBreakdown.map((s) => (
              <div key={s.supplierId} className="rounded-[8px] border border-black/5 bg-bg px-3 py-1.5 text-[12px]">
                <span className="font-medium text-ink">{s.supplier}</span>
                <span className={`ml-2 font-medium ${s.avgVariancePct > 3 ? 'text-accent' : 'text-secondary'}`}>
                  {pct(s.avgVariancePct)}
                </span>
                <span className="ml-1 text-ink/50">
                  avg · {s.purchases} orders
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* all products (click a row to select it) */}
      <div className="bg-card border border-black/5 rounded-card shadow-sm overflow-hidden">
        <div className="border-b border-black/5 px-4 py-3 text-[15px] font-semibold text-ink">All Products</div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead className="bg-bg text-[12px] text-ink/60">
              <tr>
                <th className="px-4 py-2 font-medium">Product</th>
                <th className="px-4 py-2 font-medium">Last price</th>
                <th className="px-4 py-2 font-medium">Market price</th>
                <th className="px-4 py-2 font-medium">Variance</th>
                <th className="px-4 py-2 font-medium">Verdict</th>
                <th className="px-4 py-2 text-right font-medium">Potential savings</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.productId}
                  onClick={() => setSelectedId(r.productId)}
                  className={`cursor-pointer border-t border-black/5 hover:bg-bg ${r.productId === selectedId ? 'bg-secondary/5' : ''}`}
                >
                  <td className="px-4 py-2.5 font-medium text-ink">
                    {r.productName}
                    <span className="ml-1 text-ink/40">/{r.unit}</span>
                  </td>
                  <td className="px-4 py-2.5">{rupee(r.lastPurchasePrice)}</td>
                  <td className="px-4 py-2.5">{r.hasMarketData ? rupee(r.referencePrice) : '-'}</td>
                  <td className={`px-4 py-2.5 font-medium ${r.variancePct > 3 ? 'text-accent' : 'text-ink'}`}>
                    {pct(r.variancePct)}
                  </td>
                  <td className="px-4 py-2.5">
                    <VerdictBadge verdict={r.verdict} hasMarketData={r.hasMarketData} />
                  </td>
                  <td className="px-4 py-2.5 text-right">{r.hasMarketData ? rupee(r.potentialSavings, 0) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
