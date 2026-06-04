import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchProfile, fetchEntries, createEntry, updateEntry, deleteEntry } from '../services/api'
import Economy from './Economy'

const PILLARS = [
  { key: 'spiritual', label: 'Spiritual', icon: '✝️', placeholder: "e.g. 'First prayer unprompted'" },
  { key: 'financial', label: 'Financial', icon: '💰', placeholder: "e.g. 'Opened savings account'" },
  { key: 'education', label: 'Education & Career', icon: '🎓', placeholder: "e.g. 'Joined robotics club'" },
  { key: 'character', label: 'Character', icon: '🛡️', placeholder: "e.g. 'Admitted mistake to teacher'" },
  { key: 'life_skills', label: 'Life Skills', icon: '🔧', placeholder: "e.g. 'Cooked first meal alone'" },
  { key: 'heritage', label: 'Heritage', icon: '🌳', placeholder: "e.g. 'Researched great-grandfather'" },
  { key: 'economy', label: 'Family Economy', icon: '⚖️', placeholder: "e.g. 'Completed first Silver task'" },
  { key: 'resilience', label: 'Resilience', icon: '🏔️', placeholder: "e.g. 'Discussed career pressure'" },
]

const STATUS_COLORS = { pending: '#e0e0e0', in_progress: '#f5a623', complete: '#2ecc71' }
const STATUS_LABELS = { pending: '○', in_progress: '◐', complete: '●' }
const STATUS_CYCLE = { pending: 'in_progress', in_progress: 'complete', complete: 'pending' }

