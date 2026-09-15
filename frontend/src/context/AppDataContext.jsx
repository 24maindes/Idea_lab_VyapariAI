import { createContext, useContext, useMemo, useState } from 'react'
import {
  initialSuppliers,
  initialInventory,
  initialPurchases,
  productList,
} from '../data/mockData.js'

const AppDataContext = createContext(null)

let supplierSeq = initialSuppliers.length + 1
let purchaseSeq = initialPurchases.length + 1

export function AppDataProvider({ children }) {
  const [suppliers, setSuppliers] = useState(initialSuppliers)
  const [inventory, setInventory] = useState(initialInventory)
  const [purchases, setPurchases] = useState(initialPurchases)

  const addSupplier = (supplier) => {
    const newSupplier = {
      id: `SUP-${String(supplierSeq++).padStart(3, '0')}`,
      productsSupplied: [],
      ...supplier,
    }
    setSuppliers((prev) => [newSupplier, ...prev])
    return newSupplier
  }

  // Recording a purchase also increases the matching inventory quantity,
  // so the Supplier -> Purchase -> Inventory flow feels connected in the demo.
  const addPurchase = (purchase) => {
    const newPurchase = {
      id: `PO-${1000 + purchaseSeq++}`,
      ...purchase,
    }
    setPurchases((prev) => [newPurchase, ...prev])

    setInventory((prev) => {
      const existingIndex = prev.findIndex((item) => item.product === purchase.product)
      if (existingIndex === -1) {
        const productMeta = productList.find((p) => p.name === purchase.product)
        return [
          {
            id: productMeta?.id ?? `PRD-${prev.length + 1}`,
            product: purchase.product,
            category: productMeta?.category ?? 'General',
            unit: productMeta?.unit ?? 'unit',
            quantity: Number(purchase.quantity) || 0,
            lowStockThreshold: 20,
          },
          ...prev,
        ]
      }
      return prev.map((item, index) =>
        index === existingIndex
          ? { ...item, quantity: item.quantity + (Number(purchase.quantity) || 0) }
          : item
      )
    })

    return newPurchase
  }

  const value = useMemo(
    () => ({
      suppliers,
      addSupplier,
      inventory,
      purchases,
      addPurchase,
      products: productList,
    }),
    [suppliers, inventory, purchases]
  )

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>
}

export function useAppData() {
  const ctx = useContext(AppDataContext)
  if (!ctx) throw new Error('useAppData must be used within AppDataProvider')
  return ctx
}
