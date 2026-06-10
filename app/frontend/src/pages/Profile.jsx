import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchProfile, fetchEntries, createEntry, updateEntry, deleteEntry, uploadAttachments, fetchAttachments, deleteAttachment, fetchChildren, uploadAvatar, fetchBounties, createBounty, updateBounty, deleteBounty } from '../services/api'
import AvatarCrop from '../components/AvatarCrop'
import Economy from './Economy'

const PILLARS = [
  { key: 'spiritual', label: 'Spiritual', icon: '✝️', placeholder: "e.g. 'First prayer unprompted'", about: "Spiritual formation tracks the development of an examined faith — not blind belief, not rebellion. It progresses from family prayers and Bible stories through theology, apologetics, and competing worldviews, culminating in personal convictions that have been tested, owned, and can be articulated. The goal is a faith that survives challenge because it has already faced it." },
  { key: 'financial', label: 'Financial', icon: '💰', placeholder: "e.g. 'Opened savings account'", about: "Financial development builds real investment literacy from birth through generational wealth planning. Starting with savings jars and compound interest stories, progressing through custodial accounts, Roth IRAs, portfolio allocation, and behavioral finance. The child learns not just to save but to understand markets, manage risk, and eventually build wealth structures that outlast them." },
  { key: 'education', label: 'Education & Career', icon: '🎓', placeholder: "e.g. 'Joined robotics club'", about: "Education & Career tracks interests, aptitudes, and experiences across all valid paths — college, trade, military, entrepreneurship. Early years expose without directing. Adolescence tracks emerging strengths through job shadowing, internships, and projects. Adulthood tracks specialization and mastery. All outcomes are valid; the metric is fit, not prestige." },
  { key: 'character', label: 'Character', icon: '🛡️', placeholder: "e.g. 'Admitted mistake to teacher'", about: "Character is the pillar most parents ignore. It tracks responsibility, courage, compassion, and discipline annually — not as abstract virtues but as observable behaviors. Can they admit mistakes? Finish hard things? Handle criticism? Case studies of real figures (MLK, Malcolm X, Goggins, Daryl Davis) teach analysis without hero worship through the sacramental ladder framework." },
  { key: 'life_skills', label: 'Life Skills', icon: '🔧', placeholder: "e.g. 'Cooked first meal alone'", about: "Life Skills ensures that by age 18 the child can cook, clean, do laundry, manage money, drive, perform first aid, and navigate digital security. By 35: home ownership literacy, legal literacy, estate planning, and community leadership. These are the competencies that prevent capable adults from being helpless in daily life." },
  { key: 'heritage', label: 'Heritage & Language', icon: '🌳', placeholder: "e.g. 'Reading chapter books in Spanish'", about: "Heritage & Language combines identity investigation ('Who do you think you are?') with active bilingual development. It tracks family origins, stories, artifacts, and traditions alongside a full language comprehension pathway — phonology, vocabulary, grammar, discourse, pragmatics, and literacy. Family participation roles ensure language transmission doesn't rest on one person. The goal: by 35 they inherit a map, not just money, and can transmit their languages to their own children." },
  { key: 'economy', label: 'Family Economy', icon: '⚖️', placeholder: "e.g. 'Completed first Silver task'", about: "Family Economy separates citizenship (unpaid family duties) from contribution (earned bounties). It teaches that value creation creates opportunity, character determines eligibility, trust unlocks responsibility, and responsibility unlocks freedom. Tiers progress from household help through competence, stewardship, initiative, and eventually entrepreneurship — mirroring how the adult world actually works." },
  { key: 'resilience', label: 'Resilience', icon: '🏔️', placeholder: "e.g. 'Discussed career pressure'", about: "Environmental Resilience maps the failure modes of every high-performance career path before the child enters one. It teaches: every field has a substance culture, institutions will frame your destruction as personal failure, and sustainable excellence beats unsustainable brilliance. The ADAPT framework (Assess, Detect, Alternatives, Protect, Threshold) is applied before entering any high-pressure environment." },
  { key: 'dimensional_navigation', label: 'Life Navigation', icon: '🧭', placeholder: "e.g. 'Identified hidden consequence'", about: "Life Navigation is the meta-pillar underpinning the entire system. It defines dimensions (Knowledge, Character, Faith, Relationships, Stewardship, Legacy, Responsibility, Wisdom, Freedom) and the navigational forces acting within them (Position, Azimuth, Velocity, Acceleration, Current, Time, Course Correction). It includes the Golden Rule of Consequence, the Circuit Breaker against abuse, horizons of perception from immediate through eternal, and the radius of influence from self through civilization. The goal is not prediction — it is perception." },
  { key: 'civic', label: 'Civic & Institutional', icon: '🏛️', placeholder: "e.g. 'Attended town council meeting'", about: "Civic, Economic & Institutional Navigation teaches how society actually functions — not as spectators watching presidents and CEOs, but as participants in overlapping systems. Voting is not the only vote: money, time, attention, labor, purchases, and investment are all forms of influence. It covers layers of governance from self through civilization, ownership as participation, the visibility problem (most influence is local/invisible), civic symbol literacy (reading political cartoons, propaganda, and public messaging for hidden power structures), and institutional stewardship. The goal is informed citizens who understand that society is not happening around them — they are already shaping it." },
]

