// "Compare" tab of the Suppliers page: which supplier gives the best value for ONE product?
import { useEffect, useState } from 'react'
import { ChevronDown, Star } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import Card from './ui/Card.jsx'
import Skeleton from './ui/Skeleton.jsx'
import ErrorBox from './ui/ErrorBox.jsx'
import { apiFetch } from '../api/client'
import { useAppData } from '../context/AppDataContext.jsx'
import { pct, rupee, shortDate } from '../utils/format'

const STABILITY = {
  Stable: 'bg-secondary/10 text-secondary',
  Moderate: 'bg-amber-100 text-amber-800',
  Volatile: 'bg-accent/10 text-accent',
  'Not enough data': 'bg-black/5 text-ink/50',
}

export default function SupplierComparison() {
  const { products } = useAppData()
  const [productId, setProductId] = useState(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [picked, setPicked] = useState(null)       // supplier whose price history is shown
  const [history, setHistory] = useState(null)

  useEffect(() => { if (productId === null && products.length) setProductId(products[0].id) }, [products, productId])

  const load = () => {
    if (productId === null) return
    setLoading(true); setError(''); setPicked(null); setHistory(null)
    apiFetch(`/api/suppliers/comparison?productId=${productId}`).then(setData).catch((e) => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [productId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!picked) return
    setHistory(null)
    apiFetch(`/api/suppliers/${picked}/prices?productId=${productId}`).then(setHistory).catch(() => setHistory(null))
  }, [picked, productId])

  const rows = data?.suppliers || []
  const lineData = (() => {
    if (!history) return []
    const m = new Map()
    history.reference.forEach((r) => m.set(r.date, { date: r.date, market: r.price }))
    history.prices.forEach((p) => { const r = m.get(p.date) || { date: p.date }; r.paid = p.price; m.set(p.date, r) })
    return [...m.values()].sort((a, b) => a.date.localeCompare(b.date))
  })()

  if (products.length === 0) return <Card className="p-10 text-center text-sm text-[#8A9599]">Add products and record purchases to compare suppliers.</Card>

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <span className="text-[13px] text-[#6B7A7E]">Product</span>
        <div className="relative">
          <select value={productId ?? ''} onChange={(e) => setProductId(Number(e.target.value))} className="appearance-none rounded-[8px] border border-[#D9DEDA] bg-white py-2 pl-3 pr-9 text-sm text-text focus:border-secondary focus:outline-none">
            {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <ChevronDown size={14} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink/40" />
        </div>
        <span className="text-[12px] text-[#8A9599]">based on purchases of the last 180 days</span>
      </div>

      {error && <ErrorBox message={error} onRetry={load} />}
      {loading || !data ? <Skeleton className="h-64" /> : rows.length === 0 ? (
        <Card className="p-10 text-center text-sm text-[#8A9599]">No purchases of {data.productName} in the last 180 days, so there is nothing to compare yet.</Card>
      ) : (
        <>
          <Card className="mb-5 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[#E7E9E4] bg-[#FAFAF8] text-[12px] uppercase tracking-wide text-[#7C8A8E]">
                    {['Supplier', 'Avg price', 'Min - Max', 'Latest', 'Price stability', 'vs market', 'Orders'].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((s) => (
                    <tr key={s.supplierId} onClick={() => setPicked(s.supplierId)} className={`cursor-pointer border-b border-[#EFF1EC] last:border-0 hover:bg-[#FAFBF9] ${picked === s.supplierId ? 'bg-secondary/5' : ''}`}>
                      <td className="px-4 py-3 font-medium text-text">
                        {s.supplierName}
                        {s.bestValue && <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-[11px] font-medium text-white"><Star size={10} />Best value</span>}
                      </td>
                      <td className="px-4 py-3">{rupee(s.avgPrice)}/{data.unit}</td>
                      <td className="px-4 py-3 text-[#4B5B61]">{rupee(s.minPrice)} - {rupee(s.maxPrice)}</td>
                      <td className="px-4 py-3 text-[#4B5B61]">{rupee(s.latestPrice)}</td>
                      <td className="px-4 py-3"><span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STABILITY[s.stability]}`}>{s.stability}</span>{s.coefficientOfVariationPct != null && <span className="ml-1 text-[11px] text-[#8A9599]">({s.coefficientOfVariationPct}%)</span>}</td>
                      <td className={`px-4 py-3 font-medium ${s.avgVarianceVsMarketPct > 3 ? 'text-accent' : 'text-text'}`}>{pct(s.avgVarianceVsMarketPct)}</td>
                      <td className="px-4 py-3 text-[#4B5B61]">{s.purchaseCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="border-t border-[#E7E9E4] px-4 py-2 text-[11px] text-[#8A9599]">Best value = lowest average price among suppliers with at least 3 orders and no volatile pricing. Click a row to see that supplier's prices over time.</p>
          </Card>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <Card className="p-4">
              <h3 className="mb-2 text-[14px] font-semibold text-text">Average price by supplier</h3>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={rows} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#24323814" vertical={false} />
                    <XAxis dataKey="supplierName" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} domain={[0, 'auto']} tickFormatter={(v) => `₹${v}`} />
                    <Tooltip formatter={(v) => [rupee(v), 'Average price']} />
                    {data.marketAvgPrice != null && <ReferenceLine y={data.marketAvgPrice} stroke="#E9785B" strokeDasharray="4 3" label={{ value: `Market ${rupee(data.marketAvgPrice)}`, fontSize: 11, fill: '#E9785B', position: 'insideTopRight' }} />}
                    <Bar dataKey="avgPrice" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                      {rows.map((s) => <Cell key={s.supplierId} fill={s.bestValue ? '#2A7F8E' : '#0F4C5C99'} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card className="p-4">
              <h3 className="mb-2 text-[14px] font-semibold text-text">{picked ? `${rows.find((r) => r.supplierId === picked)?.supplierName}: price over time` : 'Price over time'}</h3>
              <div className="h-56">
                {!picked ? <div className="flex h-full items-center justify-center text-[12px] text-[#8A9599]">Click a supplier in the table.</div>
                  : !history ? <Skeleton className="h-full" /> : (
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={lineData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#24323814" vertical={false} />
                        <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={40} />
                        <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} domain={['auto', 'auto']} tickFormatter={(v) => `₹${v}`} />
                        <Tooltip formatter={(v, n) => [rupee(v), n]} labelFormatter={shortDate} />
                        <Legend wrapperStyle={{ fontSize: 12 }} />
                        <Line dataKey="market" name="Market price" stroke="#243238" strokeOpacity={0.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} connectNulls />
                        <Line dataKey="paid" name="You paid" stroke="#E9785B" strokeWidth={0} dot={{ r: 4, fill: '#E9785B' }} legendType="circle" isAnimationActive={false} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  )}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
