import { useMemo, useState } from 'react'
import { CheckCircle2, PackagePlus } from 'lucide-react'
import { useAppData } from '../context/AppDataContext.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'

const emptyForm = {
  product: '',
  supplier: '',
  quantity: '',
  price: '',
  date: new Date().toISOString().slice(0, 10),
}

export default function PurchaseEntry() {
  const { products, suppliers, purchases, addPurchase } = useAppData()
  const [form, setForm] = useState(emptyForm)
  const [errors, setErrors] = useState({})
  const [confirmation, setConfirmation] = useState(null)

  const updateField = (field, value) => setForm((prev) => ({ ...prev, [field]: value }))

  const validate = () => {
    const next = {}
    if (!form.product) next.product = 'Select a product'
    if (!form.supplier) next.supplier = 'Select a supplier'
    if (!form.quantity || Number(form.quantity) <= 0) next.quantity = 'Enter a valid quantity'
    if (!form.price || Number(form.price) <= 0) next.price = 'Enter a valid purchase price'
    if (!form.date) next.date = 'Select a date'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    const saved = addPurchase({
      product: form.product,
      supplier: form.supplier,
      quantity: Number(form.quantity),
      price: Number(form.price),
      date: form.date,
    })
    setConfirmation(saved)
    setForm(emptyForm)
    setErrors({})
    window.setTimeout(() => setConfirmation(null), 4000)
  }

  const recentPurchases = useMemo(() => purchases.slice(0, 6), [purchases])

  return (
    <div>
      <PageHeader
        title="Purchase Entry"
        subtitle="Record stock purchased from a supplier."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <Card className="p-6 lg:col-span-2">
          <div className="mb-5 flex items-center gap-2">
            <PackagePlus className="h-4 w-4 text-secondary" />
            <h2 className="text-[16px] font-semibold text-text">New Purchase</h2>
          </div>

          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <Field label="Product" error={errors.product}>
              <select
                className={inputClass(errors.product)}
                value={form.product}
                onChange={(e) => updateField('product', e.target.value)}
              >
                <option value="">Select product</option>
                {products.map((p) => (
                  <option key={p.id} value={p.name}>{p.name}</option>
                ))}
              </select>
            </Field>

            <Field label="Supplier" error={errors.supplier}>
              <select
                className={inputClass(errors.supplier)}
                value={form.supplier}
                onChange={(e) => updateField('supplier', e.target.value)}
              >
                <option value="">Select supplier</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.name}>{s.name}</option>
                ))}
              </select>
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Quantity" error={errors.quantity}>
                <input
                  type="number"
                  min="0"
                  className={inputClass(errors.quantity)}
                  value={form.quantity}
                  onChange={(e) => updateField('quantity', e.target.value)}
                  placeholder="e.g. 20"
                />
              </Field>
              <Field label="Purchase Price (₹)" error={errors.price}>
                <input
                  type="number"
                  min="0"
                  className={inputClass(errors.price)}
                  value={form.price}
                  onChange={(e) => updateField('price', e.target.value)}
                  placeholder="e.g. 1200"
                />
              </Field>
            </div>

            <Field label="Purchase Date" error={errors.date}>
              <input
                type="date"
                className={inputClass(errors.date)}
                value={form.date}
                onChange={(e) => updateField('date', e.target.value)}
              />
            </Field>

            {confirmation && (
              <div className="flex items-center gap-2 rounded-[8px] bg-[#E4EFE7] px-3 py-2.5 text-[13px] text-[#3C6B4B]">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                Purchase {confirmation.id} saved — {confirmation.quantity} × {confirmation.product} added to inventory.
              </div>
            )}

            <Button type="submit" variant="primary" className="mt-1 w-full">
              Save Purchase
            </Button>
          </form>
        </Card>

        <Card className="overflow-hidden lg:col-span-3">
          <div className="border-b border-[#E7E9E4] px-5 py-4">
            <h2 className="text-[16px] font-semibold text-text">Recent Purchases</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[#E7E9E4] bg-[#FAFAF8] text-[12px] uppercase tracking-wide text-[#7C8A8E]">
                  <th className="px-5 py-3 font-medium">Purchase ID</th>
                  <th className="px-5 py-3 font-medium">Product</th>
                  <th className="px-5 py-3 font-medium">Supplier</th>
                  <th className="px-5 py-3 font-medium">Qty</th>
                  <th className="px-5 py-3 font-medium">Price (₹)</th>
                  <th className="px-5 py-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {recentPurchases.map((p) => (
                  <tr key={p.id} className="border-b border-[#EFF1EC] last:border-0 hover:bg-[#FAFBF9]">
                    <td className="px-5 py-3.5 text-[#4B5B61]">{p.id}</td>
                    <td className="px-5 py-3.5 font-medium text-text">{p.product}</td>
                    <td className="px-5 py-3.5 text-[#4B5B61]">{p.supplier}</td>
                    <td className="px-5 py-3.5 text-[#4B5B61]">{p.quantity}</td>
                    <td className="px-5 py-3.5 text-[#4B5B61]">₹{p.price.toLocaleString('en-IN')}</td>
                    <td className="px-5 py-3.5 text-[#4B5B61]">{p.date}</td>
                  </tr>
                ))}
                {recentPurchases.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-5 py-10 text-center text-sm text-[#8A9599]">
                      No purchases recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
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
