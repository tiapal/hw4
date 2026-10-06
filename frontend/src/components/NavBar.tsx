import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { useCart } from './CartContext'

type NavItem = { to: string; label: string; cta?: boolean }

const baseLinks: NavItem[] = [
  { to: '/', label: 'Home' },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]
const guestLinks: NavItem[] = [
  { to: '/login', label: 'Log In' },
  { to: '/signup', label: 'Create Account', cta: true },
]

export default function NavBar() {
  const { user, loading, logOut } = useAuth()
  const { count } = useCart()
  const navigate = useNavigate()
  const cartLink: NavItem = { to: '/cart', label: count > 0 ? `Cart (${count})` : 'Cart' }
  const links = user ? [...baseLinks, cartLink] : [...baseLinks, cartLink, ...(loading ? [] : guestLinks)]

  return (
    <header className="nav">
      <NavLink to="/" className="brand">
        Campus<span>Customs</span>
      </NavLink>
      <nav>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            className={({ isActive }) =>
              ['nav-link', l.cta && 'cta', isActive && 'active'].filter(Boolean).join(' ')
            }
          >
            {l.label}
          </NavLink>
        ))}
        {user && (
          <>
            <span className="nav-user">Hi, {user.first_name}</span>
            <button className="nav-link cta" onClick={async () => { await logOut(); navigate('/') }}>
              Log Out
            </button>
          </>
        )}
      </nav>
    </header>
  )
}
