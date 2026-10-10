import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PackagePlus, ChevronLeft, ChevronRight, Trash2, Upload } from 'lucide-react'
import ImportModal from '../components/ImportModal.jsx'
import { useAppData } from '../context/AppDataContext.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import ConfirmModal from '../components/ui/ConfirmModal.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'
import ErrorBox from '../components/ui/ErrorBox.jsx'
import { useToast } from '../components/ui/Toast.jsx'
import FairPriceChip from '../components/FairPriceChip.jsx'
import AnomalyModal from '../components/AnomalyModal.jsx'
import { createPurchase, deletePurchase, listPurchases } from '../api/purchases'
import { ALERTS_CHANGED } from '../hooks/useUnreadAlerts'
import { fullDate, rupee, todayISO } from '../utils/format'

const emptyForm = (productId = '') => ({ productId, supplierId: '', quantity: '', price: '', date: todayISO() })

export default function PurchaseEntry() {
  const { products, suppliers, purchases, purchasesLoading, refreshAll } = useAppData()
  const toast = useToast()
  const [params] = useSearchParams()
  const [tab, setTab] = useState('new')
  const [form, setForm] = useState(() => emptyForm(params.get('productId') || ''))
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [anomaly, setAnomaly] = useState(null) // { purchaseId, ...insights.anomaly }
  const [undoing, setUndoing] = useState(false)
  const [importing, setImporting] = useState(false)

  // ?productId= in the URL preselects the product (used by "Record purchase" buttons elsewhere)
  useEffect(() => {
    const id = params.get('productId')
    if (id) setForm((f) => ({ ...f, productId: id }))
  }, [params])

  const updateField = (field, value) => setForm((prev) => ({ ...prev, [field]: value }))
  const product = products.find((p) => String(p.id) === String(form.productId))
  const total = Number(form.quantity) > 0 && Number(form.price) > 0 ? Number(form.quantity) * Number(form.price) : null

  const validate = () => {
    const next = {}
    if (!form.productId) next.productId = 'Select a product'
    if (!form.supplierId) next.supplierId = 'Select a supplier'
    if (!(Number(form.quantity) > 0)) next.quantity = 'Enter a quantity above 0'
    if (!(Number(form.price) > 0)) next.price = 'Enter a price above 0'
    if (!form.date) next.date = 'Select a date'
    else if (form.date > todayISO()) next.date = 'Date cannot be in the future'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (saving || !validate()) return
    setSaving(true)
    try {
      const saved = await createPurchase({
        productId: Number(form.productId), supplierId: Number(form.supplierId),
        quantity: Number(form.quantity), unitPrice: Number(form.price), purchaseDate: form.date,
      })
      toast.success(`Saved: ${saved.quantity} ${saved.unit} of ${saved.productName} (${rupee(saved.total)})`)
      setForm((f) => ({ ...emptyForm(f.productId), supplierId: f.supplierId }))   // keep product and supplier for the next entry
      setErrors({})
      refreshAll()
      if (saved.insights?.anomaly) {
        setAnomaly({ purchaseId: saved.id, ...saved.insights.anomaly })
        window.dispatchEvent(new Event(ALERTS_CHANGED))                            // the sidebar badge updates now
      }
    } catch (err) {
      toast.error(err.message)
      setErrors({ form: err.message })
    } finally {
      setSaving(false)
    }
  }

  const undo = async () => {
    setUndoing(true)
    try {
      await deletePurchase(anomaly.purchaseId)
      toast.success('Purchase removed. Stock is back to what it was.')
      refreshAll()
      window.dispatchEvent(new Event(ALERTS_CHANGED))
      setAnomaly(null)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setUndoing(false)
    }
  }

  return (
    <div>
      <PageHeader title="Purchase Entry" subtitle="Record stock purchased from a supplier." action={<Button variant="secondary" onClick={() => setImporting(true)}><Upload className="h-4 w-4" />Import CSV</Button>} />

      <div className="mb-5 inline-flex rounded-[8px] border border-[#D9DEDA] bg-white p-0.5">
        {[['new', 'New Purchase'], ['history', 'History']].map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`rounded-[6px] px-4 py-1.5 text-sm font-medium transition-colors ${tab === key ? 'bg-primary text-white' : 'text-[#4B5B61] hover:bg-[#F1F2EF]'}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'history' ? (
        <History products={products} suppliers={suppliers} onChanged={refreshAll} />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          <Card className="p-6 lg:col-span-2">
            <div className="mb-5 flex items-center gap-2">
              <PackagePlus className="h-4 w-4 text-secondary" />
              <h2 className="text-[16px] font-semibold text-text">New Purchase</h2>
            </div>

            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              <Field label="Product" error={errors.productId}>
                <select className={inputClass(errors.productId)} value={form.productId} onChange={(e) => updateField('productId', e.target.value)}>
                  <option value="">Select product</option>
                  {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </Field>

              <Field label="Supplier" error={errors.supplierId}>
                <select className={inputClass(errors.supplierId)} value={form.supplierId} onChange={(e) => updateField('supplierId', e.target.value)}>
                  <option value="">Select supplier</option>
                  {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </Field>

              <div className="grid grid-cols-2 gap-4">
                <Field label={`Quantity${product ? ` (${product.unit})` : ''}`} error={errors.quantity}>
                  <input type="number" min="0" step="any" className={inputClass(errors.quantity)} value={form.quantity}
                    onChange={(e) => updateField('quantity', e.target.value)} placeholder="e.g. 20" />
                </Field>
                <Field label="Price per unit (Rs)" error={errors.price}>
                  <input type="number" min="0" step="any" className={inputClass(errors.price)} value={form.price}
                    onChange={(e) => updateField('price', e.target.value)} placeholder="e.g. 42.50" />
                </Field>
              </div>

              <div className="-mt-2">
                <FairPriceChip productId={form.productId} price={form.price} date={form.date} />
              </div>

              <Field label="Purchase Date" error={errors.date}>
                <input type="date" max={todayISO()} className={inputClass(errors.date)} value={form.date} onChange={(e) => updateField('date', e.target.value)} />
              </Field>

              <div className="flex items-center justify-between rounded-[8px] bg-[#F4F6F3] px-3 py-2.5 text-sm">
                <span className="text-[#5B6B70]">Total amount</span>
                <span className="font-semibold text-text">{total === null ? '-' : rupee(total)}</span>
              </div>

              {errors.form && <p className="text-[12px] text-accent">{errors.form}</p>}

              <Button type="submit" variant="primary" className="mt-1 w-full" disabled={saving}>
                {saving ? 'Saving...' : 'Save Purchase'}
              </Button>
            </form>
          </Card>

          <Card className="overflow-hidden lg:col-span-3">
            <div className="border-b border-[#E7E9E4] px-5 py-4">
              <h2 className="text-[16px] font-semibold text-text">Recent Purchases</h2>
            </div>
            {purchasesLoading && purchases.length === 0 ? (
              <div className="space-y-2 p-4">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-10" />)}</div>
            ) : (
              <PurchaseTable rows={purchases.slice(0, 8)} empty="No purchases recorded yet." />
            )}
          </Card>
        </div>
      )}

      {importing && <ImportModal kind="purchases" title="Import purchases from CSV" showSupplierOption onClose={() => setImporting(false)} onImported={() => { refreshAll(); window.dispatchEvent(new Event(ALERTS_CHANGED)); toast.success('Purchases imported') }} />}
      <AnomalyModal anomaly={anomaly} busy={undoing} onKeep={() => setAnomaly(null)} onUndo={undo} />
    </div>
  )
}

// ---------------------------------------------------------------- History tab
function History({ products, suppliers, onChanged }) {
  const toast = useToast()
  const [filters, setFilters] = useState({ productId: '', supplierId: '', from: '', to: '', sort: 'date_desc' })
  const [page, setPage] = useState(1)
  const [data, setData] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const pageSize = 15

  const load = () => {
    setLoading(true)
    setError('')
    listPurchases({ ...filters, page, pageSize })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(load, [filters, page]) // eslint-disable-line react-hooks/exhaustive-deps

  const setFilter = (key, value) => { setPage(1); setFilters((f) => ({ ...f, [key]: value })) }
  const pages = Math.max(1, Math.ceil(data.total / pageSize))

  const remove = async () => {
    setDeleting(true)
    try {
      await deletePurchase(toDelete.id)
      toast.success('Purchase deleted. Stock was reduced again.')
      onChanged()
      load()
    } catch (e) {
      toast.error(e.message)            // e.g. "Cannot delete: 8 kg of Rice from this purchase were already sold"
    } finally {
      setDeleting(false)
      setToDelete(null)
    }
  }

  const sel = 'rounded-[8px] border border-[#D9DEDA] bg-white px-3 py-2 text-sm text-text focus:border-secondary focus:outline-none'
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <select className={sel} value={filters.productId} onChange={(e) => setFilter('productId', e.target.value)} aria-label="Filter by product">
          <option value="">All products</option>
          {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select className={sel} value={filters.supplierId} onChange={(e) => setFilter('supplierId', e.target.value)} aria-label="Filter by supplier">
          <option value="">All suppliers</option>
          {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <label className="text-[12px] text-[#6B7A7E]">From <input type="date" className={sel} value={filters.from} onChange={(e) => setFilter('from', e.target.value)} /></label>
        <label className="text-[12px] text-[#6B7A7E]">To <input type="date" className={sel} value={filters.to} onChange={(e) => setFilter('to', e.target.value)} /></label>
        <select className={sel} value={filters.sort} onChange={(e) => setFilter('sort', e.target.value)} aria-label="Sort">
          <option value="date_desc">Newest first</option>
          <option value="date_asc">Oldest first</option>
          <option value="price_desc">Price: high to low</option>
          <option value="price_asc">Price: low to high</option>
        </select>
      </div>

      {error && <ErrorBox message={error} onRetry={load} />}
      <Card className="overflow-hidden">
        {loading ? (
          <div className="space-y-2 p-4">{[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-10" />)}</div>
        ) : (
          <PurchaseTable rows={data.items} empty="No purchases match these filters." onDelete={setToDelete} />
        )}
        <div className="flex items-center justify-between border-t border-[#E7E9E4] px-5 py-3 text-[13px] text-[#6B7A7E]">
          <span>{data.total} purchases</span>
          <div className="flex items-center gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} aria-label="Previous page" className="rounded-[6px] border border-[#D9DEDA] p-1 disabled:opacity-40"><ChevronLeft size={16} /></button>
            <span>Page {page} of {pages}</span>
            <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)} aria-label="Next page" className="rounded-[6px] border border-[#D9DEDA] p-1 disabled:opacity-40"><ChevronRight size={16} /></button>
          </div>
        </div>
      </Card>

      <ConfirmModal open={Boolean(toDelete)} busy={deleting} title="Delete this purchase?"
        message={toDelete ? `${toDelete.quantity} ${toDelete.unit} of ${toDelete.productName} on ${fullDate(toDelete.purchaseDate)}. Stock will be reduced by that amount.` : ''}
        onConfirm={remove} onCancel={() => setToDelete(null)} />
    </div>
  )
}

function PurchaseTable({ rows, empty, onDelete }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-[#E7E9E4] bg-[#FAFAF8] text-[12px] uppercase tracking-wide text-[#7C8A8E]">
            <th className="px-5 py-3 font-medium">Date</th>
            <th className="px-5 py-3 font-medium">Product</th>
            <th className="px-5 py-3 font-medium">Supplier</th>
            <th className="px-5 py-3 font-medium">Qty</th>
            <th className="px-5 py-3 font-medium">Price/unit</th>
            <th className="px-5 py-3 font-medium">Total</th>
            {onDelete && <th className="px-5 py-3 font-medium text-right"> </th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id} className="border-b border-[#EFF1EC] last:border-0 hover:bg-[#FAFBF9]">
              <td className="px-5 py-3 text-[#4B5B61]">{fullDate(p.purchaseDate)}</td>
              <td className="px-5 py-3 font-medium text-text">{p.productName}</td>
              <td className="px-5 py-3 text-[#4B5B61]">{p.supplierName || '-'}</td>
              <td className="px-5 py-3 text-[#4B5B61]">{p.quantity} {p.unit}</td>
              <td className="px-5 py-3 text-[#4B5B61]">{rupee(p.unitPrice)}</td>
              <td className="px-5 py-3 text-[#4B5B61]">{rupee(p.total, 0)}</td>
              {onDelete && (
                <td className="px-5 py-3 text-right">
                  <button onClick={() => onDelete(p)} aria-label="Delete purchase" title="Delete" className="rounded-[6px] p-1.5 text-[#6B7A7E] hover:bg-accent/10 hover:text-accent"><Trash2 size={15} /></button>
                </td>
              )}
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={onDelete ? 7 : 6} className="px-5 py-10 text-center text-sm text-[#8A9599]">{empty}</td></tr>
          )}
        </tbody>
      </table>
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
    focus:outline-none focus:ring-2 focus:ring-secondary/20
    ${error ? 'border-accent' : 'border-[#D9DEDA] focus:border-secondary'}`
}
