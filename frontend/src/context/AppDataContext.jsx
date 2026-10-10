// Shared data: products, suppliers, recent purchases and inventory come from the API after login.
// Pages call refreshX() after they change something, so every page stays in sync.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useAuth } from './AuthContext'
import { listProducts } from '../api/products'
import { listSuppliers } from '../api/suppliers'
import { listPurchases } from '../api/purchases'
import { getInventory } from '../api/inventory'

const AppDataContext = createContext(null)

const empty = { data: [], loading: true, error: '' }

export function AppDataProvider({ children }) {
  const { token, shop } = useAuth()
  const ready = Boolean(token && shop)

  const [products, setProducts] = useState(empty)
  const [suppliers, setSuppliers] = useState(empty)
  const [purchases, setPurchases] = useState(empty)
  const [inventory, setInventory] = useState(empty)

  // one generic loader: keeps old data while reloading, remembers the error message
  const loader = (setter, fetcher) => async () => {
    setter((s) => ({ ...s, loading: true, error: '' }))
    try {
      setter({ data: await fetcher(), loading: false, error: '' })
    } catch (e) {
      setter((s) => ({ ...s, loading: false, error: e.message }))
    }
  }

  const refreshProducts = useCallback(loader(setProducts, () => listProducts()), [])
  const refreshSuppliers = useCallback(loader(setSuppliers, () => listSuppliers()), [])
  const refreshPurchases = useCallback(loader(setPurchases, async () => (await listPurchases({ pageSize: 10 })).items), [])
  const refreshInventory = useCallback(loader(setInventory, () => getInventory()), [])

  const refreshAll = useCallback(
    () => Promise.all([refreshProducts(), refreshSuppliers(), refreshPurchases(), refreshInventory()]),
    [refreshProducts, refreshSuppliers, refreshPurchases, refreshInventory]
  )

  // load when a shop becomes available, clear everything on logout
  useEffect(() => {
    if (ready) {
      refreshAll()
    } else {
      setProducts(empty); setSuppliers(empty); setPurchases(empty); setInventory(empty)
    }
  }, [ready, refreshAll])

  const value = useMemo(
    () => ({
      products: products.data, productsLoading: products.loading, productsError: products.error,
      suppliers: suppliers.data, suppliersLoading: suppliers.loading, suppliersError: suppliers.error,
      purchases: purchases.data, purchasesLoading: purchases.loading,
      inventory: inventory.data, inventoryLoading: inventory.loading, inventoryError: inventory.error,
      refreshProducts, refreshSuppliers, refreshPurchases, refreshInventory, refreshAll,
    }),
    [products, suppliers, purchases, inventory, refreshProducts, refreshSuppliers, refreshPurchases, refreshInventory, refreshAll]
  )
  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>
}

export function useAppData() {
  const ctx = useContext(AppDataContext)
  if (!ctx) throw new Error('useAppData must be used inside <AppDataProvider>')
  return ctx
}
