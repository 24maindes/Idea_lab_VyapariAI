// Add / Edit product. Pass `product` to edit, nothing to add. Calls onSave(formBody) and shows server errors inside the form.
import { useEffect, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import Modal from './Modal'
import InputField from './InputField'
import Button from './Button'
import { listCommodities } from '../api/reference'

const UNITS = ['kg', 'litre', 'packet', 'box']
const CATEGORIES = ['Grocery', 'Grains', 'Pulses', 'Staples', 'Oils', 'Vegetables', 'Dairy', 'Beverages', 'Snacks', 'Household']

export default function AddProductModal({ product, onClose, onSave }) {
  const editing = Boolean(product)
  const [form, setForm] = useState({
    name: product?.name ?? '',
    category: product?.category ?? '',
    unit: product?.unit ?? '',
    openingStock: '',
    reorderLevel: product?.reorderLevel ?? '',
    sellingPrice: product?.sellingPrice ?? '',
    referenceCommodity: product?.referenceCommodity ?? '',
  })
  const [commodities, setCommodities] = useState([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    listCommodities().then(setCommodities).catch(() => setCommodities([]))   // the dropdown just stays at "None"
  }, [])

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const handleSave = async () => {
    if (!form.name.trim() || !form.unit) {
      setError('Please enter a product name and choose a unit.')
      return
    }
    const body = {
      name: form.name.trim(),
      category: form.category || null,
      unit: form.unit,
      reorderLevel: form.reorderLevel === '' ? 0 : Number(form.reorderLevel),
      sellingPrice: form.sellingPrice === '' ? null : Number(form.sellingPrice),
      referenceCommodity: form.referenceCommodity || null,
    }
    if (!editing) body.openingStock = form.openingStock === '' ? 0 : Number(form.openingStock)
    setSaving(true)
    setError('')
    try {
      await onSave(body)
    } catch (e) {
      setError(e.message)
      setSaving(false)
    }
  }

  return (
    <Modal title={editing ? 'Edit Product' : 'Add Product'} onClose={onClose}>
      <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
        <InputField label="Product Name" value={form.name} onChange={update('name')} placeholder="e.g. Toor Dal" />
        <Select label="Category" value={form.category} onChange={update('category')} options={CATEGORIES} optional />
        <Select label="Unit" value={form.unit} onChange={update('unit')} options={UNITS} />
        {!editing && (
          <InputField label="Opening Stock" type="number" min="0" step="any" value={form.openingStock} onChange={update('openingStock')} placeholder="e.g. 25" />
        )}
        <InputField label="Reorder Level" type="number" min="0" step="any" value={form.reorderLevel} onChange={update('reorderLevel')} placeholder="Alert when stock falls to this" />
        <InputField label="Selling Price per unit (₹, optional)" type="number" min="0" step="any" value={form.sellingPrice} onChange={update('sellingPrice')} placeholder="e.g. 48" />
        <div className="w-full">
          <label className="mb-1.5 block text-[13px] font-medium text-ink/80">Reference commodity (market price)</label>
          <div className="relative flex items-center rounded-control border border-ink/15 bg-white px-3 py-2.5 focus-within:border-secondary">
            <select value={form.referenceCommodity} onChange={update('referenceCommodity')} className="w-full appearance-none bg-transparent text-[14px] text-ink focus:outline-none">
              <option value="">None</option>
              {commodities.map((c) => (
                <option key={c.name} value={c.name}>{c.name} ({c.unit})</option>
              ))}
            </select>
            <ChevronDown size={16} className="pointer-events-none text-ink/40" />
          </div>
          <p className="mt-1 text-[11px] text-ink/50">Link a commodity to get fair-price checks, forecasts and recommendations.</p>
        </div>

        {error && <p className="text-[12px] text-accent">{error}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="accent" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : editing ? 'Save Changes' : 'Add Product'}</Button>
        </div>
      </div>
    </Modal>
  )
}

function Select({ label, value, onChange, options, optional = false }) {
  return (
    <div className="w-full">
      <label className="mb-1.5 block text-[13px] font-medium text-ink/80">{label}</label>
      <div className="relative flex items-center rounded-control border border-ink/15 bg-white px-3 py-2.5 focus-within:border-secondary">
        <select value={value} onChange={onChange} className="w-full appearance-none bg-transparent text-[14px] text-ink focus:outline-none">
          <option value="" disabled={!optional}>{optional ? 'None' : `Select ${label.toLowerCase()}`}</option>
          {options.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
        <ChevronDown size={16} className="pointer-events-none text-ink/40" />
      </div>
    </div>
  )
}
