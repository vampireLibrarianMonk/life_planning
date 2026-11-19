import { useEffect, useState } from 'react'
import {
  fetchCDOverview, fetchCDAgeGroup, seedCDAgeGroup, deactivateCDAgeGroup,
  fetchCDWorries, saveCDWorries, updateEntry, deleteEntry, createEntry,
  fetchGallery, smartUploadGalleryMedia, linkGalleryObjective, unlinkGalleryObjective,
  createCDDomain, renameCDDomain, deleteCDDomain,
} from '../services/api'

const MARKS = [
  { key: 'not_started', label: 'not yet' },
  { key: 'in_progress', label: 'emerging' },
  { key: 'complete', label: 'doing' },
]

// The legend shown on the page and on the printed stage sheet.
const LEGEND = [
  { label: 'not yet', text: 'not observed in this stage yet — every child moves at their own pace' },
  { label: 'emerging', text: 'attempted sometimes or with help — the skill is forming' },
  { label: 'doing', text: 'done reliably and independently' },
]


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
        {!overview && <p style={{ color: '#595959' }}>Loading…</p>}
        {overview && (
          <div className="pillar-grid-desktop" style={{ marginTop: 12 }}>
            {overview.catalog.map(g => (
              <button
                key={g.age_band}
                onClick={() => setAgeBand(g.age_band)}
                style={{ ...s.card, background: g.active ? '#fff' : '#f7f7f7', borderColor: g.active ? '#8bc79b' : '#d0d0d0' }}
                title={g.active ? 'Open' : 'Not activated yet'}
              >
                <span style={{ fontSize: 20, opacity: g.active ? 1 : 0.6 }} aria-hidden="true">{g.active ? '🌿' : '➕'}</span>
                <span style={{ fontSize: 14, fontWeight: 600, marginTop: 6 }}>{g.label}</span>
                <span style={{ fontSize: 11, color: '#595959', marginTop: 2 }}>{g.active ? 'Active' : 'Tap to add'}</span>
              </button>
            ))}
          </div>
        )}
        <p style={{ fontSize: 12, color: '#595959', marginTop: 16 }}>
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
  // Idempotent top-up: adds any checklist items added to the corpus since this
  // age group was first seeded (skips everything already present).
  const syncChecklist = async () => {
    setBusy(true)
    const r = await seedCDAgeGroup(profileId, ageBand)
    await loadGroup(ageBand)
    setBusy(false)
    if (r && typeof r.created === 'number') {
      alert(r.created > 0 ? `${r.created} new checklist item(s) added.` : 'Checklist is already up to date.')
    }
  }
  // Print: browsers use document.title as the default "Save as PDF" filename.
  const printSheet = () => {
    const now = new Date()
    const pad = (n) => String(n).padStart(2, '0')
    const fname = [
      `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`,
      `${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`,
      ageBand,
      profileName,
    ].join('-')
    const prev = document.title
    document.title = fname
    window.print()
    document.title = prev
  }
  const renameDomain = async (domainKey, domainLabel) => {
    const name = prompt(`Rename "${domainLabel}" to:`, domainLabel)
    if (!name || !name.trim() || name.trim() === domainLabel) return
    setBusy(true)
    try {
      await renameCDDomain(profileId, ageBand, domainKey, name.trim())
      await loadGroup(ageBand)
    } catch (e) {
      alert(e.message || 'Rename failed')
    } finally {
      setBusy(false)
    }
  }
  const removeDomain = async (domainKey, domainLabel, itemCount) => {
    if (!confirm(`Delete the "${domainLabel}" category and its ${itemCount} objective(s)? Accomplishment photos stay in the Gallery.`)) return
    setBusy(true)
    try {
      await deleteCDDomain(profileId, ageBand, domainKey)
      await loadGroup(ageBand)
    } catch (e) {
      alert(e.message || 'Delete failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={s.container}>
      <style>{`
        @media print {
          .cd-no-print { display: none !important; }
          .cd-print-header { display: block !important; }
        }
        .cd-print-header { display: none; }
      `}</style>
      <button onClick={() => setAgeBand(null)} className="cd-no-print" style={s.back}>&larr; All age groups</button>
      {/* Print-only header: names the saved PDF and carries the legend */}
      <div className="cd-print-header" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>{profileName} — {group ? group.label : ageBand} Development Checklist</h2>
        <p style={{ margin: '2px 0 6px', fontSize: 12 }}>
          Printed {new Date().toLocaleString()} · Child Development · Early Growth Markers
        </p>
        <p style={{ margin: 0, fontSize: 11 }}>
          <strong>Legend:</strong>{' '}
          {LEGEND.map(l => `${l.label} = ${l.text}`).join(' · ')}
        </p>
      </div>
      <div style={s.header}>
        <span style={{ fontSize: 30 }}>🌿</span>
        <div>
          <h2 style={{ margin: 0 }}>{group ? group.label : ageBand}</h2>
          <p style={{ margin: '2px 0 0', fontSize: 13, color: '#666' }}>{profileName} · Child Development</p>
        </div>
      </div>

      {/* Legend — how to mark */}
      <div style={s.legend}>
        <strong style={{ fontSize: 12 }}>How to mark:</strong>{' '}
        {LEGEND.map(l => (
          <span key={l.label} style={{ fontSize: 12, color: '#595959' }}>
            <strong>{l.label}</strong> — {l.text}{'  '}
          </span>
        ))}
      </div>

      {!group && <p style={{ color: '#595959' }}>Loading…</p>}

      {group && !hasObjectives && (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <p style={{ color: '#595959' }}>This age group isn't active yet.</p>
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
                <h3 style={{ margin: '0 0 6px', fontSize: 15, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ flex: 1 }}>{domainLabel}</span>
                  {canWrite && (
                    <span className="cd-no-print" style={{ display: 'flex', gap: 2 }}>
                      <button
                        className="tap-target"
                        onClick={() => renameDomain(domainKey, domainLabel)}
                        style={s.iconBtn}
                        title="Rename this category"
                      >✎</button>
                      <button
                        className="tap-target"
                        onClick={() => removeDomain(domainKey, domainLabel, items.length)}
                        style={{ ...s.iconBtn, color: '#c0392b' }}
                        title="Delete this category and its objectives"
                      >✕</button>
                    </span>
                  )}
                </h3>
                {items.length === 0 && <p style={{ fontSize: 12, color: '#595959', margin: '0 0 8px' }}>No objectives.</p>}
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

          {canWrite && <AddDomain profileId={profileId} ageBand={ageBand} onAdded={() => loadGroup(ageBand)} />}

          <Notes profileId={profileId} ageBand={ageBand} canWrite={canWrite} adminUser={adminUser} />

          <div className="cd-no-print" style={{ marginTop: 20, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button onClick={printSheet} style={s.secondaryBtn}>🖨️ Print stage sheet</button>
            {canWrite && (
              <button onClick={syncChecklist} disabled={busy} style={s.smallGray} title="Adds any checklist items added to the app since this age group was first created. Never changes your marks or custom items.">
                {busy ? 'Checking…' : '⟳ Sync new checklist items'}
              </button>
            )}
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
  const [uploadError, setUploadError] = useState('')
  const [editing, setEditing] = useState(false)
  const [draftTitle, setDraftTitle] = useState('')

  const setMark = async (statusKey) => {
    await updateEntry(profileId, obj.id, { status: statusKey })
    onChanged()
  }
  const startEdit = () => {
    setDraftTitle(obj.title)
    setEditing(true)
  }
  const saveEdit = async () => {
    if (!draftTitle.trim() || draftTitle.trim() === obj.title) {
      setEditing(false)
      return
    }
    await updateEntry(profileId, obj.id, { title: draftTitle.trim() })
    setEditing(false)
    onChanged()
  }
  const remove = async () => {
    if (!confirm('Delete this objective?')) return
    await deleteEntry(profileId, obj.id)
    onChanged()
  }
  // Media now lives in the canonical, child-scoped Gallery and is linked to this
  // objective. That means it ALSO appears in the main Gallery and, critically,
  // survives this objective (or the whole age group) being deleted.
  const loadPhotos = async () => {
    const a = await fetchGallery(profileId, { objectiveId: obj.id })
    setPhotos(Array.isArray(a) ? a : [])
    setShowPhotos(true)
  }
  const onUpload = async (e) => {
    const files = Array.from(e.target.files || [])
    e.target.value = ''
    if (!files.length) return
    setUploadError('')
    try {
      const created = await smartUploadGalleryMedia(profileId, files)
      for (const m of created) {
        await linkGalleryObjective(profileId, m.id, obj.id)
      }
      const a = await fetchGallery(profileId, { objectiveId: obj.id })
      setPhotos(Array.isArray(a) ? a : [])
      setShowPhotos(true)
    } catch (err) {
      setUploadError(err.message || 'Upload failed')
      setShowPhotos(true)
    }
  }

  return (
    <div style={s.objRow}>
      <div style={{ flex: 1 }}>
        {editing ? (
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              value={draftTitle}
              onChange={e => setDraftTitle(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') setEditing(false) }}
              style={{ ...s.input, flex: 1 }}
              autoFocus
            />
            <button onClick={saveEdit} style={s.smallBtn}>Save</button>
            <button onClick={() => setEditing(false)} style={s.smallGray}>Cancel</button>
          </div>
        ) : (
          <span style={{ fontSize: 14 }}>{obj.title}</span>
        )}
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
        {canWrite && !editing && (
          <button className="tap-target" onClick={startEdit} style={s.iconBtn} title="Edit this objective">✎</button>
        )}
        <button className="tap-target" onClick={loadPhotos} style={s.iconBtn} title="Accomplishment photos & videos">📷</button>
        {canWrite && <button className="tap-target" onClick={remove} style={s.iconBtn} title="Delete objective">✕</button>}
      </div>
      {showPhotos && (
        <div style={s.photoPanel}>
          {canWrite && (
            <label style={s.uploadLabel}>
              + Add photo/video
              <input type="file" multiple accept="image/*,video/*,.pdf" onChange={onUpload} style={{ display: 'none' }} />
            </label>
          )}
          <p style={{ fontSize: 11, color: '#767676', margin: '4px 0 0' }}>
            Also appears in this child&rsquo;s Gallery; kept even if this objective is removed.
          </p>
          {uploadError && (
            <p style={{ fontSize: 12, color: '#c0392b', background: '#fdf0ef', borderRadius: 6, padding: '6px 10px', margin: '6px 0 0' }}>
              {uploadError}
            </p>
          )}
          {photos && photos.length === 0 && <span style={{ fontSize: 12, color: '#595959' }}>No media yet.</span>}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
            {(photos || []).map(p => (
              <div key={p.id} style={{ position: 'relative' }}>
                {p.media_type === 'video' ? (
                  <video src={p.url} controls preload="metadata" style={{ width: 90, height: 70, objectFit: 'cover', borderRadius: 6, background: '#000' }} />
                ) : p.media_type === 'photo' ? (
                  <a href={p.url} target="_blank" rel="noreferrer">
                    <img src={p.url} alt={p.observation || p.original_name} style={{ width: 70, height: 70, objectFit: 'cover', borderRadius: 6 }} />
                  </a>
                ) : (
                  <a href={p.url} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>📄 {p.original_name}</a>
                )}
                {canWrite && (
                  <button
                    title="Remove from this objective (keeps it in the Gallery)"
                    onClick={async () => { await unlinkGalleryObjective(profileId, p.id, obj.id); const a = await fetchGallery(profileId, { objectiveId: obj.id }); setPhotos(Array.isArray(a) ? a : []) }}
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

function AddDomain({ profileId, ageBand, onAdded }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [firstItem, setFirstItem] = useState('')
  const [error, setError] = useState('')
  const add = async () => {
    if (!name.trim()) return
    setError('')
    try {
      await createCDDomain(profileId, ageBand, name.trim(), firstItem.trim() || null)
      setName('')
      setFirstItem('')
      setOpen(false)
      onAdded()
    } catch (e) {
      setError(e.message || 'Could not add category')
    }
  }
  if (!open) return <button onClick={() => setOpen(true)} style={s.addBtn}>+ Add a category</button>
  return (
    <div style={{ background: '#f9fbf9', border: '1px dashed #cdd8ce', borderRadius: 10, padding: 10, marginBottom: 12 }}>
      <input
        value={name}
        onChange={e => setName(e.target.value)}
        placeholder="Category name (e.g. Self-help skills)"
        style={{ ...s.input, width: '100%', boxSizing: 'border-box' }}
        autoFocus
      />
      <input
        value={firstItem}
        onChange={e => setFirstItem(e.target.value)}
        placeholder="First objective (optional — add more after)"
        style={{ ...s.input, width: '100%', boxSizing: 'border-box', marginTop: 6 }}
      />
      {error && <p style={{ fontSize: 12, color: '#c0392b', margin: '6px 0 0' }}>{error}</p>}
      <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
        <button onClick={add} style={s.smallBtn}>Add category</button>
        <button onClick={() => { setOpen(false); setName(''); setFirstItem(''); setError('') }} style={s.smallGray}>Cancel</button>
      </div>
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
          <p style={{ fontSize: 12, color: '#595959', marginTop: 6 }}>Private to parents and the child.</p>
        )}
      </div>
    </div>
  )
}

const s = {
  container: { maxWidth: 820, margin: '0 auto', padding: '8px 16px 48px' },
  back: { background: 'none', border: 'none', color: '#2563b0', cursor: 'pointer', fontSize: 14, padding: '6px 0' },
  header: { display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0 10px' },
  card: { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '14px 10px', background: '#fff', border: '2px solid #e0e0e0', borderRadius: 10, cursor: 'pointer' },
  domain: { background: '#f9fbf9', border: '1px solid #e6efe6', borderRadius: 10, padding: 12, marginBottom: 12 },
  objRow: { display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', gap: 8, padding: '8px 4px', borderBottom: '1px solid #eef3ee' },
  mark: { fontSize: 11, padding: '3px 10px', borderRadius: 12, border: '1px solid #cdd8ce', background: '#fff', color: '#5a6b5c', cursor: 'pointer' },
  markOn: { background: '#2a7d45', borderColor: '#2a7d45', color: '#fff', fontWeight: 600 },
  iconBtn: { background: 'none', border: 'none', cursor: 'pointer', fontSize: 15, color: '#777' },
  photoPanel: { width: '100%', background: '#fff', border: '1px dashed #d6e0d6', borderRadius: 8, padding: 8, marginTop: 6 },
  uploadLabel: { fontSize: 12, color: '#2563b0', cursor: 'pointer' },
  photoDel: { position: 'absolute', top: -6, right: -6, background: '#c0392b', color: '#fff', border: 'none', borderRadius: '50%', width: 18, height: 18, cursor: 'pointer', fontSize: 11 },
  addBtn: { fontSize: 12, color: '#2563b0', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 0', textAlign: 'left' },
  input: { padding: '7px 10px', border: '1px solid #ccc', borderRadius: 6, fontSize: 13 },
  smallBtn: { padding: '7px 14px', background: '#2a7d45', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  smallGray: { padding: '7px 14px', background: '#eee', color: '#333', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  primaryBtn: { padding: '10px 22px', background: '#2a7d45', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 },
  secondaryBtn: { padding: '9px 18px', background: '#2563b0', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13 },
  dangerBtn: { padding: '9px 18px', background: '#fdecea', color: '#c0392b', border: '1px solid #f3c6c0', borderRadius: 8, cursor: 'pointer', fontSize: 13 },
  noteBox: { background: '#fffdf5', border: '1px solid #efe6c8', borderRadius: 10, padding: 12 },
  legend: { background: '#f4f7f4', border: '1px solid #e2ebe2', borderRadius: 8, padding: '8px 10px', marginBottom: 12, display: 'flex', flexWrap: 'wrap', gap: 10 },
}
