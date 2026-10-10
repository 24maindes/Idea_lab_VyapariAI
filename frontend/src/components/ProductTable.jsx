import { Pencil, Trash2 } from 'lucide-react'

const STATUS_STYLE = {
  'In Stock': 'bg-emerald-50 text-emerald-700',
  'Low Stock': 'bg-amber-50 text-amber-700',
  'Out of Stock': 'bg-red-50 text-red-700',
}

const TH = 'px-4 py-3 text-[12px] font-semibold uppercase tracking-wide text-ink/50'

export default function ProductTable({ products, onEdit, onDelete, emptyText = 'No products match your search.' }) {
  return (
    <div className="overflow-hidden rounded-card border border-ink/10 bg-white shadow-subtle">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-ink/10 bg-ink/[0.02]">
            <th className={TH}>Product Name</th>
            <th className={TH}>Category</th>
            <th className={TH}>Unit</th>
            <th className={TH}>Stock</th>
            <th className={TH}>Status</th>
            <th className={`${TH} text-right`}>Action</th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id} className="border-b border-ink/5 text-[14px] last:border-0 hover:bg-ink/[0.015]">
              <td className="px-4 py-3 font-medium text-ink">
                {p.name}
                {p.referenceCommodity && <span className="ml-2 rounded-full bg-secondary/10 px-2 py-0.5 text-[11px] font-normal text-secondary">{p.referenceCommodity}</span>}
              </td>
              <td className="px-4 py-3 text-ink/70">{p.category || '-'}</td>
              <td className="px-4 py-3 text-ink/70">{p.unit}</td>
              <td className="px-4 py-3 text-ink/70">{Number(p.currentStock).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
              <td className="px-4 py-3">
                <span className={`rounded-control px-2 py-0.5 text-[12px] font-medium ${STATUS_STYLE[p.stockStatus]}`}>{p.stockStatus}</span>
              </td>
              <td className="px-4 py-3 text-right">
                <button onClick={() => onEdit(p)} title="Edit" aria-label={`Edit ${p.name}`} className="rounded-control p-1.5 text-ink/40 hover:bg-ink/5 hover:text-ink">
                  <Pencil size={15} />
                </button>
                <button onClick={() => onDelete(p)} title="Delete" aria-label={`Delete ${p.name}`} className="rounded-control p-1.5 text-ink/40 hover:bg-accent/10 hover:text-accent">
                  <Trash2 size={15} />
                </button>
              </td>
            </tr>
          ))}
          {products.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-10 text-center text-[14px] text-ink/40">{emptyText}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