const STATUS_COLORS = { not_started: '#e0e0e0', introduced: '#a0d2db', in_progress: '#f5a623', practicing: '#c39bd3', complete: '#2ecc71', mastered: '#1a7a4c', pending: '#e0e0e0' }
const STATUS_LABELS = { not_started: '○', introduced: '◔', in_progress: '◑', practicing: '◕', complete: '●', mastered: '★', pending: '○' }
const STATUS_CYCLE = { not_started: 'introduced', introduced: 'in_progress', in_progress: 'practicing', practicing: 'complete', complete: 'mastered', mastered: 'not_started', pending: 'in_progress' }
const STATUS_DISPLAY = { not_started: 'Not Started', introduced: 'Introduced', in_progress: 'In Progress', practicing: 'Practicing', complete: 'Complete', mastered: 'Mastered', pending: 'Pending' }

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
  const [showEventForm, setShowEventForm] = useState(false)
  const [eventTitle, setEventTitle] = useState('')
  const [eventContent, setEventContent] = useState('')
  const [eventFiles, setEventFiles] = useState([])
  const [eventMilestone, setEventMilestone] = useState('') // entry id to mark complete
  const [eventAgeBand, setEventAgeBand] = useState('')
  const [attachmentsMap, setAttachmentsMap] = useState({}) // entryId -> [attachments]
  const [expandedAttachments, setExpandedAttachments] = useState(null) // entry id or null
  const [expandedMilestone, setExpandedMilestone] = useState(null) // entry id showing sub-entries
  const [pillarTab, setPillarTab] = useState('milestones') // 'milestones' or 'bounties'
  const [pillarBounties, setPillarBounties] = useState([])
  const [showPillarBountyForm, setShowPillarBountyForm] = useState(false)
  const [pBountyForm, setPBountyForm] = useState({ tier: 'bronze', title: '', description: '', reward_amount: '' })
  const [childrenMap, setChildrenMap] = useState({}) // entryId -> [children]
  const [subFormParent, setSubFormParent] = useState(null) // entry id for sub-entry form
  const [subTitle, setSubTitle] = useState('')
  const [subContent, setSubContent] = useState('')
  const [subType, setSubType] = useState('note') // note, event, evidence
  const [avatarSrc, setAvatarSrc] = useState(null) // data URL for crop modal
  const [avatarFile, setAvatarFile] = useState(null) // original File object

  useEffect(() => { fetchProfile(id).then(setProfile); loadCounts() }, [id])

  const loadCounts = () => {
    fetchEntries(id).then(data => {
      if (!Array.isArray(data)) return
      setAllRaw(data)
      const counts = {}
      data.forEach(e => {
        if (!counts[e.pillar]) counts[e.pillar] = { total: 0, complete: 0 }
        if (e.is_milestone) counts[e.pillar].total++
        if (e.status === 'complete' || e.status === 'mastered') counts[e.pillar].complete++
      })
      setAllCounts(counts)
    })
  }

  const loadEntries = () => {
    if (activePillar) fetchEntries(id, activePillar).then(data => setEntries(Array.isArray(data) ? data : []))
  }

  useEffect(() => { loadEntries() }, [id, activePillar])
  useEffect(() => {
    if (activePillar && activePillar !== '__economy__') {
      fetchBounties(id, activePillar).then(d => Array.isArray(d) && setPillarBounties(d))
    }
  }, [id, activePillar, pillarTab])

  const handleAddEntry = async (e) => {
    e.preventDefault()
    if (!formTitle.trim()) return
    await createEntry(id, {
      pillar: activePillar,
      title: formTitle.trim(),
      content: formContent.trim() || null,
      age_band: formAgeBand || null,
      category: formAgeBand ? ({'0-5':'Foundation','6-12':'Exploration','13-18':'Formation','18-25':'Launch','25-35':'Stewardship'}[formAgeBand] || null) : null,
      entry_type: 'milestone',
      is_milestone: 1,
    })
    setFormTitle(''); setFormContent(''); setFormAgeBand(''); setShowForm(false)
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

  const handleAddEvent = async (e) => {
    e.preventDefault()
    if (!eventTitle.trim()) return
    // Create the event entry
    const entry = await createEntry(id, {
      pillar: activePillar,
      title: eventTitle.trim(),
      content: eventContent.trim() || null,
      age_band: eventAgeBand || null,
      category: eventAgeBand ? ({'0-5':'Foundation','6-12':'Exploration','13-18':'Formation','18-25':'Launch','25-35':'Stewardship'}[eventAgeBand] || null) : null,
      is_milestone: 0,
    })
    // Upload files if any
    if (eventFiles.length > 0 && entry && entry.id) {
      await uploadAttachments(id, entry.id, eventFiles)
    }
    // Mark linked milestone as complete if selected
    if (eventMilestone && entry) {
      await updateEntry(id, parseInt(eventMilestone), { status: 'complete' })
    }
    setEventTitle(''); setEventContent(''); setEventFiles([]); setEventMilestone(''); setEventAgeBand(''); setShowEventForm(false)
    loadEntries(); loadCounts()
  }

  const loadAttachments = async (entryId) => {
    if (expandedAttachments === entryId) { setExpandedAttachments(null); return }
    const atts = await fetchAttachments(id, entryId)
    setAttachmentsMap(prev => ({ ...prev, [entryId]: Array.isArray(atts) ? atts : [] }))
    setExpandedAttachments(entryId)
  }

  const handleDeleteAttachment = async (entryId, attId) => {
    if (!confirm('Delete this attachment?')) return
    await deleteAttachment(id, entryId, attId)
    const atts = await fetchAttachments(id, entryId)
    setAttachmentsMap(prev => ({ ...prev, [entryId]: Array.isArray(atts) ? atts : [] }))
  }

  const toggleMilestoneExpand = async (entryId) => {
    if (expandedMilestone === entryId) { setExpandedMilestone(null); return }
    const kids = await fetchChildren(id, entryId)
    setChildrenMap(prev => ({ ...prev, [entryId]: Array.isArray(kids) ? kids : [] }))
    setExpandedMilestone(entryId)
  }

  const handleAddSubEntry = async (e, parentId) => {
    e.preventDefault()
    if (!subTitle.trim()) return
    const parent = entries.find(en => en.id === parentId)
    await createEntry(id, {
      pillar: activePillar,
      parent_id: parentId,
      entry_type: subType,
      title: subTitle.trim(),
      content: subContent.trim() || null,
      age_band: parent?.age_band || null,
      is_milestone: 0,
    })
    const kids = await fetchChildren(id, parentId)
    setChildrenMap(prev => ({ ...prev, [parentId]: Array.isArray(kids) ? kids : [] }))
    setSubTitle(''); setSubContent(''); setSubFormParent(null); setSubType('note')
    loadCounts()
  }

  const handlePillarBountySubmit = async (e) => {
    e.preventDefault()
    if (!pBountyForm.title.trim()) return
    await createBounty(id, { ...pBountyForm, title: pBountyForm.title.trim(), description: pBountyForm.description.trim() || null, reward_amount: Math.round((parseFloat(pBountyForm.reward_amount) || 0) * 100), pillar: activePillar })
    setShowPillarBountyForm(false)
    setPBountyForm({ tier: 'bronze', title: '', description: '', reward_amount: '' })
    fetchBounties(id, activePillar).then(d => Array.isArray(d) && setPillarBounties(d))
  }

  const cyclePillarBountyStatus = async (b) => {
    const next = { available: 'claimed', claimed: 'complete', complete: 'paid' }[b.status]
    if (!next) return
    await updateBounty(id, b.id, { status: next })
    fetchBounties(id, activePillar).then(d => Array.isArray(d) && setPillarBounties(d))
  }

  const handleDeletePillarBounty = async (bountyId) => {
    if (!confirm('Delete this bounty?')) return
    await deleteBounty(id, bountyId)
    fetchBounties(id, activePillar).then(d => Array.isArray(d) && setPillarBounties(d))
  }

  const handleAvatarSelect = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setAvatarFile(file)
    const reader = new FileReader()
    reader.onload = () => setAvatarSrc(reader.result)
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const handleAvatarCropped = async (blob) => {
    const updated = await uploadAvatar(id, avatarFile, blob)
    setProfile(updated)
    setAvatarSrc(null)
    setAvatarFile(null)
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
        {avatarSrc && <AvatarCrop imageSrc={avatarSrc} onComplete={handleAvatarCropped} onCancel={() => { setAvatarSrc(null); setAvatarFile(null) }} />}
        <Link to="/" style={s.back}>&larr; All Profiles</Link>
        <div style={s.profileHeader}>
          <label style={{ cursor: 'pointer', position: 'relative' }} title="Click to change photo">
            {profile.avatar ? (
              <img src={`/api/uploads/${profile.avatar}`} alt={profile.name} style={s.bigAvatar} />
            ) : (
              <div style={s.bigAvatarPlaceholder}>{profile.name.charAt(0)}</div>
            )}
            <input type="file" accept="image/*" onChange={handleAvatarSelect} style={{ display: 'none' }} />
            <span style={s.avatarEdit}>📷</span>
          </label>
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
                      const done = pillarEntries.filter(e => e.status === 'complete' || e.status === 'mastered').length
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

  const renderItem = (item, showDelete = true, isChild = false) => {
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
    const atts = attachmentsMap[item.id] || []
    const kids = childrenMap[item.id] || []
    const isMilestone = item.is_milestone === 1
    const isExpanded = expandedMilestone === item.id
    return (
      <div key={item.id} style={{ marginBottom: 6, marginLeft: isChild ? 24 : 0 }}>
        <div style={{ ...s.milestone, borderLeft: `3px solid ${STATUS_COLORS[item.status] || '#e0e0e0'}` }}>
          <button onClick={() => handleStatusToggle(item)} style={s.statusBtn} title={`Status: ${STATUS_DISPLAY[item.status] || item.status} (click to advance)`}>
            <span style={{ color: STATUS_COLORS[item.status] || '#e0e0e0', fontSize: 18 }}>{STATUS_LABELS[item.status] || '○'}</span>
          </button>
          <div style={{ flex: 1, cursor: isMilestone ? 'pointer' : 'default' }} onClick={() => isMilestone && toggleMilestoneExpand(item.id)}>
            <span style={{ textDecoration: item.status === 'complete' || item.status === 'mastered' ? 'line-through' : 'none', color: item.status === 'mastered' ? '#1a7a4c' : item.status === 'complete' ? '#888' : '#1a1a1a' }}>{item.title}</span>
            {item.content && <p style={{ margin: '4px 0 0', fontSize: 12, color: '#888' }}>{item.content}</p>}
            {isMilestone && <span style={{ fontSize: 10, color: '#bbb', marginLeft: 4 }}>{isExpanded ? '▾' : '▸'} details</span>}
          </div>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 8, background: STATUS_COLORS[item.status] || '#e0e0e0', color: '#fff', whiteSpace: 'nowrap' }}>{STATUS_DISPLAY[item.status] || item.status}</span>
            {item.category && <span style={s.categoryBadge}>{item.category}</span>}
            {item.score != null && <span style={s.scoreBadge}>{item.score}/5</span>}
            <button onClick={() => loadAttachments(item.id)} style={s.editBtn} title="Attachments">📎</button>
            <button onClick={() => startEdit(item)} style={s.editBtn} title="Edit">✎</button>
            {showDelete && <button onClick={() => handleDelete(item.id)} style={s.deleteBtn} title="Delete">&times;</button>}
          </div>
        </div>
        {expandedAttachments === item.id && (
          <div style={s.attachPanel}>
            {atts.length === 0 && <span style={{ fontSize: 12, color: '#999' }}>No attachments</span>}
            {atts.map(a => (
              <div key={a.id} style={s.attachItem}>
                {a.mime_type.startsWith('image/') ? (
                  <a href={`/api/uploads/${a.filename}`} target="_blank" rel="noreferrer">
                    <img src={`/api/uploads/${a.filename}`} alt={a.original_name} style={{ maxWidth: 120, maxHeight: 80, borderRadius: 4 }} />
                  </a>
                ) : a.mime_type.startsWith('video/') ? (
                  <video src={`/api/uploads/${a.filename}`} controls style={{ maxWidth: 180, maxHeight: 100, borderRadius: 4 }} />
                ) : (
                  <a href={`/api/uploads/${a.filename}`} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: '#4a90d9' }}>📄 {a.original_name}</a>
                )}
                <button onClick={() => handleDeleteAttachment(item.id, a.id)} style={{ ...s.deleteBtn, fontSize: 14 }} title="Remove">×</button>
              </div>
            ))}
          </div>
        )}
        {/* Sub-entries panel for milestones */}
        {isMilestone && isExpanded && (
          <div style={s.subPanel}>
            {kids.length > 0 && kids.map(child => (
              <div key={child.id} style={s.subEntry}>
                <span style={{ fontSize: 11, color: '#666', fontWeight: 600, textTransform: 'uppercase' }}>{child.entry_type}</span>
                <span style={{ fontSize: 13 }}>{child.title}</span>
                {child.content && <p style={{ margin: '2px 0 0', fontSize: 11, color: '#999' }}>{child.content}</p>}
                <span style={{ fontSize: 10, color: '#bbb' }}>{new Date(child.created_at).toLocaleDateString()}</span>
              </div>
            ))}
            {subFormParent === item.id ? (
              <form onSubmit={(e) => handleAddSubEntry(e, item.id)} style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['note','event','evidence'].map(t => (
                    <label key={t} style={{ fontSize: 11, cursor: 'pointer' }}>
                      <input type="radio" name="subType" value={t} checked={subType === t} onChange={() => setSubType(t)} style={{ marginRight: 3 }} />
                      {t}
                    </label>
                  ))}
                </div>
                <input type="text" placeholder="What happened or was observed?" value={subTitle} onChange={e => setSubTitle(e.target.value)} style={{ ...s.input, fontSize: 12 }} autoFocus />
                <textarea placeholder="Details (optional)" value={subContent} onChange={e => setSubContent(e.target.value)} style={{ ...s.input, fontSize: 12, minHeight: 40, resize: 'vertical' }} />
                <div style={{ display: 'flex', gap: 8 }}>
                  <button type="submit" style={{ ...s.submitBtn, fontSize: 11, padding: '6px 14px' }}>Add</button>
                  <button type="button" onClick={() => setSubFormParent(null)} style={{ ...s.cancelBtn, fontSize: 11, padding: '6px 14px' }}>Cancel</button>
                </div>
              </form>
            ) : (
              <button onClick={() => setSubFormParent(item.id)} style={{ fontSize: 11, color: '#4a90d9', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 0', textAlign: 'left' }}>+ Add note, event, or evidence</button>
            )}
          </div>
        )}
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
          {pillarTab === 'milestones' && <button onClick={() => { setShowForm(!showForm); setFormType('milestone') }} style={s.addBtn}>{showForm ? 'Cancel' : '+ Milestone'}</button>}
        </div>
      </div>

      <details style={s.aboutDropdown}>
        <summary style={s.aboutSummary}>About this Pillar</summary>
        <p style={s.aboutText}>{currentPillar.about}</p>
      </details>

      {/* Tab toggle */}
      <div style={s.tabRow}>
        <button onClick={() => setPillarTab('milestones')} style={pillarTab === 'milestones' ? s.tabActive : s.tab}>Milestones</button>
        <button onClick={() => setPillarTab('bounties')} style={pillarTab === 'bounties' ? s.tabActive : s.tab}>Bounties</button>
      </div>

      {pillarTab === 'bounties' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <button onClick={() => setShowPillarBountyForm(!showPillarBountyForm)} style={s.addBtn}>{showPillarBountyForm ? 'Cancel' : '+ New Bounty'}</button>
          </div>
          {showPillarBountyForm && (
            <form onSubmit={handlePillarBountySubmit} style={s.form}>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <select value={pBountyForm.tier} onChange={e => setPBountyForm({ ...pBountyForm, tier: e.target.value })} style={{ ...s.input, maxWidth: 130 }}>
                  <option value="bronze">Bronze</option>
                  <option value="silver">Silver</option>
                  <option value="gold">Gold</option>
                  <option value="platinum">Platinum</option>
                </select>
                <input placeholder="Task title" value={pBountyForm.title} onChange={e => setPBountyForm({ ...pBountyForm, title: e.target.value })} style={{ ...s.input, flex: 1 }} autoFocus />
                <input placeholder="$ amount" type="number" step="0.25" min="0" value={pBountyForm.reward_amount} onChange={e => setPBountyForm({ ...pBountyForm, reward_amount: e.target.value })} style={{ ...s.input, maxWidth: 90 }} />
              </div>
              <input placeholder="Description (optional)" value={pBountyForm.description} onChange={e => setPBountyForm({ ...pBountyForm, description: e.target.value })} style={s.input} />
              <button type="submit" style={s.submitBtn}>Create Bounty</button>
            </form>
          )}
          {pillarBounties.length === 0 && !showPillarBountyForm && (
            <p style={{ color: '#888', textAlign: 'center', padding: 20 }}>No bounties for this pillar yet.</p>
          )}
          {pillarBounties.map(b => (
            <div key={b.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', background: '#fff', borderRadius: 6, marginBottom: 4 }}>
              <button onClick={() => cyclePillarBountyStatus(b)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}>
                <span style={{ fontSize: 16, color: b.status === 'paid' ? '#2ecc71' : b.status === 'complete' ? '#27ae60' : b.status === 'claimed' ? '#f5a623' : '#ddd' }}>
                  {b.status === 'paid' ? '✓' : b.status === 'complete' ? '●' : b.status === 'claimed' ? '◐' : '○'}
                </span>
              </button>
              <div style={{ flex: 1 }}>
                <span style={{ textDecoration: b.status === 'paid' ? 'line-through' : 'none' }}>{b.title}</span>
                {b.description && <p style={{ margin: '2px 0 0', fontSize: 12, color: '#888' }}>{b.description}</p>}
              </div>
              <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 8, background: {'bronze':'#fdf0e0','silver':'#f0f0f0','gold':'#fff8e0','platinum':'#e8f0ff'}[b.tier], color: {'bronze':'#cd7f32','silver':'#888','gold':'#b8860b','platinum':'#4a90d9'}[b.tier] }}>{b.tier}</span>
              <span style={{ fontWeight: 600, fontSize: 14 }}>${(b.reward_amount / 100).toFixed(2)}</span>
              <button onClick={() => handleDeletePillarBounty(b.id)} style={{ background: 'none', border: 'none', color: '#ccc', fontSize: 18, cursor: 'pointer' }}>&times;</button>
            </div>
          ))}
        </div>
      )}

      {pillarTab === 'milestones' && showForm && (
        <form onSubmit={handleAddEntry} style={s.form}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#4a90d9', marginBottom: 4 }}>
            📌 New Milestone (goal/target)
          </div>
          <input type="text" placeholder={currentPillar.placeholder} value={formTitle} onChange={e => setFormTitle(e.target.value)} style={s.input} autoFocus />
          <textarea placeholder="Details (optional)" value={formContent} onChange={e => setFormContent(e.target.value)} style={{ ...s.input, minHeight: 60, resize: 'vertical' }} />
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <select value={formAgeBand} onChange={e => setFormAgeBand(e.target.value)} style={{ ...s.input, maxWidth: 140 }}>
              <option value="">Age band...</option>
              <option value="0-5">0–5</option>
              <option value="6-12">6–12</option>
              <option value="13-18">13–18</option>
              <option value="18-25">18–25</option>
              <option value="25-35">25–35</option>
            </select>
            <button type="submit" style={s.submitBtn}>Save</button>
          </div>
        </form>
      )}

      {/* Milestones by age band */}
      {pillarTab === 'milestones' && bandOrder.filter(b => grouped[b]).map(band => (
        <div key={band} style={{ marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 8px', fontSize: 14, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>Ages {band}</h3>
          {grouped[band].map(m => renderItem(m, true))}
        </div>
      ))}

    </div>
  )
}

