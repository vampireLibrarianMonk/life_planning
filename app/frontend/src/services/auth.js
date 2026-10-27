// Auth now relies on an httpOnly cookie (set by the backend on login) rather
// than a JS-readable token. The cookie is sent automatically on same-origin
// requests via `credentials: 'include'`. We no longer store or read the JWT in
// JS, so XSS cannot exfiltrate it. Role/identity for UI hints comes from /me.

let _claims = null // { id, username, role } cached from /api/auth/me

export async function login(username, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) throw new Error('Login failed')
  // Body still contains the token for API clients, but the SPA ignores it and
  // relies on the cookie. Prime the identity cache from /me.
  await res.json().catch(() => ({}))
  await refreshClaims()
  return true
}

export async function logout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
  } finally {
    _claims = null
  }
}

/** Fetch + cache the current user (role/identity) from the backend. */
export async function refreshClaims() {
  try {
    const res = await fetch('/api/auth/me', { credentials: 'include' })
    if (!res.ok) {
      _claims = null
      return null
    }
    _claims = await res.json()
    return _claims
  } catch {
    _claims = null
    return null
  }
}

/** Is there a live session? Resolves via /me (cookie-backed). */
export async function isAuthenticated() {
  if (_claims) return true
  return (await refreshClaims()) != null
}

export function getClaims() {
  return _claims
}

export function getRole() {
  return _claims?.role || null
}

export function isReadonly() {
  return getRole() === 'readonly'
}

export function isAdmin() {
  return getRole() === 'admin'
}

export function isChild() {
  return getRole() === 'child'
}

/**
 * Build a URL for a stored upload. The blob-serving route is authorized by the
 * httpOnly auth cookie, which <img>/<video>/<a> tags send automatically — so
 * the token no longer needs to appear in the URL.
 */
export function uploadUrl(filename) {
  if (!filename) return ''
  return `/api/uploads/${filename}`
}
