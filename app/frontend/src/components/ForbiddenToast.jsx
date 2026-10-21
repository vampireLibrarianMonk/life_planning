import { useEffect, useState } from 'react'

/**
 * Listens for the global `api-forbidden` event (dispatched by the api.js 403
 * interceptor) and shows a brief, friendly toast. This catches the rare case
 * where a write slips through the hidden UI (e.g. a stale token or a readonly
 * account), instead of failing silently or throwing a raw error.
 */
export default function ForbiddenToast() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    let timer
    const onForbidden = () => {
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
      👁️ Read-only mode — that change wasn’t saved.
    </div>
  )
}
