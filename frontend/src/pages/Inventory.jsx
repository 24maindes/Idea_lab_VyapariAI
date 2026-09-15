import { useMemo, useState } from 'react'
import { useAppData } from '../context/AppDataContext.jsx'
import { getStockStatus } from '../data/mockData.js'
import PageHeader from '../components/ui/PageHeader.jsx'
import Card from '../components/ui/Card.jsx'
import SearchInput from '../components/ui/SearchInput.jsx'
import Badge from '../components/ui/Badge.jsx'

export default function Inventory() {
  const { inventory } = useAppData()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')

  const categories = useMemo(
    () => ['All', ...Array.from(new Set(inventory.map((i) => i.category)))],
    [inventory]
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return inventory.filter((item) => {
      const matchesQuery = !q || item.product.toLowerCase().includes(q)
      const matchesCategory = category === 'All' || item.category === category
      return matchesQuery && matchesCategory
    })
  }, [inventory, query, category])

  return (
    <div>
      <PageHeader
        title="Inventory"
        subtitle="Current stock levels across all products."
      />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <SearchInput value={query} onChange={setQuery} placeholder="Search products..." />
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-[8px] border border-[#D9DEDA] bg-white px-3 py-2 text-sm text-text
              focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary/20"
          >
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <p className="text-[13px] text-[#6B7A7E]">{filtered.length} of {inventory.length} products</p>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[#E7E9E4] bg-[#FAFAF8] text-[12px] uppercase tracking-wide text-[#7C8A8E]">
                <th className="px-5 py-3 font-medium">Product</th>
                <th className="px-5 py-3 font-medium">Category</th>
                <th className="px-5 py-3 font-medium">Unit</th>
                <th className="px-5 py-3 font-medium">Quantity</th>
                <th className="px-5 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const status = getStockStatus(item.quantity, item.lowStockThreshold)
                return (
                  <tr key={item.id} className="border-b border-[#EFF1EC] last:border-0 hover:bg-[#FAFBF9]">
                    <td className="px-5 py-3.5 font-medium text-text">{item.product}</td>
                    <td className="px-5 py-3.5 text-[#4B5B61]">{item.category}</td>
                    <td className="px-5 py-3.5 text-[#4B5B61]">{item.unit}</td>
                    <td className="px-5 py-3.5 text-[#4B5B61]">{item.quantity}</td>
                    <td className="px-5 py-3.5">
                      <Badge tone={status}>{status}</Badge>
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-10 text-center text-sm text-[#8A9599]">
                    No products match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
