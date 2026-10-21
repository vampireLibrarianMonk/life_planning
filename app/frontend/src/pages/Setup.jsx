import { useState } from 'react'

/**
 * Account setup page — reached via the one-time link emailed to a new user:
 *   /setup?token=<token>
 * The user chooses their own password; the token is validated server-side and
 * consumed. No password is ever transmitted to the user; they set it here.
 */
export default function Setup() {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      const res = await fetch('/api/auth/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Could not set your password.')
      }
      setDone(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (!token) {
    return (
      <div style={{ maxWidth: 400, margin: '100px auto', padding: 24 }}>
        <h1>Life Plan Tracker</h1>
        <p style={{ color: '#c0392b' }}>
          This setup link is missing its token. Please use the full link from
          your invitation email.
        </p>
      </div>
    )
  }

  if (done) {
    return (
      <div style={{ maxWidth: 400, margin: '100px auto', padding: 24 }}>
        <h1>Life Plan Tracker</h1>
        <p>Your password has been set. You can now sign in.</p>
        <a href="/" style={{ color: '#2563b0' }}>Go to sign in →</a>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 400, margin: '100px auto', padding: 24 }}>
      <h1>Set your password</h1>
      <p style={{ color: '#5a6b7b', fontSize: 14 }}>
        Choose a password for your Life Plan Tracker account.
      </p>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 12 }}>
          <label htmlFor="password">New password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ display: 'block', width: '100%', padding: 8 }}
            autoComplete="new-password"
            minLength={8}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label htmlFor="confirm">Confirm password</label>
          <input
            id="confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            style={{ display: 'block', width: '100%', padding: 8 }}
            autoComplete="new-password"
            minLength={8}
          />
        </div>
        {error && <p style={{ color: '#c0392b' }}>{error}</p>}
        <button type="submit" disabled={busy} style={{ padding: '8px 24px' }}>
          {busy ? 'Setting…' : 'Set password'}
        </button>
      </form>
    </div>
  )
}
