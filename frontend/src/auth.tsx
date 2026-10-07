import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

export type User = { id: number; first_name: string; last_name: string; name: string; email: string }
type Session = { token: string; user: User }

type AuthValue = {
  user: User | null
  token: string | null
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (data: SignupData) => Promise<void>
  logout: () => void
}

export type SignupData = {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

const TOKEN_KEY = 'cc_token'
const AuthContext = createContext<AuthValue | null>(null)

function readToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
function writeToken(token: string | null) {
  try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ }
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      const d = body.detail[0]
      const field = d.loc?.[d.loc.length - 1]
      const msg = String(d.msg).replace(/^Value error, /, '')
      return field && field !== 'body' ? `${String(field).replace('_', ' ')}: ${msg}` : msg
    }
  } catch { /* fall through */ }
  return `Request failed (${res.status})`
}

async function postSession(url: string, payload: unknown): Promise<Session> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await errorMessage(res))
  return res.json()
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(readToken)
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!token) { setReady(true); return }
    fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => setUser(d.user))
      .catch(() => { writeToken(null); setToken(null) })
      .finally(() => setReady(true))
  }, [token])

  const start = (s: Session) => { writeToken(s.token); setToken(s.token); setUser(s.user) }
  const login = useCallback(async (email: string, password: string) => start(await postSession('/api/auth/login', { email, password })), [])
  const signup = useCallback(async (data: SignupData) => start(await postSession('/api/auth/signup', data)), [])
  const logout = useCallback(() => { writeToken(null); setToken(null); setUser(null) }, [])

  return <AuthContext.Provider value={{ user, token, ready, login, signup, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