export default function Profile() {
  const { id } = useParams()
  const [profile, setProfile] = useState(null)
  const [activePillar, setActivePillar] = useState(null)
  const [entries, setEntries] = useState([])
  const [allCounts, setAllCounts] = useState({})
  const [allRaw, setAllRaw] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [formType, setFormType] = useState('note') // 'note' or 'milestone'
  const [formTitle, setFormTitle] = useState('')
  const [formContent, setFormContent] = useState('')
  const [formAge, setFormAge] = useState('')
  const [formAgeBand, setFormAgeBand] = useState('')
  const [formScore, setFormScore] = useState('')
  const [editing, setEditing] = useState(null) // entry id being edited
  const [editTitle, setEditTitle] = useState('')
  const [editContent, setEditContent] = useState('')

  useEffect(() => { fetchProfile(id).then(setProfile); loadCounts() }, [id])

  const loadCounts = () => {
    fetchEntries(id).then(data => {
      if (!Array.isArray(data)) return
      setAllRaw(data)
      const counts = {}
      data.forEach(e => {
        if (!counts[e.pillar]) counts[e.pillar] = { total: 0, complete: 0 }
        counts[e.pillar].total++
        if (e.status === 'complete') counts[e.pillar].complete++
      })
      setAllCounts(counts)
    })
  }

  const loadEntries = () => {
    if (activePillar) fetchEntries(id, activePillar).then(data => setEntries(Array.isArray(data) ? data : []))
  }

  useEffect(() => { loadEntries() }, [id, activePillar])

  const handleAddEntry = async (e) => {
    e.preventDefault()
    if (!formTitle.trim()) return
    await createEntry(id, {
      pillar: activePillar,
      title: formTitle.trim(),
      content: formContent.trim() || null,
      age_years: formAge ? parseInt(formAge) : null,
      age_band: formAgeBand || null,
      category: formAgeBand ? ({'0-5':'Foundation','6-12':'Exploration','13-18':'Formation','18-25':'Launch','25-35':'Stewardship'}[formAgeBand] || null) : null,
      score: formScore ? parseInt(formScore) : null,
      is_milestone: formType === 'milestone' ? 1 : 0,
    })
    setFormTitle(''); setFormContent(''); setFormAge(''); setFormAgeBand(''); setFormScore(''); setShowForm(false); setFormType('note')
    loadEntries(); loadCounts()
  }

  const handleStatusToggle = async (entry) => {
    await updateEntry(id, entry.id, { status: STATUS_CYCLE[entry.status] })
    loadEntries(); loadCounts()
  }

  const handleDelete = async (entryId) => {
    if (!confirm('Delete this entry?')) return
    await deleteEntry(id, entryId); loadEntries(); loadCounts()
  }

  const startEdit = (entry) => {
    setEditing(entry.id)
    setEditTitle(entry.title)
    setEditContent(entry.content || '')
  }

  const cancelEdit = () => { setEditing(null); setEditTitle(''); setEditContent('') }

  const saveEdit = async (entryId) => {
    if (!editTitle.trim()) return
    await updateEntry(id, entryId, { title: editTitle.trim(), content: editContent.trim() || null })
    cancelEdit(); loadEntries()
  }

  const getAge = (dob) => {
    if (!dob) return null
    const born = new Date(dob), now = new Date()
    let age = now.getFullYear() - born.getFullYear()
    if (now.getMonth() < born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() < born.getDate())) age--
    return age
  }

  if (!profile) return <div style={s.container}><p>Loading...</p></div>

  const age = getAge(profile.date_of_birth)
  const phase = age === null ? '—' : age <= 5 ? 'Foundation' : age <= 12 ? 'Exploration' : age <= 17 ? 'Formation' : age <= 24 ? 'Launch' : age <= 30 ? 'Consolidation' : 'Stewardship'

  // Dashboard overview
  if (!activePillar) {
    return (
      <div style={s.container}>
        <Link to="/" style={s.back}>&larr; All Profiles</Link>
        <div style={s.profileHeader}>
          <div style={s.bigAvatar}>{profile.name.charAt(0)}</div>
          <div>
            <h1 style={s.name}>{profile.name}</h1>
            <p style={s.meta}>{age !== null && <>Age {age} &middot; </>}Phase: <strong>{phase}</strong>{profile.date_of_birth && <> &middot; Born {profile.date_of_birth}</>}</p>
          </div>
        </div>
        <h2 style={s.sectionTitle}>Development Pillars</h2>
        <div style={s.pillarGrid}>
          {PILLARS.map(p => {
            const c = allCounts[p.key] || { total: 0, complete: 0 }
            const pct = c.total ? Math.round((c.complete / c.total) * 100) : 0
            return (
              <button key={p.key} onClick={() => setActivePillar(p.key)} style={s.pillarCard}>
                <span style={{ fontSize: 28 }}>{p.icon}</span>
                <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>{p.label}</span>
                <div style={{ width: '100%', height: 4, background: '#eee', borderRadius: 2, marginTop: 8 }}>
                  <div style={{ width: `${pct}%`, height: 4, background: '#2ecc71', borderRadius: 2 }} />
                </div>
                <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>{c.complete}/{c.total} complete</span>
              </button>
            )
          })}
          <button onClick={() => setActivePillar('__economy__')} style={{ ...s.pillarCard, border: '2px solid #f0e6d0' }}>
            <span style={{ fontSize: 28 }}>💵</span>
            <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>Bounty Board</span>
            <span style={{ fontSize: 11, color: '#888', marginTop: 8 }}>Behavior &middot; Bounties &middot; Earnings</span>
          </button>
        </div>
        <div style={s.coreMetric}>
          <p style={{ margin: 0, fontSize: 12, color: '#888', textTransform: 'uppercase', letterSpacing: 1 }}>Core Metric</p>
          <p style={{ margin: '8px 0 0', fontSize: 18, fontStyle: 'italic' }}>"Is {profile.name.split(' ')[0]} becoming a wise, capable, kind, and independent person?"</p>
        </div>

        {/* Roadmap */}
        <h2 style={{ ...s.sectionTitle, marginTop: 40 }}>Roadmap</h2>
        <div style={s.roadmap}>
          {['0-5','6-12','13-18','18-25','25-35'].map((band, i) => {
            const labels = { '0-5': 'Foundation', '6-12': 'Exploration', '13-18': 'Formation', '18-25': 'Launch', '25-35': 'Consolidation' }
            const isCurrentBand = age !== null && (
              (band === '0-5' && age <= 5) || (band === '6-12' && age >= 6 && age <= 12) ||
              (band === '13-18' && age >= 13 && age <= 18) || (band === '18-25' && age >= 18 && age <= 25) ||
              (band === '25-35' && age >= 25 && age <= 35)
            )
            // Count milestones complete per band across all pillars
            const bandEntries = Object.values(allCounts).length ? null : null // we need raw entries
            return (
              <div key={band} style={{ ...s.roadmapPhase, ...(isCurrentBand ? s.roadmapActive : {}) }}>
                <div style={s.roadmapDot}>
                  <div style={{ width: 14, height: 14, borderRadius: '50%', background: isCurrentBand ? '#4a90d9' : i < (['0-5','6-12','13-18','18-25','25-35'].indexOf(band)) ? '#2ecc71' : '#ddd' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>{labels[band]}</span>
                    <span style={{ fontSize: 12, color: '#888' }}>Ages {band}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
                    {PILLARS.map(p => {
                      const pillarEntries = allRaw.filter(e => e.pillar === p.key && e.age_band === band && e.is_milestone)
                      const done = pillarEntries.filter(e => e.status === 'complete').length
                      const total = pillarEntries.length
                      if (!total) return null
                      return <span key={p.key} style={{ fontSize: 11, padding: '1px 6px', borderRadius: 8, background: done === total ? '#e8f8f0' : '#f5f5f5', color: done === total ? '#27ae60' : '#888' }}>{p.icon} {done}/{total}</span>
                    })}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // Economy view
  if (activePillar === '__economy__') {
    return (
      <div style={s.container}>
        <button onClick={() => setActivePillar(null)} style={s.backBtn}>&larr; Back to Dashboard</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0 16px' }}>
          <span style={{ fontSize: 32 }}>💵</span>
          <h2 style={{ margin: 0 }}>Bounty Board</h2>
        </div>
        <Economy profileId={id} />
      </div>
    )
  }

  // Pillar detail
  const currentPillar = PILLARS.find(p => p.key === activePillar)
  const milestones = entries.filter(e => e.is_milestone)
  const notes = entries.filter(e => !e.is_milestone)

  const grouped = {}
  milestones.forEach(m => { const band = m.age_band || 'Other'; if (!grouped[band]) grouped[band] = []; grouped[band].push(m) })
  const bandOrder = ['0-5', '6-12', '13-18', '18-25', '25-35', 'Other']

  const renderItem = (item, showDelete = true) => {
    if (editing === item.id) {
      return (
        <div key={item.id} style={{ ...s.milestone, flexDirection: 'column', alignItems: 'stretch', borderLeft: `3px solid ${STATUS_COLORS[item.status]}` }}>
          <input value={editTitle} onChange={e => setEditTitle(e.target.value)} style={s.input} />
          <textarea value={editContent} onChange={e => setEditContent(e.target.value)} placeholder="Notes/observations..." style={{ ...s.input, minHeight: 50, resize: 'vertical', marginTop: 8 }} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button onClick={() => saveEdit(item.id)} style={s.submitBtn}>Save</button>
            <button onClick={cancelEdit} style={s.cancelBtn}>Cancel</button>
          </div>
        </div>
      )
    }
    return (
      <div key={item.id} style={{ ...s.milestone, borderLeft: `3px solid ${STATUS_COLORS[item.status]}` }}>
        <button onClick={() => handleStatusToggle(item)} style={s.statusBtn} title={`Status: ${item.status} (click to cycle)`}>
          <span style={{ color: STATUS_COLORS[item.status], fontSize: 18 }}>{STATUS_LABELS[item.status]}</span>
        </button>
        <div style={{ flex: 1 }}>
          <span style={{ textDecoration: item.status === 'complete' ? 'line-through' : 'none', color: item.status === 'complete' ? '#888' : '#1a1a1a' }}>{item.title}</span>
          {item.content && <p style={{ margin: '4px 0 0', fontSize: 12, color: '#888' }}>{item.content}</p>}
        </div>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          {item.category && <span style={s.categoryBadge}>{item.category}</span>}
          {item.score != null && <span style={s.scoreBadge}>{item.score}/5</span>}
          <button onClick={() => startEdit(item)} style={s.editBtn} title="Edit">✎</button>
          {showDelete && <button onClick={() => handleDelete(item.id)} style={s.deleteBtn} title="Delete">&times;</button>}
        </div>
      </div>
    )
  }

  return (
    <div style={s.container}>
      <button onClick={() => setActivePillar(null)} style={s.backBtn}>&larr; Back to Dashboard</button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '24px 0 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 32 }}>{currentPillar.icon}</span>
          <h2 style={{ margin: 0 }}>{currentPillar.label}</h2>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => { setShowForm(!showForm); setFormType('milestone') }} style={s.addBtn}>{showForm && formType === 'milestone' ? 'Cancel' : '+ Milestone'}</button>
          <button onClick={() => { setShowForm(!showForm); setFormType('note') }} style={{ ...s.addBtn, background: '#8e44ad' }}>{showForm && formType === 'note' ? 'Cancel' : '+ Note'}</button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleAddEntry} style={s.form}>
          <div style={{ fontSize: 13, fontWeight: 600, color: formType === 'milestone' ? '#4a90d9' : '#8e44ad', marginBottom: 4 }}>
            {formType === 'milestone' ? '📌 New Milestone (goal/target)' : '📝 New Note (observation/record)'}
          </div>
          <input type="text" placeholder={currentPillar.placeholder} value={formTitle} onChange={e => setFormTitle(e.target.value)} style={s.input} autoFocus />
          <textarea placeholder="Details (optional)" value={formContent} onChange={e => setFormContent(e.target.value)} style={{ ...s.input, minHeight: 60, resize: 'vertical' }} />
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {formType === 'milestone' && (
              <select value={formAgeBand} onChange={e => setFormAgeBand(e.target.value)} style={{ ...s.input, maxWidth: 140 }}>
                <option value="">Age band...</option>
                <option value="0-5">0–5</option>
                <option value="6-12">6–12</option>
                <option value="13-18">13–18</option>
                <option value="18-25">18–25</option>
                <option value="25-35">25–35</option>
              </select>
            )}
            {formType === 'note' && (
              <input type="number" placeholder="Age" value={formAge} onChange={e => setFormAge(e.target.value)} style={{ ...s.input, maxWidth: 100 }} min="0" max="35" />
            )}
            <input type="number" placeholder="Score 1-5" value={formScore} onChange={e => setFormScore(e.target.value)} style={{ ...s.input, maxWidth: 100 }} min="1" max="5" />
            <button type="submit" style={s.submitBtn}>Save</button>
          </div>
        </form>
      )}

      {/* Milestones by age band */}
      {bandOrder.filter(b => grouped[b]).map(band => (
        <div key={band} style={{ marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 8px', fontSize: 14, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>Ages {band}</h3>
          {grouped[band].map(m => renderItem(m, true))}
        </div>
      ))}

      {/* User notes */}
      {notes.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>Notes & Observations</h3>
          {notes.map(e => renderItem(e, true))}
        </div>
      )}
    </div>
  )
}

const s = {
  container: { maxWidth: 900, margin: '0 auto', padding: '32px 24px', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', color: '#1a1a1a' },
  back: { color: '#4a90d9', textDecoration: 'none', fontSize: 14 },
  backBtn: { background: 'none', border: 'none', color: '#4a90d9', cursor: 'pointer', fontSize: 14, padding: 0 },
  profileHeader: { display: 'flex', alignItems: 'center', gap: 20, margin: '24px 0 32px', padding: 24, background: 'linear-gradient(135deg, #f8f9ff, #f0f4ff)', borderRadius: 16 },
  bigAvatar: { width: 72, height: 72, borderRadius: '50%', background: 'linear-gradient(135deg, #667eea, #764ba2)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30, fontWeight: 600, flexShrink: 0 },
  name: { margin: 0, fontSize: 26 },
  meta: { margin: '4px 0 0', color: '#666', fontSize: 15 },
  sectionTitle: { margin: '0 0 16px', fontSize: 18, fontWeight: 600, color: '#444' },
  pillarGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 },
  pillarCard: { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 20, background: '#fff', border: '1px solid #e8e8e8', borderRadius: 12, cursor: 'pointer', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' },
  coreMetric: { marginTop: 40, padding: 24, background: '#fffbf0', border: '1px solid #f0e6d0', borderRadius: 12, textAlign: 'center' },
  addBtn: { padding: '10px 20px', background: '#4a90d9', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 },
  form: { display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20, padding: 20, background: '#f8f9ff', borderRadius: 12 },
  input: { padding: '10px 14px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14, width: '100%', boxSizing: 'border-box' },
  submitBtn: { padding: '10px 24px', background: '#2ecc71', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 },
  cancelBtn: { padding: '10px 24px', background: '#eee', color: '#333', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14 },
  milestone: { display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', marginBottom: 6, background: '#fff', borderRadius: 8 },
  statusBtn: { background: 'none', border: 'none', cursor: 'pointer', padding: 4, lineHeight: 1 },
  categoryBadge: { fontSize: 10, padding: '2px 8px', background: '#f5f5f5', borderRadius: 10, color: '#888', whiteSpace: 'nowrap' },
  scoreBadge: { fontSize: 10, padding: '2px 8px', background: '#efe', borderRadius: 10, color: '#464', whiteSpace: 'nowrap' },
  editBtn: { background: 'none', border: 'none', color: '#aaa', fontSize: 14, cursor: 'pointer', padding: '0 4px' },
  deleteBtn: { background: 'none', border: 'none', color: '#ccc', fontSize: 18, cursor: 'pointer', padding: '0 4px', lineHeight: 1 },
  roadmap: { display: 'flex', flexDirection: 'column', gap: 0, position: 'relative', paddingLeft: 20 },
  roadmapPhase: { display: 'flex', gap: 12, padding: '12px 16px', borderLeft: '2px solid #e8e8e8', marginLeft: 6 },
  roadmapActive: { background: '#f0f6ff', borderRadius: 8, borderLeft: '2px solid #4a90d9' },
  roadmapDot: { position: 'relative', left: -27, display: 'flex', alignItems: 'center' },
}
