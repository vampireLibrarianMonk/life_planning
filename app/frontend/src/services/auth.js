const TOKEN_KEY = 'life_plan_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export async function login(username, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) throw new Error('Login failed')
  const data = await res.json()
  setToken(data.access_token)
  return data.access_token
}

/** Decode the JWT payload (unverified — for UI hints only; the backend enforces). */
export function getClaims() {
  const t = getToken()
  if (!t) return null
  try {
    const payload = t.split('.')[1]
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(json)
  } catch {
    return null
  }
}

export function getRole() {
  return getClaims()?.role || null
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
