// Shared mock data for Member 2 screens (Suppliers, Purchases, Inventory).
// In the full app this will be replaced by API/DB data from other modules.

export const initialSuppliers = [
  {
    id: 'SUP-001',
    name: 'ABC Traders',
    contact: '+91 98765 43210',
    address: 'Shop 14, Itwari Market, Nagpur',
    productsSupplied: ['Rice', 'Wheat', 'Sugar'],
  },
  {
    id: 'SUP-002',
    name: 'Sharma Foods',
    contact: '+91 91234 56789',
    address: 'Plot 22, Kalamna Market, Nagpur',
    productsSupplied: ['Oil', 'Tea', 'Sugar'],
  },
  {
    id: 'SUP-003',
    name: 'XYZ Wholesale',
    contact: '+91 90909 80808',
    address: 'MG Road, Sitabuldi, Nagpur',
    productsSupplied: ['Rice', 'Wheat'],
  },
  {
    id: 'SUP-004',
    name: 'GoodFood Co.',
    contact: '+91 88990 11223',
    address: 'Wardha Road, Nagpur',
    productsSupplied: ['Tea', 'Oil'],
  },
]

// Products list kept in sync with the sample inventory below, so dropdowns
// stay realistic without needing Member 1's Product module yet.
export const productList = [
  { id: 'PRD-001', name: 'Rice', category: 'Grains', unit: 'kg' },
  { id: 'PRD-002', name: 'Wheat', category: 'Grains', unit: 'kg' },
  { id: 'PRD-003', name: 'Sugar', category: 'Grocery', unit: 'kg' },
  { id: 'PRD-004', name: 'Oil', category: 'Edible Oil', unit: 'L' },
  { id: 'PRD-005', name: 'Tea', category: 'Beverages', unit: 'pack' },
]

export const initialInventory = [
  { id: 'PRD-001', product: 'Rice', category: 'Grains', unit: 'kg', quantity: 50, lowStockThreshold: 20 },
  { id: 'PRD-002', product: 'Wheat', category: 'Grains', unit: 'kg', quantity: 30, lowStockThreshold: 20 },
  { id: 'PRD-003', product: 'Sugar', category: 'Grocery', unit: 'kg', quantity: 40, lowStockThreshold: 20 },
  { id: 'PRD-004', product: 'Oil', category: 'Edible Oil', unit: 'L', quantity: 20, lowStockThreshold: 20 },
  { id: 'PRD-005', product: 'Tea', category: 'Beverages', unit: 'pack', quantity: 15, lowStockThreshold: 20 },
]

export const initialPurchases = [
  { id: 'PO-1001', product: 'Rice', supplier: 'ABC Traders', quantity: 25, price: 1450, date: '2026-09-02' },
  { id: 'PO-1002', product: 'Oil', supplier: 'Sharma Foods', quantity: 10, price: 1650, date: '2026-09-05' },
  { id: 'PO-1003', product: 'Tea', supplier: 'GoodFood Co.', quantity: 8, price: 960, date: '2026-09-08' },
]

export function getStockStatus(quantity, lowStockThreshold = 20) {
  if (quantity <= 0) return 'Out of Stock'
  if (quantity <= lowStockThreshold) return 'Low Stock'
  return 'In Stock'
}
