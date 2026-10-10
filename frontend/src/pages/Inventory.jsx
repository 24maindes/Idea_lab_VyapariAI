import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Boxes, AlertTriangle, PackageX, Wallet, ShoppingCart } from 'lucide-react'
import { useAppData } from '../context/AppDataContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Card from '../components/ui/Card.jsx'
import SearchInput from '../components/ui/SearchInput.jsx'
import Badge from '../components/ui/Badge.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'
import ErrorBox from '../components/ui/ErrorBox.jsx'
import StatCard from '../components/StatCard.jsx'
import { fullDate, num, rupee } from '../utils/format'

// colour of "days of cover": red below the supplier lead time, amber below 7 days, otherwise neutral
function coverClass(days, leadTime) {
  if (days === null || days === undefined) return 'text-[#8A9599]'
  if (days < leadTime) return 'font-semibold text-accent'
  if (days < 7) return 'font-medium text-amber-600'
  return 'text-[#4B5B61]'
}

export default function Inventory() {
  const { inventory, inventoryLoading, inventoryError, refreshInventory } = useAppData()
  const { shop } = useAuth()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')

  const categories = useMemo(() => ['All', ...new Set(inventory.map((i) => i.category).filter(Boolean))], [inventory])
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return inventory.filter((i) => (!q || i.name.toLowerCase().includes(q)) && (category === 'All' || i.category === category))
  }, [inventory, query, category])

  const stats = useMemo(() => ({
    products: inventory.length,
    low: inventory.filter((i) => i.status === 'Low Stock').length,
    out: inventory.filter((i) => i.status === 'Out of Stock').length,
    value: inventory.reduce((s, i) => s + (i.stockValue || 0), 0),
  }), [inventory])

  const leadTime = shop?.leadTimeDays ?? 3

  return (
    <div>
      <PageHeader title="Inventory" subtitle="Current stock levels across all products." />

      <div className="mb-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard icon={Boxes} label="Products" value={stats.products} tint="primary" />
        <StatCard icon={AlertTriangle} label="Low stock" value={stats.low} tint="accent" />
        <StatCard icon={PackageX} label="Out of stock" value={stats.out} tint="accent" />
        <StatCard icon={Wallet} label="Total stock value" value={rupee(stats.value, 0)} tint="secondary" />
      </div>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <SearchInput value={query} onChange={setQuery} placeholder="Search products..." />
          <select value={category} onChange={(e) => setCategory(e.target.value)}
            className="rounded-[8px] border border-[#D9DEDA] bg-white px-3 py-2 text-sm text-text focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary/20">
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <p className="text-[13px] text-[#6B7A7E]">{filtered.length} of {inventory.length} products</p>
      </div>

      {inventoryError && <ErrorBox message={inventoryError} onRetry={refreshInventory} />}

      <Card className="overflow-hidden">
        {inventoryLoading && inventory.length === 0 ? (
          <div className="space-y-2 p-4">{[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-11" />)}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[#E7E9E4] bg-[#FAFAF8] text-[12px] uppercase tracking-wide text-[#7C8A8E]">
                  <th className="px-5 py-3 font-medium">Product</th>
                  <th className="px-5 py-3 font-medium">Stock</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Avg sales / day</th>
                  <th className="px-5 py-3 font-medium">Days of cover</th>
                  <th className="px-5 py-3 font-medium">Last purchase</th>
                  <th className="px-5 py-3 font-medium">Stock value</th>
                  <th className="px-5 py-3 font-medium text-right"> </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const needsStock = item.status !== 'In Stock'
                  return (
                    <tr key={item.id} className={`border-b border-[#EFF1EC] last:border-0 hover:bg-[#FAFBF9] ${needsStock ? 'bg-accent/[0.04]' : ''}`}>
                      <td className="px-5 py-3.5">
                        <p className="font-medium text-text">{item.name}</p>
                        <p className="text-[12px] text-[#8A9599]">{item.category || '-'} · {item.unit}</p>
                      </td>
                      <td className="px-5 py-3.5 text-[#4B5B61]">{num(item.currentStock, 2)} <span className="text-[12px] text-[#8A9599]">/ reorder {num(item.reorderLevel, 0)}</span></td>
                      <td className="px-5 py-3.5"><Badge tone={item.status}>{item.status}</Badge></td>
                      <td className="px-5 py-3.5 text-[#4B5B61]">{item.avgDailySales === null ? '-' : num(item.avgDailySales, 1)}</td>
                      <td className={`px-5 py-3.5 ${coverClass(item.daysOfCover, leadTime)}`}>{item.daysOfCover === null ? '-' : `${num(item.daysOfCover, 1)} days`}</td>
                      <td className="px-5 py-3.5 text-[#4B5B61]">
                        {item.lastPurchaseDate ? <>{fullDate(item.lastPurchaseDate)}<span className="text-[12px] text-[#8A9599]"> · {rupee(item.lastPurchasePrice)}</span></> : '-'}
                      </td>
                      <td className="px-5 py-3.5 text-[#4B5B61]">{rupee(item.stockValue, 0)}</td>
                      <td className="px-5 py-3.5 text-right">
                        {needsStock && (
                          <button onClick={() => navigate(`/purchases?productId=${item.id}`)}
                            className="inline-flex items-center gap-1.5 rounded-[8px] border border-accent/40 bg-white px-2.5 py-1 text-[12px] font-medium text-accent hover:bg-accent/5">
                            <ShoppingCart size={13} /> Record purchase
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
                {filtered.length === 0 && (
                  <tr><td colSpan={8} className="px-5 py-10 text-center text-sm text-[#8A9599]">
                    {inventory.length === 0 ? 'No products yet. Add products first.' : 'No products match your filters.'}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
