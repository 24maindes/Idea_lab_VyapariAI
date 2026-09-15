import { useMemo, useState } from 'react'
import { Plus, Phone, MoreHorizontal } from 'lucide-react'
import { useAppData } from '../context/AppDataContext.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import SearchInput from '../components/ui/SearchInput.jsx'
import Modal from '../components/ui/Modal.jsx'

const emptyForm = { name: '', contact: '', address: '' }

export default function Suppliers() {
  const { suppliers, addSupplier } = useAppData()
  const [query, setQuery] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [errors, setErrors] = useState({})

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return suppliers
    return suppliers.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.contact.toLowerCase().includes(q) ||
        s.productsSupplied.join(' ').toLowerCase().includes(q)
    )
  }, [suppliers, query])

  const updateField = (field, value) => setForm((prev) => ({ ...prev, [field]: value }))

  const validate = () => {
    const next = {}
    if (!form.name.trim()) next.name = 'Supplier name is required'
    if (!form.contact.trim()) next.contact = 'Phone number is required'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    addSupplier({
      name: form.name.trim(),
      contact: form.contact.trim(),
      address: form.address.trim(),
    })
    setForm(emptyForm)
    setErrors({})
    setModalOpen(false)
  }

  return (
    <div>
      <PageHeader
        title="Suppliers"
        subtitle="Manage the suppliers you purchase stock from."
        action={
          <Button variant="primary" onClick={() => setModalOpen(true)}>
            <Plus className="h-4 w-4" />
            Add Supplier
          </Button>
        }
      />

      <div className="mb-4 flex items-center justify-between gap-3">
        <SearchInput value={query} onChange={setQuery} placeholder="Search suppliers or products..." />
        <p className="text-[13px] text-[#6B7A7E]">{filtered.length} of {suppliers.length} suppliers</p>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[#E7E9E4] bg-[#FAFAF8] text-[12px] uppercase tracking-wide text-[#7C8A8E]">
                <th className="px-5 py-3 font-medium">Supplier Name</th>
                <th className="px-5 py-3 font-medium">Contact</th>
                <th className="px-5 py-3 font-medium">Products Supplied</th>
                <th className="px-5 py-3 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id} className="border-b border-[#EFF1EC] last:border-0 hover:bg-[#FAFBF9]">
                  <td className="px-5 py-3.5">
                    <p className="font-medium text-text">{s.name}</p>
                    <p className="text-[12px] text-[#8A9599]">{s.address || '—'}</p>
                  </td>
                  <td className="px-5 py-3.5 text-[#4B5B61]">
                    <span className="inline-flex items-center gap-1.5">
                      <Phone className="h-3.5 w-3.5 text-secondary" />
                      {s.contact}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    {s.productsSupplied.length ? (
                      <div className="flex flex-wrap gap-1.5">
                        {s.productsSupplied.map((p) => (
                          <span
                            key={p}
                            className="rounded-full bg-[#EAF2F1] px-2.5 py-0.5 text-[12px] text-secondary"
                          >
                            {p}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-[13px] text-[#9AA5A8]">Not linked yet</span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button
                      className="inline-flex h-8 w-8 items-center justify-center rounded-[8px] text-[#6B7A7E] hover:bg-[#F1F2EF]"
                      aria-label={`Actions for ${s.name}`}
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-10 text-center text-sm text-[#8A9599]">
                    No suppliers match your search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={modalOpen} title="Add Supplier" onClose={() => setModalOpen(false)}>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <Field label="Supplier Name" error={errors.name}>
            <input
              className={inputClass(errors.name)}
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
              placeholder="e.g. Patil Grocery Suppliers"
            />
          </Field>
          <Field label="Phone Number" error={errors.contact}>
            <input
              className={inputClass(errors.contact)}
              value={form.contact}
              onChange={(e) => updateField('contact', e.target.value)}
              placeholder="e.g. +91 98765 43210"
            />
          </Field>
          <Field label="Address">
            <textarea
              className={inputClass() + ' resize-none'}
              rows={3}
              value={form.address}
              onChange={(e) => updateField('address', e.target.value)}
              placeholder="Shop / market address"
            />
          </Field>

          <div className="mt-2 flex justify-end gap-3">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Add Supplier
            </Button>
          </div>
        </form>
      </Modal>
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
