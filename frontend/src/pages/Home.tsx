import { Link } from 'react-router-dom'

const categories = [
  { name: 'Tees', blurb: 'Soft, everyday shirts for lecture, the dining hall, and everything after.', price: 'from $32' },
  { name: 'Hoodies', blurb: 'The heavyweight layer you’ll live in from October to May.', price: 'from $68' },
  { name: 'Crewnecks', blurb: 'Clean wordmarks and team logos on a timeless cut.', price: 'from $58' },
  { name: 'Quarter-Zips & Jackets', blurb: 'Polished enough for a career fair, warm enough for a Harvard game.', price: 'from $72' },
]

export default function Home() {
  return (
    <>
      <section className="hero">
        <p className="eyebrow">Officially licensed · New Haven, CT</p>
        <h1>
          Wear your <span className="accent">Bulldog</span> pride.
        </h1>
        <p className="lead">
          Campus Customs makes the Yale gear you actually reach for, from game-day tees to the
          hoodie you’ll still be wearing at your tenth reunion.
        </p>
        <div className="hero-actions">
          <Link to="/products" className="btn">Shop the collection</Link>
          <Link to="/about" className="btn ghost">Our story</Link>
        </div>
      </section>

      <section className="section">
        <h2>Shop by vibe</h2>
        <div className="grid">
          {categories.map((c) => (
            <Link to="/products" className="card" key={c.name}>
              <h3>{c.name}</h3>
              <p>{c.blurb}</p>
              <span className="price">{c.price}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="section band">
        <h2>Not sure what fits?</h2>
        <p>
          Our shopping assistant knows every product, color, and size we carry. Ask it if that
          crewneck comes in XL or what to wear to The Game. It’ll give you a straight answer.
        </p>
      </section>
    </>
  )
}
