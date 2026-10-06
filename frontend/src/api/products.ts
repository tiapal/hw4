export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  price: number
  image_url: string
  in_stock?: boolean
}

export type SizeStock = { size: string; quantity: number }
export type ProductDetail = Product & { sizes: SizeStock[] }

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(res.status === 404 ? 'Product not found' : `Request failed (${res.status})`)
  return res.json()
}

export const fetchProducts = () => getJson<Product[]>('/api/products')
export const fetchProduct = (id: string) => getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)

export const formatPrice = (p: number) => `$${p.toFixed(0)}`
