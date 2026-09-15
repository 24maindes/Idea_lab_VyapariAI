import { MoreVertical } from "lucide-react";

function StockBadge({ stock }) {
  let style = "bg-emerald-50 text-emerald-700";
  let label = "In stock";
  if (stock <= 15) {
    style = "bg-amber-50 text-amber-700";
    label = "Low stock";
  }
  if (stock === 0) {
    style = "bg-red-50 text-red-700";
    label = "Out of stock";
  }
  return (
    <span className={`rounded-control px-2 py-0.5 text-[12px] font-medium ${style}`}>
      {label}
    </span>
  );
}

export default function ProductTable({ products }) {
  return (
    <div className="overflow-hidden rounded-card border border-ink/10 bg-white shadow-subtle">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-ink/10 bg-ink/[0.02]">
            <th className="px-4 py-3 text-[12px] font-semibold uppercase tracking-wide text-ink/50">
              Product Name
            </th>
            <th className="px-4 py-3 text-[12px] font-semibold uppercase tracking-wide text-ink/50">
              Category
            </th>
            <th className="px-4 py-3 text-[12px] font-semibold uppercase tracking-wide text-ink/50">
              Unit
            </th>
            <th className="px-4 py-3 text-[12px] font-semibold uppercase tracking-wide text-ink/50">
              Stock
            </th>
            <th className="px-4 py-3 text-[12px] font-semibold uppercase tracking-wide text-ink/50">
              Status
            </th>
            <th className="px-4 py-3 text-right text-[12px] font-semibold uppercase tracking-wide text-ink/50">
              Action
            </th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr
              key={p.id}
              className="border-b border-ink/5 text-[14px] last:border-0 hover:bg-ink/[0.015]"
            >
              <td className="px-4 py-3 font-medium text-ink">{p.name}</td>
              <td className="px-4 py-3 text-ink/70">{p.category}</td>
              <td className="px-4 py-3 text-ink/70">{p.unit}</td>
              <td className="px-4 py-3 text-ink/70">{p.stock}</td>
              <td className="px-4 py-3">
                <StockBadge stock={p.stock} />
              </td>
              <td className="px-4 py-3 text-right">
                <button className="rounded-control p-1.5 text-ink/40 hover:bg-ink/5 hover:text-ink">
                  <MoreVertical size={16} />
                </button>
              </td>
            </tr>
          ))}
          {products.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-10 text-center text-[14px] text-ink/40">
                No products match your search.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
