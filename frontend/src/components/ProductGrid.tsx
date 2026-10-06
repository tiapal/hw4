import { Link } from 'react-router-dom'
import { formatPrice, type Product } from '../api/products'

// Clicking a card opens that product's detail page (/products/:id).
export default function ProductGrid({ products, highlight = false }: { products: Product[]; highlight?: boolean }) {
  return (
    <div className={`product-grid ${highlight ? 'highlight' : ''}`}>
      {products.map((p, i) => (
        <Link
          to={`/products/${p.product_id}`}
          className="product-card"
          key={p.product_id}
          style={highlight ? { animationDelay: `${Math.min(i, 12) * 40}ms` } : undefined}
        >
          <div className="product-img">
            <img src={p.image_url} alt={p.name} loading="lazy" />
            {p.in_stock === false && <span className="badge">Sold out</span>}
          </div>
          <div className="product-info">
            <h3>{p.name}</h3>
            <p className="clamp">{p.description}</p>
            <span className="price">{formatPrice(p.price)}</span>
          </div>
        </Link>
      ))}
    </div>
  )
}
