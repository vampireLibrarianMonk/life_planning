import { useEffect, useRef, useState } from 'react'
import {
  fetchGallery,
  smartUploadGalleryMedia,
  updateGalleryMedia,
  deleteGalleryMedia,
  fetchCDObjectiveChoices,
  linkGalleryObjective,
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

export default function Gallery({ profileId, profileName, onBack, canWrite, onEmailCenter }) {
  const [items, setItems] = useState(null)
  const [mediaType, setMediaType] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState(null) // media id being edited
  const [draftObs, setDraftObs] = useState('')
  const [goalPicker, setGoalPicker] = useState(null)
  const [goalChoices, setGoalChoices] = useState([])
  const [selectedGoalIds, setSelectedGoalIds] = useState([])
  const [goalBusy, setGoalBusy] = useState(false)
  const [goalError, setGoalError] = useState('')
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
    setNotice('')
    try {
      const uploaded = await smartUploadGalleryMedia(profileId, files)
      const reused = uploaded.filter((media) => media.reused).length
      if (reused) {
        setNotice(`${reused} existing Gallery item${reused === 1 ? '' : 's'} reused; no duplicate file was uploaded.`)
      }
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

  async function openGoalPicker(media) {
    setGoalPicker(media)
    setSelectedGoalIds(media.objective_ids || [])
    setGoalError('')
    setGoalChoices([])
    setGoalBusy(true)
    try {
      const choices = await fetchCDObjectiveChoices(profileId)
      setGoalChoices(Array.isArray(choices) ? choices : [])
    } catch (err) {
      setGoalError(err.message || 'Could not load development goals.')
    } finally {
      setGoalBusy(false)
    }
  }

  async function saveGoalLinks() {
    if (!goalPicker) return
    setGoalBusy(true)
    setGoalError('')
    try {
      const alreadyLinked = new Set(goalPicker.objective_ids || [])
      for (const objectiveId of selectedGoalIds) {
        if (!alreadyLinked.has(objectiveId)) {
          await linkGalleryObjective(profileId, goalPicker.id, objectiveId)
        }
      }
      await load()
      setGoalPicker(null)
    } catch (err) {
      setGoalError(err.message || 'Could not add the Gallery item to the selected goal.')
    } finally {
      setGoalBusy(false)
    }
  }

  function toggleGoal(objectiveId) {
    setSelectedGoalIds((ids) => (
      ids.includes(objectiveId) ? ids.filter((id) => id !== objectiveId) : [...ids, objectiveId]
    ))
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
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {canWrite && onEmailCenter && (
            <button onClick={onEmailCenter} style={s.emailBtn} title="Compose an email update from selected media">
              ✉️ Email Center
            </button>
          )}
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
      </div>

      {error && <p style={s.error}>{error}</p>}
      {notice && <p style={s.notice}>{notice}</p>}
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
                            title="Add to development goal"
                            onClick={() => openGoalPicker(m)}
                            style={s.iconBtn}
                          >
                            🌱
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
      {goalPicker && (
        <div role="dialog" aria-modal="true" aria-label="Add Gallery item to development goals" style={s.modalShade}>
          <div style={s.modal}>
            <h3 style={{ margin: 0, fontSize: 16 }}>Add to development goals</h3>
            <p style={{ margin: '6px 0 10px', fontSize: 13, color: '#595959' }}>
              {goalPicker.original_name} stays in this child&apos;s Gallery; selecting goals only adds links.
            </p>
            {goalError && <p style={s.error}>{goalError}</p>}
            {goalBusy && goalChoices.length === 0 ? (
              <p style={{ color: '#595959' }}>Loading goals…</p>
            ) : goalChoices.length === 0 ? (
              <p style={{ color: '#595959' }}>No development goals are active yet.</p>
            ) : (
              <div style={s.goalList}>
                {goalChoices.map((goal) => {
                  const wasLinked = (goalPicker.objective_ids || []).includes(goal.id)
                  return (
                    <label key={goal.id} style={s.goalChoice}>
                      <input
                        type="checkbox"
                        checked={selectedGoalIds.includes(goal.id)}
                        disabled={wasLinked || goalBusy}
                        onChange={() => toggleGoal(goal.id)}
                      />
                      <span>
                        {goal.title}
                        <small style={s.goalMeta}>{goal.age_band} · {goal.domain}{wasLinked ? ' · already added' : ''}</small>
                      </span>
                    </label>
                  )
                })}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
              <button onClick={() => setGoalPicker(null)} disabled={goalBusy} style={s.smallGray}>Cancel</button>
              <button onClick={saveGoalLinks} disabled={goalBusy || goalChoices.length === 0} style={s.smallBtn}>
                {goalBusy ? 'Adding…' : 'Add selected'}
              </button>
            </div>
          </div>
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
  emailBtn: { fontSize: 14, fontWeight: 600, padding: '8px 16px', background: '#2563b0', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' },
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
  notice: { color: '#166534', background: '#ecfdf3', padding: 12, borderRadius: 8, marginBottom: 12 },
  modalShade: { position: 'fixed', inset: 0, zIndex: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, background: 'rgba(0, 0, 0, .42)' },
  modal: { width: 'min(520px, 100%)', maxHeight: 'min(640px, calc(100vh - 32px))', overflowY: 'auto', boxSizing: 'border-box', padding: 18, borderRadius: 12, background: '#fff', boxShadow: '0 12px 36px rgba(0,0,0,.25)' },
  goalList: { display: 'flex', flexDirection: 'column', gap: 7, maxHeight: 360, overflowY: 'auto', padding: '2px 0' },
  goalChoice: { display: 'flex', gap: 9, alignItems: 'flex-start', padding: 8, border: '1px solid #e4e7eb', borderRadius: 7, fontSize: 13, cursor: 'pointer' },
  goalMeta: { display: 'block', marginTop: 2, color: '#666', fontSize: 11 },
}
