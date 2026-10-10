import { useEffect, useMemo, useState } from 'react'
import { Receipt, Trash2, IndianRupee, Package, TrendingUp, Upload } from 'lucide-react'
import ImportModal from '../components/ImportModal.jsx'
import { useAppData } from '../context/AppDataContext.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'
import ErrorBox from '../components/ui/ErrorBox.jsx'
import ConfirmModal from '../components/ui/ConfirmModal.jsx'
import { useToast } from '../components/ui/Toast.jsx'
import StatCard from '../components/StatCard.jsx'
import { createSale, deleteSale, getSalesSummary, listSales } from '../api/sales'
import { num, rupee, todayISO } from '../utils/format'

export default function Sales() {
  const { products, refreshAll } = useAppData()
  const toast = useToast()
  const [form, setForm] = useState({ productId: '', quantity: '', price: '', date: todayISO() })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const [today, setToday] = useState({ items: [], total: 0 })
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [importing, setImporting] = useState(false)

  const product = products.find((p) => String(p.id) === String(form.productId))

  const load = () => {
    setError('')
    Promise.all([listSales({ from: todayISO(), to: todayISO(), pageSize: 100 }), getSalesSummary(30)])
      .then(([sales, sum]) => { setToday(sales); setSummary(sum) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  // choosing a product prefills its selling price
  const chooseProduct = (id) => {
    const p = products.find((x) => String(x.id) === String(id))
    setForm((f) => ({ ...f, productId: id, price: p?.sellingPrice ?? '' }))
  }

  const qty = Number(form.quantity)
  const stockAfter = product && qty > 0 ? product.currentStock - qty : null
  const total = qty > 0 && Number(form.price) > 0 ? qty * Number(form.price) : null

  const validate = () => {
    const next = {}
    if (!form.productId) next.productId = 'Select a product'
    if (!(qty > 0)) next.quantity = 'Enter a quantity above 0'
    if (!(Number(form.price) > 0)) next.price = 'Enter a price above 0'
    if (!form.date) next.date = 'Select a date'
    else if (form.date > todayISO()) next.date = 'Date cannot be in the future'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const submit = async (e) => {
    e.preventDefault()
    if (saving || !validate()) return
    setSaving(true)
    try {
      const s = await createSale({ productId: Number(form.productId), quantity: qty, unitPrice: Number(form.price), saleDate: form.date })
      toast.success(`Sale recorded: ${s.quantity} ${s.unit} ${s.productName} (${rupee(s.total)})`)
      setForm((f) => ({ ...f, quantity: '' }))          // form stays open for the next sale
      setErrors({})
      refreshAll()
      load()
    } catch (err) {
      toast.error(err.message)                           // e.g. "Only 3 kg in stock"
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    setDeleting(true)
    try {
      await deleteSale(toDelete.id)
      toast.success('Sale deleted. Stock restored.')
      refreshAll()
      load()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setDeleting(false)
      setToDelete(null)
    }
  }

  const t30 = summary?.totals.last30Days
  const profit30 = useMemo(() => (summary ? summary.products.reduce((s, p) => s + p.grossProfit, 0) : 0), [summary])

  return (
    <div>
      <PageHeader title="Sales" subtitle="Record what you sold. Stock goes down automatically." action={<Button variant="secondary" onClick={() => setImporting(true)}><Upload className="h-4 w-4" />Import CSV</Button>} />
      {error && <ErrorBox message={error} onRetry={load} />}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <Card className="p-6 lg:col-span-2">
          <div className="mb-5 flex items-center gap-2">
            <Receipt className="h-4 w-4 text-secondary" />
            <h2 className="text-[16px] font-semibold text-text">Record Sale</h2>
          </div>
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <Field label="Product" error={errors.productId}>
              <select className={inputClass(errors.productId)} value={form.productId} onChange={(e) => chooseProduct(e.target.value)}>
                <option value="">Select product</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label={`Quantity${product ? ` (${product.unit})` : ''}`} error={errors.quantity}>
                <input type="number" min="0" step="any" className={inputClass(errors.quantity)} value={form.quantity}
                  onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))} placeholder="e.g. 5" />
              </Field>
              <Field label="Price per unit (Rs)" error={errors.price}>
                <input type="number" min="0" step="any" className={inputClass(errors.price)} value={form.price}
                  onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))} placeholder="e.g. 48" />
              </Field>
            </div>
            <Field label="Date" error={errors.date}>
              <input type="date" max={todayISO()} className={inputClass(errors.date)} value={form.date} onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))} />
            </Field>

            <div className="rounded-[8px] bg-[#F4F6F3] px-3 py-2.5 text-sm">
              <div className="flex items-center justify-between"><span className="text-[#5B6B70]">Total</span><span className="font-semibold text-text">{total === null ? '-' : rupee(total)}</span></div>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-[#5B6B70]">Stock after sale</span>
                <span className={`font-semibold ${stockAfter !== null && stockAfter < 0 ? 'text-accent' : 'text-text'}`}>
                  {stockAfter === null ? '-' : `${num(stockAfter, 2)} ${product.unit}`}
                </span>
              </div>
              {stockAfter !== null && stockAfter < 0 && <p className="mt-1 text-[12px] text-accent">Not enough stock: only {num(product.currentStock, 2)} {product.unit} available.</p>}
            </div>

            <Button type="submit" variant="primary" className="w-full" disabled={saving}>{saving ? 'Saving...' : 'Save Sale'}</Button>
            <p className="-mt-2 text-center text-[11px] text-[#8A9599]">Press Enter to save. The form stays open for the next sale.</p>
          </form>
        </Card>

        <Card className="overflow-hidden lg:col-span-3">
          <div className="border-b border-[#E7E9E4] px-5 py-4">
            <h2 className="text-[16px] font-semibold text-text">Today's Sales</h2>
          </div>
          {loading ? (
            <div className="space-y-2 p-4">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-10" />)}</div>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[#E7E9E4] bg-[#FAFAF8] text-[12px] uppercase tracking-wide text-[#7C8A8E]">
                  <th className="px-5 py-3 font-medium">Product</th><th className="px-5 py-3 font-medium">Qty</th>
                  <th className="px-5 py-3 font-medium">Price/unit</th><th className="px-5 py-3 font-medium">Total</th><th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {today.items.map((s) => (
                  <tr key={s.id} className="border-b border-[#EFF1EC] last:border-0 hover:bg-[#FAFBF9]">
                    <td className="px-5 py-3 font-medium text-text">{s.productName}</td>
                    <td className="px-5 py-3 text-[#4B5B61]">{s.quantity} {s.unit}</td>
                    <td className="px-5 py-3 text-[#4B5B61]">{rupee(s.unitPrice)}</td>
                    <td className="px-5 py-3 text-[#4B5B61]">{rupee(s.total, 0)}</td>
                    <td className="px-5 py-3 text-right"><button onClick={() => setToDelete(s)} aria-label="Delete sale" className="rounded-[6px] p-1.5 text-[#6B7A7E] hover:bg-accent/10 hover:text-accent"><Trash2 size={15} /></button></td>
                  </tr>
                ))}
                {today.items.length === 0 && <tr><td colSpan={5} className="px-5 py-10 text-center text-sm text-[#8A9599]">No sales recorded today yet.</td></tr>}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <h2 className="mb-3 mt-8 text-[16px] font-semibold text-text">Last 30 days</h2>
      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard icon={IndianRupee} label="Revenue" value={t30 ? rupee(t30.revenue, 0) : '-'} tint="primary" />
        <StatCard icon={Package} label="Units sold" value={t30 ? num(t30.units, 0) : '-'} tint="secondary" />
        <StatCard icon={TrendingUp} label="Gross profit" value={summary ? rupee(profit30, 0) : '-'} tint="accent" />
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[#E7E9E4] bg-[#FAFAF8] text-[12px] uppercase tracking-wide text-[#7C8A8E]">
                <th className="px-5 py-3 font-medium">Product</th><th className="px-5 py-3 font-medium">Qty sold</th>
                <th className="px-5 py-3 font-medium">Revenue</th><th className="px-5 py-3 font-medium">Avg / day</th><th className="px-5 py-3 font-medium">Gross profit</th>
              </tr>
            </thead>
            <tbody>
              {(summary?.products || []).map((p) => (
                <tr key={p.productId} className="border-b border-[#EFF1EC] last:border-0">
                  <td className="px-5 py-3 font-medium text-text">{p.productName}</td>
                  <td className="px-5 py-3 text-[#4B5B61]">{num(p.qtySold, 1)}</td>
                  <td className="px-5 py-3 text-[#4B5B61]">{rupee(p.revenue, 0)}</td>
                  <td className="px-5 py-3 text-[#4B5B61]">{num(p.avgDailySales, 1)}</td>
                  <td className={`px-5 py-3 ${p.grossProfit < 0 ? 'text-accent' : 'text-[#4B5B61]'}`}>{rupee(p.grossProfit, 0)}</td>
                </tr>
              ))}
              {summary && summary.products.length === 0 && <tr><td colSpan={5} className="px-5 py-10 text-center text-sm text-[#8A9599]">No sales in the last 30 days.</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      {importing && <ImportModal kind="sales" title="Import sales from CSV" onClose={() => setImporting(false)} onImported={() => { refreshAll(); load(); toast.success('Sales imported') }} />}
      <ConfirmModal open={Boolean(toDelete)} busy={deleting} title="Delete this sale?"
        message={toDelete ? `${toDelete.quantity} ${toDelete.unit} of ${toDelete.productName}. The stock will be added back.` : ''}
        onConfirm={remove} onCancel={() => setToDelete(null)} />
    </div>
  )
}

function Field({ label, error, children }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="font-medium text-text">{label}</span>
      {children}
      {error && <span className="text-[12px] text-accent">{error}</span>}
    </label>
  )
}
function inputClass(error) {
  return `w-full rounded-[8px] border bg-white px-3 py-2 text-sm text-text placeholder:text-[#9AA5A8]
    focus:outline-none focus:ring-2 focus:ring-secondary/20 ${error ? 'border-accent' : 'border-[#D9DEDA] focus:border-secondary'}`
}
