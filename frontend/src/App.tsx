import { Route, Routes, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar'
import TapeChat from './components/TapeChat'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Cart from './pages/Cart'
import Login from './pages/Login'
import Signup from './pages/Signup'

export default function App() {
  const location = useLocation()
  return (
    <>
      <NavBar />
      <main>
        {/* keyed by path: each new page replays the blur-in animation (.page in index.css) */}
        <div className="page" key={location.pathname}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="*" element={<Home />} />
        </Routes>
        </div>
      </main>
      <footer className="footer">
        Campus Customs · 57 Broadway, New Haven, CT · Officially licensed Yale merch
      </footer>
      <TapeChat />
    </>
  )
}
