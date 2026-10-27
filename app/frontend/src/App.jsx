import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import Setup from './pages/Setup'
import Demo from './pages/Demo'
import RegionFailoverBanner from './components/RegionFailoverBanner'
import ReadOnlyBanner from './components/ReadOnlyBanner'
import ForbiddenToast from './components/ForbiddenToast'
import { refreshClaims, getClaims, isReadonly } from './services/auth'

export default function App() {
  // null = still checking the cookie session; false = not logged in; true = in.
  const [authed, setAuthed] = useState(null)
  const readonly = authed ? isReadonly() : false

  // Bootstrap: ask the backend who we are (cookie-backed). No token in JS.
  useEffect(() => {
    let alive = true
    const path = window.location.pathname
    if (path === '/setup' || path === '/demo') {
      setAuthed(false)
      return
    }
    refreshClaims().then((claims) => {
      if (alive) setAuthed(claims != null)
    })
    return () => { alive = false }
  }, [])

  const handleLogin = async () => {
    await refreshClaims()
    setAuthed(getClaims() != null)
  }

  // Expose the role to CSS so write controls can be disabled globally.
  useEffect(() => {
    if (readonly) document.documentElement.setAttribute('data-role', 'readonly')
    else document.documentElement.removeAttribute('data-role')
  }, [readonly])

  // The setup page is reachable WITHOUT a login (new users have no password yet).
  if (window.location.pathname === '/setup') {
    return (
      <>
        <RegionFailoverBanner />
        <Setup />
      </>
    )
  }

  // The demo page is a public, no-login app demonstrator (fake data only).
  if (window.location.pathname === '/demo') {
    return (
      <>
        <RegionFailoverBanner />
        <Demo />
      </>
    )
  }

  // Still resolving the session — avoid flashing the login screen.
  if (authed === null) {
    return <RegionFailoverBanner />
  }

  if (!authed) {
    return (
      <>
        <RegionFailoverBanner />
        <Login onLogin={handleLogin} />
      </>
    )
  }

  return (
    <>
      <RegionFailoverBanner />
      {readonly && <ReadOnlyBanner />}
      <ForbiddenToast />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/profile/:id" element={<Profile />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </>
  )
}
