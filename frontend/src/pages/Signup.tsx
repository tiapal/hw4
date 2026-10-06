import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchOptions, signup, type AffiliationOptions } from '../api/auth'
import { useAuth } from '../components/AuthContext'

export default function Signup() {
  const { setUser } = useAuth()
  const navigate = useNavigate()
  const [options, setOptions] = useState<AffiliationOptions | null>(null)
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', password: '', confirm_password: '', residential_college: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetchOptions().then(setOptions).catch(() => setError('Couldn’t load the college list. Is the backend running?'))
  }, [])

  const set = (field: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [field]: e.target.value }))

  const mismatch = form.confirm_password !== '' && form.password !== form.confirm_password

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (form.password !== form.confirm_password) return setError('Passwords don’t match')
    setBusy(true)
    try {
      setUser(await signup(form))
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="section form-wrap">
      <form className="auth-form" onSubmit={onSubmit}>
        <h1>Join Campus Customs</h1>
        <div className="row">
          <label>
            First name
            <input autoComplete="given-name" required maxLength={50} value={form.first_name} onChange={set('first_name')} />
          </label>
          <label>
            Last name
            <input autoComplete="family-name" required maxLength={50} value={form.last_name} onChange={set('last_name')} />
          </label>
        </div>
        <label>
          Email
          <input type="email" autoComplete="email" placeholder="you@yale.edu" required
            value={form.email} onChange={set('email')} />
        </label>
        <label>
          Password
          <input type="password" autoComplete="new-password" minLength={8} maxLength={128} required
            value={form.password} onChange={set('password')} />
          <small className="muted">At least 8 characters</small>
        </label>
        <label>
          Confirm password
          <input type="password" autoComplete="new-password" required aria-invalid={mismatch}
            className={mismatch ? 'invalid' : ''} value={form.confirm_password} onChange={set('confirm_password')} />
          {mismatch && <small className="error">Passwords don’t match</small>}
        </label>
        <label>
          Residential college or graduate school
          <select required value={form.residential_college} onChange={set('residential_college')}>
            <option value="" disabled>Choose one…</option>
            {options && (
              <>
                <optgroup label="Residential colleges">
                  {options.residential_colleges.map((c) => <option key={c} value={c}>{c}</option>)}
                </optgroup>
                <optgroup label="Graduate &amp; professional schools">
                  {options.graduate_schools.map((s) => <option key={s} value={s}>{s}</option>)}
                </optgroup>
              </>
            )}
          </select>
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn" type="submit" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
        <p className="muted">
          Already have one? <Link to="/login">Log in</Link>
        </p>
      </form>
    </section>
  )
}
