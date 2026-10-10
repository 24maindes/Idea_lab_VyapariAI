import { useMemo, useState } from 'react'
import { Plus, Phone, Pencil, Trash2 } from 'lucide-react'
import { useAppData } from '../context/AppDataContext.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Card from '../components/ui/Card.jsx'
import Button from '../components/ui/Button.jsx'
import SearchInput from '../components/ui/SearchInput.jsx'
import SupplierComparison from '../components/SupplierComparison.jsx'
import Modal from '../components/ui/Modal.jsx'
import ConfirmModal from '../components/ui/ConfirmModal.jsx'
import Skeleton from '../components/ui/Skeleton.jsx'
import ErrorBox from '../components/ui/ErrorBox.jsx'
import { useToast } from '../components/ui/Toast.jsx'
import { createSupplier, deleteSupplier, updateSupplier } from '../api/suppliers'

const emptyForm = { name: '', contact: '', address: '', productIds: [] }

export default function Suppliers() {
  const { suppliers, suppliersLoading, suppliersError, products, refreshSuppliers } = useAppData()
  const toast = useToast()
  const [query, setQuery] = useState('')
  const [modal, setModal] = useState(null) // null | 'add' | supplier being edited
  const [form, setForm] = useState(emptyForm)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [tab, setTab] = useState('list')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return suppliers
    return suppliers.filter(
      (s) => s.name.toLowerCase().includes(q) || (s.contact || '').toLowerCase().includes(q) || s.productNames.join(' ').toLowerCase().includes(q)
    )
  }, [suppliers, query])

  const openAdd = () => { setForm(emptyForm); setErrors({}); setModal('add') }
  const openEdit = (s) => {
    setForm({ name: s.name, contact: s.contact || '', address: s.address || '', productIds: s.productIds })
    setErrors({})
    setModal(s)
  }
  const updateField = (field, value) => setForm((prev) => ({ ...prev, [field]: value }))
  const toggleProduct = (id) =>
    updateField('productIds', form.productIds.includes(id) ? form.productIds.filter((x) => x !== id) : [...form.productIds, id])

  const handleSubmit = async (e) => {
    e.preventDefault()
    const next = {}
    if (!form.name.trim()) next.name = 'Supplier name is required'
    setErrors(next)
    if (Object.keys(next).length) return
    setSaving(true)
    try {
      const body = { name: form.name.trim(), contact: form.contact.trim(), address: form.address.trim(), productIds: form.productIds }
      if (modal === 'add') {
        await createSupplier(body)
        toast.success(`${body.name} added`)
      } else {
        await updateSupplier(modal.id, body)
        toast.success(`${body.name} updated`)
      }
      setModal(null)
      refreshSuppliers()
    } catch (err) {
      setErrors({ form: err.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deleteSupplier(toDelete.id)
      toast.success(`${toDelete.name} deleted`)
      refreshSuppliers()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setDeleting(false)
      setToDelete(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Suppliers"
        subtitle="Manage the suppliers you purchase stock from."
        action={<Button variant="primary" onClick={openAdd}><Plus className="h-4 w-4" />Add Supplier</Button>}
      />

      <div className="mb-5 inline-flex rounded-[8px] border border-[#D9DEDA] bg-white p-0.5">
        {[['list', 'Suppliers'], ['compare', 'Compare']].map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} aria-pressed={tab === key}
            className={`rounded-[6px] px-4 py-1.5 text-sm font-medium transition-colors ${tab === key ? 'bg-primary text-white' : 'text-[#4B5B61] hover:bg-[#F1F2EF]'}`}>{label}</button>
        ))}
      </div>

      {tab === 'compare' ? <SupplierComparison /> : (<>
      <div className="mb-4 flex items-center justify-between gap-3">
        <SearchInput value={query} onChange={setQuery} placeholder="Search suppliers or products..." />
        <p className="text-[13px] text-[#6B7A7E]">{filtered.length} of {suppliers.length} suppliers</p>
      </div>

      {suppliersError && <ErrorBox message={suppliersError} onRetry={refreshSuppliers} />}

      <Card className="overflow-hidden">
        {suppliersLoading && suppliers.length === 0 ? (
          <div className="space-y-2 p-4">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12" />)}</div>
        ) : (
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
                      {s.contact ? (
                        <span className="inline-flex items-center gap-1.5"><Phone className="h-3.5 w-3.5 text-secondary" />{s.contact}</span>
                      ) : '—'}
                    </td>
                    <td className="px-5 py-3.5">
                      {s.productNames.length ? (
                        <div className="flex flex-wrap gap-1.5">
                          {s.productNames.map((p) => (
                            <span key={p} className="rounded-full bg-[#EAF2F1] px-2.5 py-0.5 text-[12px] text-secondary">{p}</span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[13px] text-[#9AA5A8]">Not linked yet</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button onClick={() => openEdit(s)} aria-label={`Edit ${s.name}`} title="Edit" className="inline-flex h-8 w-8 items-center justify-center rounded-[8px] text-[#6B7A7E] hover:bg-[#F1F2EF]">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => setToDelete(s)} aria-label={`Delete ${s.name}`} title="Delete" className="inline-flex h-8 w-8 items-center justify-center rounded-[8px] text-[#6B7A7E] hover:bg-accent/10 hover:text-accent">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-5 py-10 text-center text-sm text-[#8A9599]">
                      {suppliers.length === 0 ? 'No suppliers yet. Click "Add Supplier" to create one.' : 'No suppliers match your search.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      </>)}

      <Modal open={Boolean(modal)} title={modal === 'add' ? 'Add Supplier' : 'Edit Supplier'} onClose={() => setModal(null)}>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <Field label="Supplier Name" error={errors.name}>
            <input className={inputClass(errors.name)} value={form.name} onChange={(e) => updateField('name', e.target.value)} placeholder="e.g. Patil Grocery Suppliers" />
          </Field>
          <Field label="Phone Number">
            <input className={inputClass()} value={form.contact} onChange={(e) => updateField('contact', e.target.value)} placeholder="e.g. +91 98765 43210" />
          </Field>
          <Field label="Address">
            <textarea className={inputClass() + ' resize-none'} rows={2} value={form.address} onChange={(e) => updateField('address', e.target.value)} placeholder="Shop / market address" />
          </Field>

          <div>
            <p className="mb-1.5 text-sm font-medium text-text">Products supplied</p>
            {products.length === 0 ? (
              <p className="text-[12px] text-[#8A9599]">Add products first, then link them here.</p>
            ) : (
              <div className="flex max-h-44 flex-wrap gap-2 overflow-y-auto rounded-[8px] border border-[#D9DEDA] p-2">
                {products.map((p) => {
                  const on = form.productIds.includes(p.id)
                  return (
                    <button type="button" key={p.id} onClick={() => toggleProduct(p.id)} aria-pressed={on}
                      className={`rounded-full border px-3 py-1 text-[12px] transition-colors ${on ? 'border-secondary bg-secondary text-white' : 'border-[#D9DEDA] bg-white text-[#4B5B61] hover:bg-[#F1F2EF]'}`}>
                      {p.name}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {errors.form && <p className="text-[12px] text-accent">{errors.form}</p>}
          <div className="mt-2 flex justify-end gap-3">
            <Button type="button" variant="secondary" onClick={() => setModal(null)}>Cancel</Button>
            <Button type="submit" variant="primary" disabled={saving}>{saving ? 'Saving...' : modal === 'add' ? 'Add Supplier' : 'Save Changes'}</Button>
          </div>
        </form>
      </Modal>

      <ConfirmModal
        open={Boolean(toDelete)} busy={deleting} title="Delete supplier?"
        message={toDelete ? `"${toDelete.name}" will be removed. Suppliers that already have purchases cannot be deleted.` : ''}
        onConfirm={handleDelete} onCancel={() => setToDelete(null)}
      />
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
