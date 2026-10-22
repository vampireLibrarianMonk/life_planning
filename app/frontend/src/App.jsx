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
import { getToken, setToken as saveToken, isReadonly } from './services/auth'

export default function App() {
  const [token, setTokenState] = useState(getToken())
  const readonly = token ? isReadonly() : false

  const handleLogin = (t) => {
    saveToken(t)
    setTokenState(t)
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

  if (!token) {
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
