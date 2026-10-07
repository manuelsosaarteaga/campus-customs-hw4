import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth, type SignupData } from '../auth'

const EMPTY: SignupData = { first_name: '', last_name: '', email: '', password: '', confirm_password: '' }

export default function Signup() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<SignupData>(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  const set = (key: keyof SignupData) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password.length < 8) return setError('Password must be at least 8 characters.')
    if (form.password !== form.confirm_password) return setError('Passwords do not match.')
    setBusy(true)
    try {
      await signup({ ...form, email: form.email.trim() })
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-wrap">
      <div className="auth-card reveal in">
      <h1>Create account</h1>
      <p className="muted">Join the Campus Customs community.</p>
      <form className="form" onSubmit={submit}>
        <div className="form-row">
          <label>First name<input required autoComplete="given-name" value={form.first_name} onChange={set('first_name')} /></label>
          <label>Last name<input required autoComplete="family-name" value={form.last_name} onChange={set('last_name')} /></label>
        </div>
        <label>Email<input type="email" required autoComplete="email" value={form.email} onChange={set('email')} /></label>
        <label>Password<input type="password" required minLength={8} autoComplete="new-password" value={form.password} onChange={set('password')} /></label>
        <label>Confirm password<input type="password" required autoComplete="new-password" value={form.confirm_password} onChange={set('confirm_password')} /></label>
        <p className="muted small">At least 8 characters.</p>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="btn primary" type="submit" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</button>
      </form>
      <p className="muted">Already have one? <Link to="/login">Log in</Link></p>
      </div>
    </section>
  )
}
