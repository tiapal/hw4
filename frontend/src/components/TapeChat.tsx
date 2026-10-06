import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, matchPath, useLocation, useNavigate } from 'react-router-dom'
import { fetchChatHistory, sendChat } from '../api/chat'
import { formatPrice, type Product } from '../api/products'
import { useAuth } from './AuthContext'
import { useSearch } from './SearchContext'

type Message = { role: 'user' | 'assistant'; content: string; products?: Product[]; error?: boolean }

const greeting = (firstName?: string): Message => ({
  role: 'assistant',
  content: `${firstName ? `Hi ${firstName}!` : 'Hi!'} I’m Inchy, your Campus Customs fit assistant. Ask me about sizes, colors, or what to wear to The Game.`,
})

export default function TapeChat() {
  const [open, setOpen] = useState(false)
  const { user, loading: authLoading } = useAuth()
  const [messages, setMessages] = useState<Message[]>([greeting()])
  const [draft, setDraft] = useState('')
  const [thinking, setThinking] = useState(false)
  const { setSearch } = useSearch()
  const navigate = useNavigate()
  const location = useLocation()
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const rollUpTimer = useRef<number | undefined>(undefined)

  // Whenever the logged-in person changes (log in, log out, someone else logs in), start from a clean chat:
  // a logged-in shopper gets their saved conversation back; a guest gets a fresh one.
  useEffect(() => {
    if (authLoading) return
    let stale = false
    setMessages([greeting(user?.first_name)])
    if (user) {
      fetchChatHistory().then((saved) => {
        if (stale || saved.length === 0) return
        setMessages([greeting(user.first_name), ...saved.map(({ role, content, products }) => ({ role, content, products }))])
      })
    }
    return () => { stale = true }
  }, [user?.id, authLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, thinking])

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 700)
  }, [open])

  async function send(e: FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text || thinking) return
    // Guests carry their conversation along (it is never stored); for logged-in shoppers the server has it.
    window.clearTimeout(rollUpTimer.current)
    const history = messages.slice(1).filter((m) => !m.error).map(({ role, content }) => ({ role, content }))
    setDraft('')
    setMessages((m) => [...m, { role: 'user', content: text }])
    setThinking(true)
    try {
      // Tell the server which page the shopper is on, so "this" can mean the open product.
      const productMatch = matchPath('/products/:productId', location.pathname)
      const page = { path: location.pathname, product_id: productMatch?.params.productId ?? null }
      const reply = await sendChat(text, user ? [] : history, page)
      // The agent searched the catalogue: put the matches on the Products page.
      if (reply.search) {
        setSearch(reply.search)
        if (location.pathname !== '/products') navigate('/products')
        // Give the shopper a moment to read the reply, then roll the chat up so the results aren't covered.
        rollUpTimer.current = window.setTimeout(() => setOpen(false), 2500)
      }
      setMessages((m) => [...m, { role: 'assistant', content: reply.message, products: reply.products }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', content: (err as Error).message, error: true }])
    } finally {
      setThinking(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className={`tape-widget ${open ? 'open' : ''}`}>
      <div className="tape-panel" aria-hidden={!open}>
        <div className="tape-ruler">
          <span>Inchy · fit assistant</span>
          <button className="tape-close" onClick={() => setOpen(false)} aria-label="Roll up chat" tabIndex={open ? 0 : -1}>
            ⟲
          </button>
        </div>
        <div className="tape-body">
          <div className="tape-messages" ref={listRef}>
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                <div className={`bubble ${m.role} ${m.error ? 'error-bubble' : ''}`}>{m.content}</div>
                {m.products && m.products.length > 0 && (
                  <div className="mini-cards">
                    {m.products.map((p) => (
                      <Link to={`/products/${p.product_id}`} className="mini-card" key={p.product_id} onClick={() => setOpen(false)}>
                        <img src={p.image_url} alt="" />
                        <span className="mini-name">{p.name}</span>
                        <span className="price">{formatPrice(p.price)}</span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {thinking && (
              <div className="msg assistant">
                <div className="bubble assistant typing" aria-label="Inchy is typing"><i /><i /><i /></div>
              </div>
            )}
          </div>
          <form className="tape-input" onSubmit={send}>
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask about sizes, colors…"
              tabIndex={open ? 0 : -1}
            />
            <button type="submit" className="btn" disabled={thinking} tabIndex={open ? 0 : -1}>Send</button>
          </form>
        </div>
      </div>

      <button
        className="tape-case"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? 'Roll up chat' : 'Unroll chat'}
      >
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <rect x="6" y="6" width="88" height="88" rx="26" fill="#ff4fa3" stroke="#0a0a0a" strokeWidth="4" />
          <circle cx="50" cy="50" r="28" fill="#0a0a0a" />
          <g className="tape-reel">
            <circle cx="50" cy="50" r="20" fill="none" stroke="#ff9fcf" strokeWidth="3" strokeDasharray="4 4" />
            <circle cx="50" cy="50" r="9" fill="#ff4fa3" />
            <text x="50" y="54" textAnchor="middle" fontSize="10" fontWeight="800" fill="#0a0a0a">CC</text>
          </g>
          <rect x="70" y="14" width="14" height="8" rx="3" fill="#0a0a0a" />
        </svg>
        {!open && <span className="tape-hint">Need a fit check?</span>}
      </button>
    </div>
  )
}
