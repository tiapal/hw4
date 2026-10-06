import { Link } from 'react-router-dom'
import { formatPrice } from '../api/products'
import { useCart } from '../components/CartContext'

export default function Cart() {
  const { items, remove } = useCart()
  const subtotal = items.reduce((sum, i) => sum + i.price * i.quantity, 0)

  return (
    <section className="section narrow">
      <p className="eyebrow">Your cart</p>
      <h1>Cart</h1>
      {items.length === 0 ? (
        <p className="muted">Your cart is empty. <Link to="/products">Browse the collection</Link></p>
      ) : (
        <>
          <ul className="cart-list">
            {items.map((i) => (
              <li key={`${i.product_id}-${i.size}`} className="cart-row">
                <img src={i.image_url} alt="" />
                <div className="cart-info">
                  <Link to={`/products/${i.product_id}`}>{i.name}</Link>
                  <span className="muted">Size {i.size} · Qty {i.quantity}</span>
                </div>
                <span className="price">{formatPrice(i.price * i.quantity)}</span>
                <button className="btn ghost small" onClick={() => remove(i.product_id, i.size)}>Remove</button>
              </li>
            ))}
          </ul>
          <p className="cart-total">Subtotal <strong>{formatPrice(subtotal)}</strong></p>
          <p className="muted">Checkout isn’t built yet. This cart is saved in your browser.</p>
        </>
      )}
    </section>
  )
}