const s = {
  container: { maxWidth: 900, margin: '0 auto', padding: '32px 24px', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', color: '#1a1a1a' },
  back: { color: '#4a90d9', textDecoration: 'none', fontSize: 14 },
  backBtn: { background: 'none', border: 'none', color: '#4a90d9', cursor: 'pointer', fontSize: 14, padding: 0 },
  profileHeader: { display: 'flex', alignItems: 'center', gap: 20, margin: '24px 0 32px', padding: 24, background: 'linear-gradient(135deg, #f8f9ff, #f0f4ff)', borderRadius: 16 },
  bigAvatar: { width: 72, height: 72, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 },
  bigAvatarPlaceholder: { width: 72, height: 72, borderRadius: '50%', background: 'linear-gradient(135deg, #667eea, #764ba2)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30, fontWeight: 600, flexShrink: 0 },
  avatarEdit: { position: 'absolute', bottom: 0, right: 0, background: '#fff', borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.2)' },
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
  attachPanel: { padding: '8px 12px 8px 40px', display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', background: '#fafafa', borderRadius: '0 0 8px 8px', marginTop: -2 },
  attachItem: { display: 'flex', alignItems: 'center', gap: 6, padding: 4, background: '#fff', borderRadius: 6, border: '1px solid #eee' },
  subPanel: { marginLeft: 32, padding: '8px 12px', background: '#f9f9ff', borderLeft: '2px solid #e0e0f0', borderRadius: '0 8px 8px 0', marginTop: 2, maxHeight: 240, overflowY: 'auto' },
  subEntry: { display: 'flex', flexDirection: 'column', gap: 2, padding: '6px 0', borderBottom: '1px solid #f0f0f0' },
  aboutDropdown: { marginBottom: 16, background: '#f8f9ff', border: '1px solid #e8e8f0', borderRadius: 10, padding: '0 16px' },
  aboutSummary: { padding: '12px 0', cursor: 'pointer', fontSize: 13, fontWeight: 600, color: '#666', listStyle: 'none' },
  aboutText: { margin: '0 0 12px', fontSize: 13, lineHeight: 1.6, color: '#444' },
  tabRow: { display: 'flex', gap: 0, marginBottom: 16, borderBottom: '2px solid #e8e8e8' },
  tab: { padding: '10px 20px', background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: '#888', borderBottom: '2px solid transparent', marginBottom: -2 },
  tabActive: { padding: '10px 20px', background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: '#4a90d9', fontWeight: 600, borderBottom: '2px solid #4a90d9', marginBottom: -2 },
}
