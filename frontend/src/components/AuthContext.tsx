import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import * as api from '../api/auth'
import type { User } from '../api/auth'

type AuthState = {
  user: User | null
  loading: boolean
  setUser: (u: User | null) => void
  logOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Ask the server who we are (the session cookie is sent automatically).
  useEffect(() => {
    api.fetchMe().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false))
  }, [])

  async function logOut() {
    await api.logout().catch(() => {})
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, setUser, logOut }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
