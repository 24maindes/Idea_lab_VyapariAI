import { useMemo, useState } from 'react'
import { Search, Plus, ChevronDown, Upload } from 'lucide-react'
import ImportModal from '../components/ImportModal'
import ProductTable from '../components/ProductTable'
import Button from '../components/Button'
import AddProductModal from '../components/AddProductModal'
import ConfirmModal from '../components/ui/ConfirmModal'
import Skeleton from '../components/ui/Skeleton'
import ErrorBox from '../components/ui/ErrorBox'
import { useToast } from '../components/ui/Toast'
import { useAppData } from '../context/AppDataContext'
import { createProduct, deleteProduct, updateProduct } from '../api/products'

export default function Products() {
  const { products, productsLoading, productsError, refreshProducts, refreshInventory } = useAppData()
  const toast = useToast()
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const [modal, setModal] = useState(null) // null | 'add' | product being edited
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [importing, setImporting] = useState(false)

  const categories = useMemo(() => [...new Set(products.map((p) => p.category).filter(Boolean))].sort(), [products])

  const filtered = useMemo(
    () =>
      products.filter(
        (p) => p.name.toLowerCase().includes(search.toLowerCase()) && (category === 'All' || p.category === category)
      ),
    [products, search, category]
  )

  const handleSave = async (body) => {
    // errors thrown here are shown inside the modal; the modal stays open
    if (modal === 'add') {
      await createProduct(body)
      toast.success(`${body.name} added`)
    } else {
      await updateProduct(modal.id, body)
      toast.success(`${body.name} updated`)
    }
    setModal(null)
    refreshProducts()
    refreshInventory()
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deleteProduct(toDelete.id)
      toast.success(`${toDelete.name} deleted`)
      refreshProducts()
      refreshInventory()
    } catch (e) {
      toast.error(e.message) // e.g. "Product has purchases or sales and cannot be deleted"
    } finally {
      setDeleting(false)
      setToDelete(null)
    }
  }

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[24px] font-semibold text-ink">Products</h1>
          <p className="mt-1 text-[14px] text-ink/60">Manage the products and stock for your shop</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" icon={Upload} onClick={() => setImporting(true)}>Import CSV</Button>
          <Button variant="accent" icon={Plus} onClick={() => setModal('add')}>Add Product</Button>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <div className="flex min-w-[240px] flex-1 items-center gap-2 rounded-control border border-ink/15 bg-white px-3 py-2.5">
          <Search size={16} className="text-ink/40" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search products"
            className="w-full bg-transparent text-[14px] text-ink placeholder:text-ink/35 focus:outline-none" />
        </div>
        <div className="relative flex items-center rounded-control border border-ink/15 bg-white px-3 py-2.5">
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="appearance-none bg-transparent pr-6 text-[14px] text-ink focus:outline-none">
            <option value="All">All Categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <ChevronDown size={15} className="pointer-events-none absolute right-3 text-ink/40" />
        </div>
      </div>

      <div className="mt-5">
        {productsError && <ErrorBox message={productsError} onRetry={refreshProducts} />}
        {productsLoading && products.length === 0 ? (
          <div className="space-y-2">{[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-12" />)}</div>
        ) : (
          <ProductTable
            products={filtered}
            onEdit={setModal}
            onDelete={setToDelete}
            emptyText={products.length === 0 ? 'No products yet. Click "Add Product" to create your first one.' : 'No products match your search.'}
          />
        )}
      </div>

      {importing && <ImportModal kind="products" title="Import products from CSV" onClose={() => setImporting(false)} onImported={() => { refreshProducts(); refreshInventory(); toast.success('Products imported') }} />}
      {modal && <AddProductModal product={modal === 'add' ? null : modal} onClose={() => setModal(null)} onSave={handleSave} />}
      <ConfirmModal
        open={Boolean(toDelete)} busy={deleting} title="Delete product?"
        message={toDelete ? `"${toDelete.name}" will be removed. Products that already have purchases or sales cannot be deleted.` : ''}
        onConfirm={handleDelete} onCancel={() => setToDelete(null)}
      />
    </div>
  )
}
