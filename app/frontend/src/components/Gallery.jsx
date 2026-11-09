import { useEffect, useRef, useState } from 'react'
import {
  fetchGallery,
  smartUploadGalleryMedia,
  updateGalleryMedia,
  deleteGalleryMedia,
} from '../services/api'

/**
 * Gallery — the child's canonical, private media store (Pass 2).
 *
 * A peer section of Age Groups / SMS / Email. Media lives independently of any
 * objective: the backend guarantees it survives age-group / objective removal.
 * Read-only users see media but get no upload/edit/delete controls (canWrite).
 */
const MEDIA_FILTERS = [
  { key: '', label: 'All' },
  { key: 'photo', label: 'Photos' },
  { key: 'video', label: 'Videos' },
  { key: 'document', label: 'Docs' },
]

function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString()
}

export default function Gallery({ profileId, profileName, onBack, canWrite }) {
  const [items, setItems] = useState(null)
  const [mediaType, setMediaType] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null) // media id being edited
  const [draftObs, setDraftObs] = useState('')
  const fileRef = useRef(null)

  const load = () =>
    fetchGallery(profileId, { mediaType: mediaType || undefined }).then((d) =>
      setItems(Array.isArray(d) ? d : []),
    )

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId, mediaType])

  async function onFiles(e) {
    const files = Array.from(e.target.files || [])
    if (!files.length) return
    setBusy(true)
    setError('')
    try {
      await smartUploadGalleryMedia(profileId, files)
      await load()
    } catch (err) {
      setError(err.message || 'Upload failed')
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function saveObservation(id) {
    await updateGalleryMedia(profileId, id, { observation: draftObs })
    setEditing(null)
    setDraftObs('')
    await load()
  }

  async function remove(id) {
    if (!confirm('Delete this item from the gallery? This cannot be undone.')) return
    await deleteGalleryMedia(profileId, id)
    await load()
  }

  return (
    <div style={s.container}>
      <button className="back-btn" onClick={onBack} style={s.back}>
        &larr; Back to Dashboard
      </button>
      <div style={s.header}>
        <span style={{ fontSize: 30 }} aria-hidden="true">
          🖼️
        </span>
        <div>
          <h2 style={{ margin: 0 }}>Gallery</h2>
          <p style={{ margin: '2px 0 0', fontSize: 13, color: '#595959' }}>
            {profileName} · photos &amp; videos
          </p>
        </div>
      </div>

      <div style={s.toolbar}>
        <div className="gallery-filters" style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {MEDIA_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setMediaType(f.key)}
              style={{ ...s.filter, ...(mediaType === f.key ? s.filterOn : {}) }}
            >
              {f.label}
            </button>
          ))}
        </div>
        {canWrite && (
          <label className="write-action" style={s.uploadBtn}>
            {busy ? 'Uploading…' : '+ Add media'}
            <input
              ref={fileRef}
              type="file"
              accept="image/*,video/*"
              multiple
              onChange={onFiles}
              disabled={busy}
              style={{ display: 'none' }}
            />
          </label>
        )}
      </div>

      {error && <p style={s.error}>{error}</p>}
      {items === null && <p style={{ color: '#595959' }}>Loading…</p>}
      {items !== null && items.length === 0 && (
        <div style={s.empty}>
          <p style={{ margin: 0, color: '#595959' }}>No media yet.</p>
          {canWrite && (
            <p style={{ margin: '6px 0 0', fontSize: 13, color: '#595959' }}>
              Use “+ Add media” to capture or upload a photo or video.
            </p>
          )}
        </div>
      )}

      {items && items.length > 0 && (
        <div className="gallery-grid" style={s.grid}>
          {items.map((m) => (
            <figure key={m.id} style={s.tile}>
              {m.media_type === 'video' ? (
                <video src={m.url} controls preload="metadata" style={s.media} />
              ) : m.media_type === 'photo' ? (
                <img src={m.url} alt={m.observation || m.original_name} style={s.media} />
              ) : (
                <a href={m.url} target="_blank" rel="noopener noreferrer" style={s.docTile}>
                  📄 {m.original_name}
                </a>
              )}
              <figcaption style={s.cap}>
                {editing === m.id ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <textarea
                      value={draftObs}
                      onChange={(e) => setDraftObs(e.target.value)}
                      rows={2}
                      style={s.input}
                      placeholder="Observation…"
                    />
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button onClick={() => saveObservation(m.id)} style={s.smallBtn}>
                        Save
                      </button>
                      <button onClick={() => setEditing(null)} style={s.smallGray}>
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    {m.observation && <p style={s.obs}>{m.observation}</p>}
                    <div style={s.metaRow}>
                      <span style={s.date}>{fmtDate(m.taken_at || m.created_at)}</span>
                      {canWrite && (
                        <span style={{ display: 'flex', gap: 2 }}>
                          <button
                            className="tap-target"
                            title="Edit observation"
                            onClick={() => {
                              setEditing(m.id)
                              setDraftObs(m.observation || '')
                            }}
                            style={s.iconBtn}
                          >
                            ✎
                          </button>
                          <button
                            className="tap-target"
                            title="Delete"
                            onClick={() => remove(m.id)}
                            style={{ ...s.iconBtn, color: '#c0392b' }}
                          >
                            ×
                          </button>
                        </span>
                      )}
                    </div>
                  </>
                )}
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </div>
  )
}

const s = {
  container: { maxWidth: 820, margin: '0 auto', padding: '8px 16px 48px' },
  back: { background: 'none', border: 'none', color: '#2563b0', cursor: 'pointer', fontSize: 14, padding: '6px 0' },
  header: { display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0 10px' },
  toolbar: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 12 },
  filter: { fontSize: 13, padding: '6px 12px', borderRadius: 14, border: '1px solid #cdd4dc', background: '#fff', color: '#333', cursor: 'pointer' },
  filterOn: { background: '#2563b0', borderColor: '#2563b0', color: '#fff', fontWeight: 600 },
  uploadBtn: { fontSize: 14, fontWeight: 600, padding: '8px 16px', background: '#15803d', color: '#fff', borderRadius: 8, cursor: 'pointer' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(220px, 100%), 1fr))', gap: 12 },
  tile: { margin: 0, background: '#fff', border: '1px solid #e8e8e8', borderRadius: 10, overflow: 'hidden', display: 'flex', flexDirection: 'column' },
  media: { width: '100%', height: 180, objectFit: 'cover', background: '#f3f3f3', display: 'block' },
  docTile: { padding: 24, textAlign: 'center', color: '#2563b0', textDecoration: 'none', fontSize: 14, wordBreak: 'break-word' },
  cap: { padding: '8px 10px' },
  obs: { margin: '0 0 6px', fontSize: 13, color: '#1a1a1a', wordBreak: 'break-word' },
  metaRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  date: { fontSize: 12, color: '#595959' },
  iconBtn: { background: 'none', border: 'none', cursor: 'pointer', fontSize: 15, color: '#595959' },
  input: { padding: '7px 10px', border: '1px solid #ccc', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
  smallBtn: { padding: '6px 12px', background: '#15803d', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  smallGray: { padding: '6px 12px', background: '#eee', color: '#333', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  empty: { textAlign: 'center', padding: 40, background: '#fafafa', border: '1px dashed #ddd', borderRadius: 12 },
  error: { color: '#c0392b', background: '#fdf0ef', padding: 12, borderRadius: 8, marginBottom: 12 },
}
