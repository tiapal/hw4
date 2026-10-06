import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type ProductDetail as Detail } from '../api/products'
import { useCart } from '../components/CartContext'
import { useSearch } from '../components/SearchContext'

const LOW_STOCK = 5

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const { search } = useSearch()
  const cart = useCart()
  const [justAdded, setJustAdded] = useState(false)
  const [product, setProduct] = useState<Detail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [size, setSize] = useState<string | null>(null)

  useEffect(() => {
    setProduct(null)
    setError(null)
    setSize(null)
    setJustAdded(false)
    fetchProduct(productId).then(setProduct).catch((e) => setError(e.message))
  }, [productId])

  if (error)
    return (
      <section className="section narrow">
        <p className="error">{error}</p>
        <Link to="/products">← Back to all products</Link>
      </section>
    )
  if (!product) return <section className="section"><p className="muted">Loading…</p></section>

  const selected = product.sizes.find((s) => s.size === size)
  // Everything below comes from the inventory table via the API, so nothing about stock is hardcoded here.
  const soldOutSelected = selected !== undefined && selected.quantity === 0
  const allSoldOut = product.sizes.every((s) => s.quantity === 0)
  const inStockSizes = product.sizes.filter((s) => s.quantity > 0).map((s) => s.size)
  const inCart = selected ? cart.quantityOf(product.product_id, selected.size) : 0
  const maxedOut = selected !== undefined && selected.quantity > 0 && inCart >= selected.quantity

  function addToCart() {
    if (!selected) return
    const added = cart.add(
      { product_id: product!.product_id, name: product!.name, size: selected.size, price: product!.price, image_url: product!.image_url },
      selected.quantity,
    )
    setJustAdded(added)
  }

  return (
    <section className="section">
      <Link to="/products" className="back">{search ? `← Back to “${search.query}” results` : '← All products'}</Link>
      <div className="detail">
        <div className="detail-img">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">
            {formatPrice(product.price)}
            {allSoldOut && <span className="sold-out-tag">SOLD OUT</span>}
          </p>
          <p>{product.description}</p>

          <h3>Colors</h3>
          <div className="chips">
            {product.colors.map((c) => <span className="chip" key={c}>{c}</span>)}
          </div>

          <h3>Sizes</h3>
          <div className="sizes">
            {product.sizes.map((s) => (
              <button
                key={s.size}
                className={`size ${s.quantity === 0 ? 'sold-out' : ''} ${size === s.size ? 'selected' : ''}`}
                aria-pressed={size === s.size}
                onClick={() => { setSize(s.size); setJustAdded(false) }}
                title={s.quantity === 0 ? 'Sold out' : `${s.quantity} in stock`}
              >
                {s.size}
              </button>
            ))}
          </div>
          <p className="stock-note" role="status">
            {soldOutSelected ? (
              <>
                <strong className="sold-out-text">SOLD OUT</strong>
                {` — ${selected.size} isn’t available right now.`}
                {inStockSizes.length > 0 ? ` Still in stock: ${inStockSizes.join(', ')}.` : ' Every size is sold out.'}
              </>
            ) : selected ? (
              selected.quantity <= LOW_STOCK
                ? `Only ${selected.quantity} left in ${selected.size}. Grab it fast!`
                : `${selected.quantity} in stock in ${selected.size}`
            ) : allSoldOut ? (
              <><strong className="sold-out-text">SOLD OUT</strong>{' — every size is gone for now.'}</>
            ) : (
              'Pick a size to check stock. Sizes with a dashed outline are sold out.'
            )}
          </p>

          <button
            className="btn add-btn"
            onClick={addToCart}
            disabled={!selected || soldOutSelected || maxedOut}
          >
            {!selected ? (allSoldOut ? 'Sold out' : 'Select a size') : soldOutSelected ? 'Sold out' : maxedOut ? 'All in your cart' : 'Add to cart'}
          </button>
          {justAdded && (
            <p className="added-note" role="status">
              Added to your cart ✓ <Link to="/cart">View cart</Link>
            </p>
          )}

          <div className="chips tags">
            {product.search_tags.map((t) => <span className="tag" key={t}>#{t}</span>)}
          </div>
        </div>
      </div>
    </section>
  )
}
