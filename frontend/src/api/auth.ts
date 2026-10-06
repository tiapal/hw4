export type User = {
  id: number
  first_name: string
  last_name: string
  email: string
  residential_college: string | null
}

export type AffiliationOptions = {
  residential_colleges: string[]
  graduate_schools: string[]
}

export type SignupInput = {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
  residential_college: string
}

// FastAPI returns either {detail: "message"} or {detail: [{loc, msg}, ...]} for validation errors.
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = data.detail
    const message = Array.isArray(d)
      ? d.map((e: { msg: string }) => e.msg.replace(/^Value error, /, '')).join(' ')
      : d || `Request failed (${res.status})`
    throw new Error(message)
  }
  return data as T
}

export const fetchOptions = () => request<AffiliationOptions>('/api/auth/options')
export const fetchMe = () => request<{ user: User | null }>('/api/auth/me').then((r) => r.user)
export const signup = (body: SignupInput) =>
  request<{ user: User }>('/api/auth/signup', { method: 'POST', body: JSON.stringify(body) }).then((r) => r.user)
export const login = (email: string, password: string) =>
  request<{ user: User }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }).then((r) => r.user)
export const logout = () => request<void>('/api/auth/logout', { method: 'POST' })
