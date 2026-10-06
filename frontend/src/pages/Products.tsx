import { useEffect, useState } from 'react'
import { fetchProducts, type Product } from '../api/products'
import ProductGrid from '../components/ProductGrid'
import { useSearch } from '../components/SearchContext'

export default function Products() {
  const { search, setSearch } = useSearch()
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchProducts().then(setProducts).catch((e) => setError(e.message))
  }, [])

  // Chat results replace the full list until the shopper clears them.
  if (search) {
    return (
      <section className="section">
        <p className="eyebrow">From your chat</p>
        <h1>Results for “{search.query}”</h1>
        <div className="results-bar">
          <span className="muted">
            {search.total > search.products.length
              ? `Showing ${search.products.length} of ${search.total} matches`
              : `${search.total} ${search.total === 1 ? 'match' : 'matches'}`}
          </span>
          <button className="btn ghost small" onClick={() => setSearch(null)}>Show all products</button>
        </div>
        <ProductGrid products={search.products} highlight />
      </section>
    )
  }

  return (
    <section className="section">
      <p className="eyebrow">Products</p>
      <h1>The collection</h1>
      {error && <p className="error">Couldn’t load products: {error}. Is the backend running?</p>}
      {!products && !error && <p className="muted">Loading the racks…</p>}
      {products && (
        <>
          <p className="muted">{products.length} pieces of Bulldog gear. Or ask Inchy in the chat to find something.</p>
          <ProductGrid products={products} />
        </>
      )}
    </section>
  )
}
