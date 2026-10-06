import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type CartItem = {
  product_id: string
  name: string
  size: string
  price: number
  image_url: string
  quantity: number
}

type CartState = {
  items: CartItem[]
  count: number
  quantityOf: (productId: string, size: string) => number
  // Adds one. `inStock` is the stock for that size from the database; sold-out sizes (0) are never added.
  add: (item: Omit<CartItem, 'quantity'>, inStock: number) => boolean
  remove: (productId: string, size: string) => void
}

const CartContext = createContext<CartState | null>(null)
const STORAGE_KEY = 'cc_cart'

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    } catch {
      return []
    }
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }, [items])

  const quantityOf = (productId: string, size: string) =>
    items.find((i) => i.product_id === productId && i.size === size)?.quantity ?? 0

  function add(item: Omit<CartItem, 'quantity'>, inStock: number) {
    if (inStock <= 0 || quantityOf(item.product_id, item.size) >= inStock) return false // sold out, or all of them already in the cart
    setItems((prev) => {
      const existing = prev.find((i) => i.product_id === item.product_id && i.size === item.size)
      return existing
        ? prev.map((i) => (i === existing ? { ...i, quantity: i.quantity + 1 } : i))
        : [...prev, { ...item, quantity: 1 }]
    })
    return true
  }

  const remove = (productId: string, size: string) =>
    setItems((prev) => prev.filter((i) => !(i.product_id === productId && i.size === size)))

  const count = items.reduce((n, i) => n + i.quantity, 0)
  return <CartContext.Provider value={{ items, count, quantityOf, add, remove }}>{children}</CartContext.Provider>
}

export function useCart() {
  const ctx = useContext(CartContext)
  if (!ctx) throw new Error('useCart must be used inside <CartProvider>')
  return ctx
}
