import { useEffect, useState } from 'react'
import {
  fetchCDOverview, fetchCDAgeGroup, seedCDAgeGroup, deactivateCDAgeGroup,
  fetchCDWorries, saveCDWorries, updateEntry, deleteEntry, createEntry,
  uploadAttachments, fetchAttachments, deleteAttachment,
} from '../services/api'

const MARKS = [
  { key: 'not_started', label: 'not yet' },
  { key: 'in_progress', label: 'emerging' },
  { key: 'complete', label: 'practicing' },
]

const BANNER = 'A gentle guide, not a test, score, or diagnosis — this app is not a medical tool. Every age is a window, not a deadline. Share anything here with your pediatrician.'

/**
 * Child Development section view. Two levels:
 *  - no ageBand  -> age-group cards (active + available to activate)
 *  - ageBand set -> objectives grouped by domain, each with a CRUD menu +
 *                   accomplishment photos; plus the two notes.
 * Objectives + photos are family-readable; the "worries" note is parent/child
 * only (its API returns 403 for readonly, handled gracefully).
 */
export default function ChildDevelopment({ profileId, profileName, ageBand, setAgeBand, onBack, canWrite, adminUser }) {
  const [overview, setOverview] = useState(null)
  const [group, setGroup] = useState(null)
  const [busy, setBusy] = useState(false)

  const loadOverview = () => fetchCDOverview(profileId).then(setOverview)
  const loadGroup = (b) => fetchCDAgeGroup(profileId, b).then(setGroup)

  useEffect(() => {
    if (ageBand) loadGroup(ageBand)
    else loadOverview()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId, ageBand])

  // ---------- Age-group list level ----------
  if (!ageBand) {
    return (
      <div style={s.container}>
        <button onClick={onBack} style={s.back}>&larr; Back to Dashboard</button>
        <div style={s.header}>
          <span style={{ fontSize: 30 }}>🌱</span>
          <div>
            <h2 style={{ margin: 0 }}>Child Development</h2>
            <p style={{ margin: '2px 0 0', fontSize: 13, color: '#666' }}>Early Growth Markers — ages ~2 months to 5 years</p>
          </div>
        </div>
        <p style={s.banner} role="note">{BANNER}</p>
        {!overview && <p style={{ color: '#888' }}>Loading…</p>}
        {overview && (
          <div className="pillar-grid-desktop" style={{ marginTop: 12 }}>
            {overview.catalog.map(g => (
              <button
                key={g.age_band}
                onClick={() => setAgeBand(g.age_band)}
                style={{ ...s.card, opacity: g.active ? 1 : 0.6, borderColor: g.active ? '#8bc79b' : '#e0e0e0' }}
                title={g.active ? 'Open' : 'Not activated yet'}
              >
                <span style={{ fontSize: 20 }}>{g.active ? '🌿' : '➕'}</span>
                <span style={{ fontSize: 14, fontWeight: 600, marginTop: 6 }}>{g.label}</span>
                <span style={{ fontSize: 11, color: '#595959', marginTop: 2 }}>{g.active ? 'Active' : 'Tap to add'}</span>
              </button>
            ))}
          </div>
        )}
        <p style={{ fontSize: 12, color: '#888', marginTop: 16 }}>
          Tap an age group to view it. Grayed groups aren&apos;t active yet — opening one lets you add it.
        </p>
      </div>
    )
  }

  // ---------- Age-group detail level ----------
  const isActive = overview ? overview.active.includes(ageBand) : (group && Object.values(group.objectives || {}).some(a => a.length))
  const hasObjectives = group && Object.values(group.objectives || {}).some(a => a.length)

  const activate = async () => {
    setBusy(true)
    await seedCDAgeGroup(profileId, ageBand)
    await loadGroup(ageBand)
    setBusy(false)
  }
  const deactivate = async () => {
    if (!confirm(`Remove the ${group?.label || ageBand} age group and its marks?`)) return
    setBusy(true)
    await deactivateCDAgeGroup(profileId, ageBand)
    setGroup(null)
    setAgeBand(null)
    setBusy(false)
  }

  return (
    <div style={s.container}>
      <button onClick={() => setAgeBand(null)} style={s.back}>&larr; All age groups</button>
      <div style={s.header}>
        <span style={{ fontSize: 30 }}>🌿</span>
        <div>
          <h2 style={{ margin: 0 }}>{group ? group.label : ageBand}</h2>
          <p style={{ margin: '2px 0 0', fontSize: 13, color: '#666' }}>{profileName} · Child Development</p>
        </div>
      </div>
      <p style={s.banner} role="note">{BANNER}</p>

      {!group && <p style={{ color: '#888' }}>Loading…</p>}

      {group && !hasObjectives && (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <p style={{ color: '#595959' }}>This age group isn&apos;t active yet.</p>
          {canWrite && (
            <button onClick={activate} disabled={busy} style={s.primaryBtn}>
              {busy ? 'Adding…' : 'Add this age group'}
            </button>
          )}
        </div>
      )}

      {group && hasObjectives && (
        <>
          {Object.entries(group.domains).map(([domainKey, domainLabel]) => {
            const items = (group.objectives[domainKey] || [])
            return (
              <div key={domainKey} style={s.domain}>
                <h3 style={{ margin: '0 0 6px', fontSize: 15 }}>{domainLabel}</h3>
                {items.length === 0 && <p style={{ fontSize: 12, color: '#999', margin: '0 0 8px' }}>No objectives.</p>}
                {items.map(obj => (
                  <ObjectiveRow
                    key={obj.id}
                    profileId={profileId}
                    obj={obj}
                    canWrite={canWrite}
                    onChanged={() => loadGroup(ageBand)}
                  />
                ))}
                {canWrite && (
                  <AddObjective
                    profileId={profileId}
                    ageBand={ageBand}
                    domainKey={domainKey}
                    onAdded={() => loadGroup(ageBand)}
                  />
                )}
              </div>
            )
          })}

          <Notes profileId={profileId} ageBand={ageBand} canWrite={canWrite} adminUser={adminUser} />

          <div style={{ marginTop: 20, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button onClick={() => window.print()} style={s.secondaryBtn}>🖨️ Print stage sheet</button>
            {adminUser && <button onClick={deactivate} disabled={busy} style={s.dangerBtn}>Remove this age group</button>}
          </div>
        </>
      )}
    </div>
  )
}

function ObjectiveRow({ profileId, obj, canWrite, onChanged }) {
  const [photos, setPhotos] = useState(null)
  const [showPhotos, setShowPhotos] = useState(false)

  const setMark = async (statusKey) => {
    await updateEntry(profileId, obj.id, { status: statusKey })
    onChanged()
  }
  const remove = async () => {
    if (!confirm('Delete this objective?')) return
    await deleteEntry(profileId, obj.id)
    onChanged()
  }
  const loadPhotos = async () => {
    const a = await fetchAttachments(profileId, obj.id)
    setPhotos(Array.isArray(a) ? a : [])
    setShowPhotos(true)
  }
  const onUpload = async (e) => {
    const files = Array.from(e.target.files || [])
    e.target.value = ''
    if (!files.length) return
    await uploadAttachments(profileId, obj.id, files)
    const a = await fetchAttachments(profileId, obj.id)
    setPhotos(Array.isArray(a) ? a : [])
    setShowPhotos(true)
  }

  return (
    <div style={s.objRow}>
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 14 }}>{obj.title}</span>
        <div style={{ marginTop: 4, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {MARKS.map(m => {
            const on = obj.status === m.key
            return canWrite ? (
              <button key={m.key} onClick={() => setMark(m.key)} style={{ ...s.mark, ...(on ? s.markOn : {}) }}>{m.label}</button>
            ) : (
              <span key={m.key} style={{ ...s.mark, ...(on ? s.markOn : {}), cursor: 'default' }}>{m.label}</span>
            )
          })}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <button onClick={loadPhotos} style={s.iconBtn} title="Accomplishment photos">📷</button>
        {canWrite && <button onClick={remove} style={s.iconBtn} title="Delete objective">✕</button>}
      </div>
      {showPhotos && (
        <div style={s.photoPanel}>
          {canWrite && (
            <label style={s.uploadLabel}>
              + Add photo/attachment
              <input type="file" multiple accept="image/*,video/*,.pdf" onChange={onUpload} style={{ display: 'none' }} />
            </label>
          )}
          {photos && photos.length === 0 && <span style={{ fontSize: 12, color: '#999' }}>No photos yet.</span>}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
            {(photos || []).map(p => (
              <div key={p.id} style={{ position: 'relative' }}>
                {p.mime_type && p.mime_type.startsWith('image/') ? (
                  <a href={`/api/uploads/${p.filename}`} target="_blank" rel="noreferrer">
                    <img src={`/api/uploads/${p.filename}`} alt={p.original_name} style={{ width: 70, height: 70, objectFit: 'cover', borderRadius: 6 }} />
                  </a>
                ) : (
                  <a href={`/api/uploads/${p.filename}`} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>📄 {p.original_name}</a>
                )}
                {canWrite && (
                  <button
                    onClick={async () => { await deleteAttachment(profileId, obj.id, p.id); const a = await fetchAttachments(profileId, obj.id); setPhotos(Array.isArray(a) ? a : []) }}
                    style={s.photoDel}
                  >×</button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function AddObjective({ profileId, ageBand, domainKey, onAdded }) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const add = async () => {
    if (!title.trim()) return
    await createEntry(profileId, {
      pillar: 'education',
      is_milestone: 1,
      age_band: ageBand,
      category: `child_development:${domainKey}`,
      title: title.trim(),
    })
    setTitle('')
    setOpen(false)
    onAdded()
  }
  if (!open) return <button onClick={() => setOpen(true)} style={s.addBtn}>+ Add your own</button>
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
      <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Describe what to look for…" style={s.input} autoFocus />
      <button onClick={add} style={s.smallBtn}>Add</button>
      <button onClick={() => { setOpen(false); setTitle('') }} style={s.smallGray}>Cancel</button>
    </div>
  )
}

function Notes({ profileId, ageBand, canWrite, adminUser }) {
  const [worries, setWorries] = useState('')
  const [worriesAllowed, setWorriesAllowed] = useState(true)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetchCDWorries(profileId, ageBand).then(r => {
      if (r && typeof r.content === 'string') setWorries(r.content)
    }).catch(() => setWorriesAllowed(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId, ageBand])

  const save = async () => {
    await saveCDWorries(profileId, ageBand, worries)
    setSaved(true); setTimeout(() => setSaved(false), 1500)
  }

  return (
    <div style={{ marginTop: 16 }} className="cd-notes">
      <div style={s.noteBox}>
        <strong style={{ fontSize: 13 }}>Questions &amp; worries for the next check-up</strong>
        <span style={{ fontSize: 11, color: '#8a6f00', marginLeft: 8 }}>🔒 private — parents &amp; child only</span>
        {canWrite ? (
          <>
            <textarea value={worries} onChange={e => setWorries(e.target.value)} placeholder="Keep sensitive concerns here; raise them directly with your pediatrician." style={{ ...s.input, width: '100%', minHeight: 70, marginTop: 6 }} />
            <button onClick={save} style={s.smallBtn}>{saved ? 'Saved ✓' : 'Save'}</button>
          </>
        ) : (
          <p style={{ fontSize: 12, color: '#999', marginTop: 6 }}>Private to parents and the child.</p>
        )}
      </div>
    </div>
  )
}

const s = {
  container: { maxWidth: 820, margin: '0 auto', padding: '8px 16px 48px' },
  back: { background: 'none', border: 'none', color: '#2563b0', cursor: 'pointer', fontSize: 14, padding: '6px 0' },
  header: { display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0 10px' },
  banner: { fontSize: 12, color: '#8a6f00', background: '#fff8e6', border: '1px solid #f0e2b8', borderRadius: 8, padding: '8px 12px', margin: '0 0 12px' },
  card: { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '14px 10px', background: '#fff', border: '2px solid #e0e0e0', borderRadius: 10, cursor: 'pointer' },
  domain: { background: '#f9fbf9', border: '1px solid #e6efe6', borderRadius: 10, padding: 12, marginBottom: 12 },
  objRow: { display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', gap: 8, padding: '8px 4px', borderBottom: '1px solid #eef3ee' },
  mark: { fontSize: 11, padding: '3px 10px', borderRadius: 12, border: '1px solid #cdd8ce', background: '#fff', color: '#5a6b5c', cursor: 'pointer' },
  markOn: { background: '#2f8f4e', borderColor: '#2f8f4e', color: '#fff', fontWeight: 600 },
  iconBtn: { background: 'none', border: 'none', cursor: 'pointer', fontSize: 15, color: '#777' },
  photoPanel: { width: '100%', background: '#fff', border: '1px dashed #d6e0d6', borderRadius: 8, padding: 8, marginTop: 6 },
  uploadLabel: { fontSize: 12, color: '#2563b0', cursor: 'pointer' },
  photoDel: { position: 'absolute', top: -6, right: -6, background: '#c0392b', color: '#fff', border: 'none', borderRadius: '50%', width: 18, height: 18, cursor: 'pointer', fontSize: 11 },
  addBtn: { fontSize: 12, color: '#2563b0', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 0', textAlign: 'left' },
  input: { padding: '7px 10px', border: '1px solid #ccc', borderRadius: 6, fontSize: 13 },
  smallBtn: { padding: '7px 14px', background: '#2f8f4e', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  smallGray: { padding: '7px 14px', background: '#eee', color: '#333', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  primaryBtn: { padding: '10px 22px', background: '#2f8f4e', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 },
  secondaryBtn: { padding: '9px 18px', background: '#2563b0', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13 },
  dangerBtn: { padding: '9px 18px', background: '#fdecea', color: '#c0392b', border: '1px solid #f3c6c0', borderRadius: 8, cursor: 'pointer', fontSize: 13 },
  noteBox: { background: '#fffdf5', border: '1px solid #efe6c8', borderRadius: 10, padding: 12 },
}
