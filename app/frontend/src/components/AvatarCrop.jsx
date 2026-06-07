import { useState, useCallback } from 'react'
import Cropper from 'react-easy-crop'

function getCroppedBlob(imageSrc, cropArea) {
  return new Promise((resolve) => {
    const img = document.createElement('img')
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const canvas = document.createElement('canvas')
      const size = 400
      canvas.width = size
      canvas.height = size
      const ctx = canvas.getContext('2d')
      ctx.drawImage(
        img,
        cropArea.x, cropArea.y, cropArea.width, cropArea.height,
        0, 0, size, size
      )
      canvas.toBlob((blob) => resolve(blob), 'image/png')
    }
    img.src = imageSrc
  })
}

export default function AvatarCrop({ imageSrc, onComplete, onCancel }) {
  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedArea, setCroppedArea] = useState(null)
  const [saving, setSaving] = useState(false)

  const onCropComplete = useCallback((_, croppedAreaPixels) => {
    setCroppedArea(croppedAreaPixels)
  }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!croppedArea || saving) return
    setSaving(true)
    const blob = await getCroppedBlob(imageSrc, croppedArea)
    if (blob) {
      await onComplete(blob)
    }
    setSaving(false)
  }

  return (
    <div style={s.overlay} onClick={e => e.stopPropagation()}>
      <div style={s.modal} onClick={e => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 12px' }}>Position photo</h3>
        <div style={s.cropContainer}>
          <Cropper
            image={imageSrc}
            crop={crop}
            zoom={zoom}
            aspect={1}
            cropShape="round"
            showGrid={false}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={onCropComplete}
          />
        </div>
        <input
          type="range" min={1} max={3} step={0.05} value={zoom}
          onChange={e => setZoom(Number(e.target.value))}
          style={{ width: '100%', marginTop: 12 }}
          aria-label="Zoom"
        />
        <div style={{ display: 'flex', gap: 12, marginTop: 16, justifyContent: 'flex-end' }}>
          <button type="button" onClick={onCancel} style={s.cancelBtn}>Cancel</button>
          <button type="button" onClick={handleSave} disabled={saving} style={s.saveBtn}>{saving ? 'Saving...' : 'Save'}</button>
        </div>
      </div>
    </div>
  )
}

const s = {
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  modal: { background: '#fff', borderRadius: 16, padding: 24, width: '90%', maxWidth: 420 },
  cropContainer: { position: 'relative', width: '100%', height: 300, borderRadius: 8, overflow: 'hidden', background: '#111' },
  cancelBtn: { padding: '10px 20px', background: '#eee', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14 },
  saveBtn: { padding: '10px 20px', background: '#2ecc71', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 },
}
