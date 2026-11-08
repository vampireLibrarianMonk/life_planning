import { useEffect, useState } from 'react'
import { isReadonly } from '../services/auth'

/**
 * Listens for the global `api-forbidden` event (dispatched by the api.js 403
 * interceptor) and shows a brief, friendly toast. The wording depends on the
 * actual role: a real readonly user is told it's read-only; any other 403
 * (e.g. an expired session) gets an accurate "sign in again" message instead
 * of a misleading "read-only" claim.
 */
export default function ForbiddenToast() {
  const [visible, setVisible] = useState(false)
  const [readonly, setReadonly] = useState(false)

  useEffect(() => {
    let timer
    const onForbidden = () => {
      setReadonly(isReadonly())
      setVisible(true)
      clearTimeout(timer)
      timer = setTimeout(() => setVisible(false), 4000)
    }
    window.addEventListener('api-forbidden', onForbidden)
    return () => {
      window.removeEventListener('api-forbidden', onForbidden)
      clearTimeout(timer)
    }
  }, [])

  if (!visible) return null

  const message = readonly
    ? '👁️ Read-only mode — that change wasn’t saved.'
    : '⚠️ That action was blocked. Your session may have expired — try signing in again.'

  return (
    <div
      role="status"
      style={{
        position: 'fixed',
        bottom: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        background: '#5c4a00',
        color: '#fff',
        padding: '10px 18px',
        borderRadius: 8,
        fontSize: 14,
        boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
        maxWidth: '90vw',
        textAlign: 'center',
      }}
    >
      {message}
    </div>
  )
}
