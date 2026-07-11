import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchProfile, fetchEntries, createEntry, updateEntry, deleteEntry, uploadAttachments, fetchAttachments, deleteAttachment, fetchChildren, uploadAvatar, fetchBounties, createBounty, updateBounty, deleteBounty, reseedProfile, fetchPillarGuide, fetchPrograms, fetchDiscernmentCategories, fetchDiscernmentEntries, createDiscernmentEntry, deleteDiscernmentEntry, fetchResearchTopics, fetchLessons, createLesson, createLessonResponse, deleteLesson, updateLesson } from '../services/api'
import AvatarCrop from '../components/AvatarCrop'
import MiniMarkdown from '../components/MiniMarkdown'
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
  { key: 'scientific_reality_testing', label: 'Scientific Method', icon: '🔬', placeholder: "e.g. 'Conducted first experiment'", about: "Scientific Method & Reality Testing teaches disciplined contact with reality — not merely academic science. It trains the child to distinguish what they know from what they assume, what they feel from what they can test, and what should change when new evidence appears. Includes introspective testing of habits and routines, claim confidence levels, institutional humility, and the knowledge decay cycle (how truths are discovered, corrupted, forgotten, and rediscovered). The goal is a person harder to deceive, easier to correct, and equipped for both measurable reality and deeper mystery." },
  { key: 'inheritance_burden_stewardship', label: 'Inheritance & Stewardship', icon: '📜', placeholder: "e.g. 'Mapped family financial patterns'", about: "Inheritance, Burden & Stewardship teaches the child to receive inheritance without naivety and evaluate burden without bitterness. Every generation hands the next a mixed estate: treasure, debt, wisdom, trauma, institutions, and unfinished work. This pillar covers financial, cultural, moral, civic, institutional, and health inheritance. It teaches the difference between fault and responsibility, honor without blindness, and the Bag Principle: open it, inventory it, keep what is good, repair what is damaged, discard what is poisonous, and prepare a better one for those who come after." },
  { key: 'catholic_formation', label: 'Catholic Formation', icon: '⛪', placeholder: "e.g. 'First Reconciliation received'", about: "Catholic Sacramental Formation tracks the child's Catholic life from baptism through adult vocation — not as checkbox spirituality but as examined, sacramental, safe, and transmissible faith. It includes sacramental records, domestic church practices, authority literacy, safe-environment formation, transmission audit (what was inherited, neglected, corrupted, or repaired), and the distinction between faithful discernment and both cynicism and naivety. The goal is a Catholic life that is owned, not merely inherited." },
  { key: 'secular_sacred_formation', label: 'Secular Sacred', icon: '🌅', placeholder: "e.g. 'Studied origin accounts across cultures'", about: "Secular Sacred Formation & Civilizational Literacy preserves proper formation even when belief is uncertain, rejected, or recovering. It teaches the human realities that religion has always addressed — origin, death, sacrifice, moral repair, ritual, authority, belonging — in language accessible to the atheist, agnostic, or wounded. The child can question, doubt, leave, and still remain capable of serious formation. The door home must remain visible. A child may become atheist and still come home." },
]

const LIFE_CHART_SECTIONS = [
  { number: 1, title: 'Before Conception', question: 'What world was prepared before I arrived?', examples: ['Ancestors', 'Family choices', 'Language & culture', 'Wealth or debt', 'Wars, migration, institutions'] },
  { number: 2, title: 'Conception to Birth', question: 'What did others give before I could give anything back?', examples: ['Dependent life', 'Protection', 'Care from others', 'Worth before achievement'] },
  { number: 3, title: 'Childhood & Formation', question: 'What kind of person am I becoming?', examples: ['Body', 'Mind', 'Faith / meaning', 'Character', 'Skills and responsibility'] },
  { number: 4, title: 'Adulthood & Responsibility', question: 'What responsibilities become mine?', examples: ['Work and vocation', 'Family', 'Stewardship', 'Service', 'Civic duty'] },
  { number: 5, title: 'Death', question: 'What should be repaired, preserved, or entrusted before death?', examples: ['Mortality', 'Reconciliation', 'Estate and records', 'Memory', 'Spiritual questions'] },
  { number: 6, title: 'After Death / Legacy', question: 'What will others inherit because I lived?', examples: ['Spiritual horizon', 'Children and students', 'Institutions', 'Traditions', 'Harm repaired or transmitted'] },
]

const BELONGING_VARIANTS = {
  religious: {
    label: 'Religious',
    image: '/reference_images/expanding_breadth_religious.png',
    alt: 'Expanding Breadth of Belonging religious chart showing responsibility widening from Person through Family, Kin, Parish, Local Community, Nation, Church, Humanity, and God.',
    summary: 'Person → Family → Kin / Tribe → Parish → Local Community → Nation → Church → Humanity → God',
    rings: [
      ['Person', 'My own life, conscience, choices.'],
      ['Family', 'Those entrusted directly to me.'],
      ['Kin / Tribe', 'Extended bonds, ancestry, mutual support.'],
      ['Parish', 'Worship and local spiritual community.'],
      ['Local Community', 'Neighbors, schools, local service, and civic life.'],
      ['Nation', 'Shared law, history, duty, and protection.'],
      ['Church', 'The wider body of belief and tradition.'],
      ['Humanity', 'Care for all people.'],
      ['God', 'The highest horizon of meaning, order, and accountability.'],
    ],
  },
  secular: {
    label: 'Secular',
    image: '/reference_images/expanding_breadth_secular.png',
    alt: 'Expanding Breadth of Belonging secular chart showing responsibility widening from Person through Family, Kin, Local Community, Civic Community, Nation, Civilization, Humanity, and Truth or Meaning.',
    summary: 'Person → Family → Kin / Tribe → Local Community → Civic Community → Nation → Civilization → Humanity → Truth / Meaning',
    rings: [
      ['Person', 'My own life, conscience, choices.'],
      ['Family', 'Those entrusted directly to me.'],
      ['Kin / Tribe', 'Extended bonds, ancestry, mutual support.'],
      ['Local Community', 'Neighbors, schools, and local belonging.'],
      ['Civic Community', 'Service, institutions, and shared responsibility.'],
      ['Nation', 'Shared law, history, duty, and protection.'],
      ['Civilization', 'Inherited knowledge, culture, and institutions.'],
      ['Humanity', 'Care for all people.'],
      ['Truth / Meaning', 'The highest horizon of reality, meaning, and accountability.'],
    ],
  },
}

const BELONGING_BOUNTY_TEMPLATE = [
  'Explain what this circle means in simple words.',
  'Name what you receive from this circle: care, language, law, worship, history, opportunity, or belonging.',
  'Name what you owe to this circle: honesty, respect, service, gratitude, repair, participation, or stewardship.',
  'Identify what can corrupt this circle: selfishness, tribalism, neglect, abuse, corruption, arrogance, or blind obedience.',
  'Give one real example and one family discussion question.',
  'End with a one-sentence lesson.',
]

const STATUS_COLORS = { not_started: '#e0e0e0', introduced: '#a0d2db', in_progress: '#f5a623', practicing: '#c39bd3', complete: '#2ecc71', mastered: '#1a7a4c', pending: '#e0e0e0' }
const STATUS_LABELS = { not_started: '○', introduced: '◔', in_progress: '◑', practicing: '◕', complete: '●', mastered: '★', pending: '○' }
const STATUS_CYCLE = { not_started: 'introduced', introduced: 'in_progress', in_progress: 'practicing', practicing: 'complete', complete: 'mastered', mastered: 'not_started', pending: 'in_progress' }
const STATUS_DISPLAY = { not_started: 'Not Started', introduced: 'Introduced', in_progress: 'In Progress', practicing: 'Practicing', complete: 'Complete', mastered: 'Mastered', pending: 'Pending' }

function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>
    if (part.startsWith('*') && part.endsWith('*')) return <em key={i}>{part.slice(1, -1)}</em>
    return part
  })
}

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
  const [editStatus, setEditStatus] = useState('')
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
  const [pBountyForm, setPBountyForm] = useState({ tier: 'bronze', title: '', description: '', reward_amount: '', age_band: '' })
  const [editingPBounty, setEditingPBounty] = useState(null)
  const [editPBForm, setEditPBForm] = useState({})
  const [childrenMap, setChildrenMap] = useState({}) // entryId -> [children]
  const [subFormParent, setSubFormParent] = useState(null) // entry id for sub-entry form
  const [subTitle, setSubTitle] = useState('')
  const [subContent, setSubContent] = useState('')
  const [subType, setSubType] = useState('note') // note, event, evidence
  const [avatarSrc, setAvatarSrc] = useState(null) // data URL for crop modal
  const [avatarFile, setAvatarFile] = useState(null) // original File object
  const [guideContent, setGuideContent] = useState(null) // markdown text for pillar guide
  const [pillarFilter, setPillarFilter] = useState('')
  const [programs, setPrograms] = useState([])
  const [activeProgram, setActiveProgram] = useState(null)
  const [researchTopics, setResearchTopics] = useState({})
  const [discernCats, setDiscernCats] = useState({})
  const [discernEntries, setDiscernEntries] = useState([])
  const [activeDiscern, setActiveDiscern] = useState(null)
  const [discernForm, setDiscernForm] = useState({ title: '', reflection: '' })
  const [lessons, setLessons] = useState([])
  const [lessonForm, setLessonForm] = useState({ title: '', source: '', url: '', transcript: '', notes: '', pillar: '', age_band: '' })
  const [showLessonForm, setShowLessonForm] = useState(false)
  const [activeLesson, setActiveLesson] = useState(null)
  const [lessonResponseForm, setLessonResponseForm] = useState({ response_type: 'rebrief', content: '' })
  const [belongingVariant, setBelongingVariant] = useState('religious')

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

  const isSpecialView = (p) => !p || p.startsWith('__')

  const loadEntries = () => {
    if (activePillar && !isSpecialView(activePillar)) fetchEntries(id, activePillar).then(data => setEntries(Array.isArray(data) ? data : []))
  }

  useEffect(() => { loadEntries() }, [id, activePillar])
  useEffect(() => {
    if (activePillar && !isSpecialView(activePillar)) {
      fetchBounties(id, activePillar).then(d => Array.isArray(d) && setPillarBounties(d))
      fetchPillarGuide(activePillar).then(d => setGuideContent(d && d.content ? d.content : null))
    } else if (activePillar === '__discernment__') {
      fetchBounties(id).then(d => Array.isArray(d) && setPillarBounties(d))
      setGuideContent(null)
    } else {
      setGuideContent(null)
    }
  }, [id, activePillar, activeDiscern, pillarTab])

  const handleAddEntry = async (e) => {
    e.preventDefault()
    if (!formTitle.trim()) return
    await createEntry(id, {
      pillar: activePillar,
      title: formTitle.trim(),
      content: formContent.trim() || null,
      age_band: formAgeBand || null,
      category: formAgeBand ? ({'0-2':'Foundation','2-3':'Foundation','3-5':'Foundation','6-12':'Exploration','13-18':'Formation','18-25':'Launch','25-35':'Stewardship'}[formAgeBand] || null) : null,
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
    setEditStatus(entry.status)
  }

  const cancelEdit = () => { setEditing(null); setEditTitle(''); setEditContent(''); setEditStatus('') }

  const saveEdit = async (entryId) => {
    if (!editTitle.trim()) return
    await updateEntry(id, entryId, { title: editTitle.trim(), content: editContent.trim() || null, status: editStatus })
    cancelEdit(); loadEntries(); loadCounts()
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
      category: eventAgeBand ? ({'0-2':'Foundation','2-3':'Foundation','3-5':'Foundation','6-12':'Exploration','13-18':'Formation','18-25':'Launch','25-35':'Stewardship'}[eventAgeBand] || null) : null,
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
    await createBounty(id, { ...pBountyForm, title: pBountyForm.title.trim(), description: pBountyForm.description.trim() || null, reward_amount: Math.round((parseFloat(pBountyForm.reward_amount) || 0) * 100), pillar: activePillar, age_band: pBountyForm.age_band || null })
    setShowPillarBountyForm(false)
    setPBountyForm({ tier: 'bronze', title: '', description: '', reward_amount: '', age_band: '' })
    fetchBounties(id, activePillar).then(d => Array.isArray(d) && setPillarBounties(d))
  }

  const handleReseedProfile = async () => {
    const result = await reseedProfile(id)
    loadEntries()
    loadCounts()
    fetchPrograms(id).then(d => Array.isArray(d) && setPrograms(d))
    if (activePillar && !isSpecialView(activePillar)) {
      fetchBounties(id, activePillar).then(d => Array.isArray(d) && setPillarBounties(d))
    }
    if (result?.detail) alert(result.detail)
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

  const startEditPBounty = (b) => {
    setEditingPBounty(b.id)
    setEditPBForm({ title: b.title, description: b.description || '', reward_amount: (b.reward_amount / 100).toFixed(2), tier: b.tier, age_band: b.age_band || '', status: b.status })
  }

  const saveEditPBounty = async (b) => {
    await updateBounty(id, b.id, { title: editPBForm.title.trim(), description: editPBForm.description.trim() || null, reward_amount: Math.round((parseFloat(editPBForm.reward_amount) || 0) * 100), status: editPBForm.status, age_band: editPBForm.age_band || null })
    setEditingPBounty(null)
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

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
          <button onClick={handleReseedProfile} style={{ ...s.addBtn, background: '#6c7a89', fontSize: 12 }} title="Add any new milestones and bounties from the planning documents to this profile. Corrects age bands on existing milestones.">🔄 Sync Milestones & Bounties</button>
        </div>

        {/* Roadmap — at-a-glance overview */}
        <h2 style={s.sectionTitle}>Roadmap</h2>
        <div className="roadmap-container" style={s.roadmap}>
          {['0-5','6-12','13-18','18-25','25-35'].map((band, i) => {
            const labels = { '0-5': 'Foundation', '6-12': 'Exploration', '13-18': 'Formation', '18-25': 'Launch', '25-35': 'Consolidation' }
            const bandGroups = { '0-5': ['0-2','2-3','3-5'], '6-12': ['6-12'], '13-18': ['13-18'], '18-25': ['18-25'], '25-35': ['25-35'] }
            const isCurrentBand = age !== null && (
              (band === '0-5' && age <= 5) || (band === '6-12' && age >= 6 && age <= 12) ||
              (band === '13-18' && age >= 13 && age <= 18) || (band === '18-25' && age >= 18 && age <= 25) ||
              (band === '25-35' && age >= 25 && age <= 35)
            )
            return (
              <details key={band} className="roadmap-phase" open={isCurrentBand} style={{ ...s.roadmapPhase, ...(isCurrentBand ? s.roadmapActive : {}) }}>
                <summary style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', listStyle: 'none' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 14, height: 14, borderRadius: '50%', background: isCurrentBand ? '#4a90d9' : '#ddd' }} />
                    <span style={{ fontWeight: 600, fontSize: 14 }}>{labels[band]}</span>
                    <span style={{ fontSize: 12, color: '#aaa', fontWeight: 400 }}>{band}</span>
                  </div>
                </summary>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8, paddingLeft: 24 }}>
                  {PILLARS.map(p => {
                    const pillarEntries = allRaw.filter(e => e.pillar === p.key && bandGroups[band].includes(e.age_band) && e.is_milestone)
                    const done = pillarEntries.filter(e => e.status === 'complete' || e.status === 'mastered').length
                    const total = pillarEntries.length
                    if (!total) return null
                    return <span key={p.key} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 8, background: done === total ? '#e8f8f0' : '#f5f5f5', color: done === total ? '#27ae60' : '#888' }}>{p.icon} {done}/{total}</span>
                  })}
                </div>
              </details>
            )
          })}
        </div>

        {/* Core Metric */}
        <div style={{ ...s.coreMetric, marginTop: 20 }}>
          <p style={{ margin: 0, fontSize: 12, color: '#888', textTransform: 'uppercase', letterSpacing: 1 }}>Core Metric</p>
          <p style={{ margin: '8px 0 0', fontSize: 18, fontStyle: 'italic' }}>"Is {profile.name.split(' ')[0]} becoming a wise, capable, kind, and independent person?"</p>
        </div>

        {/* Life Maps — dashboard-level visual cards, not pillars */}
        <h2 style={{ ...s.sectionTitle, marginTop: 32 }}>Life Maps</h2>
        <div className="pillar-grid-desktop">
          {(!pillarFilter || 'life chart legacy timeline map'.includes(pillarFilter.toLowerCase())) && (
            <button onClick={() => setActivePillar('__life_chart__')} style={{ ...s.pillarCard, border: '2px solid #d9e7ff' }}>
              <span style={{ fontSize: 28 }}>🕰️</span>
              <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>Life Chart Card</span>
              <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>Before conception → legacy</span>
            </button>
          )}
          {(!pillarFilter || 'belonging breadth responsibility circles bounty'.includes(pillarFilter.toLowerCase())) && (
            <button onClick={() => setActivePillar('__belonging__')} style={{ ...s.pillarCard, border: '2px solid #e4d8f5' }}>
              <span style={{ fontSize: 28 }}>◎</span>
              <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>Breadth of Belonging</span>
              <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>Responsibility widens outward</span>
            </button>
          )}
        </div>

        {/* Development Pillars */}
        <h2 style={{ ...s.sectionTitle, marginTop: 32 }}>Development Pillars</h2>
        <input type="text" placeholder="🔍 Filter pillars..." value={pillarFilter} onChange={e => setPillarFilter(e.target.value)} className="pillar-filter" style={{ ...s.input, marginBottom: 12 }} />
        <div className="pillar-grid-desktop">
          {PILLARS.filter(p => !pillarFilter || p.label.toLowerCase().includes(pillarFilter.toLowerCase())).map(p => {
            const c = allCounts[p.key] || { total: 0, complete: 0 }
            const pct = c.total ? Math.round((c.complete / c.total) * 100) : 0
            return (
              <button key={p.key} onClick={() => setActivePillar(p.key)} style={s.pillarCard}>
                <span style={{ fontSize: 28 }}>{p.icon}</span>
                <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>{p.label}</span>
                <div style={{ width: '100%', height: 4, background: '#eee', borderRadius: 2, marginTop: 8 }}>
                  <div style={{ width: `${pct}%`, height: 4, background: '#2ecc71', borderRadius: 2 }} />
                </div>
                <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>{c.complete}/{c.total}</span>
              </button>
            )
          })}
        </div>

        {/* Ask and you shall receive — Wishlist */}
        <h2 style={{ ...s.sectionTitle, marginTop: 32 }}>Ask and You Shall Receive</h2>
        <div className="pillar-grid-desktop">
          {(!pillarFilter || 'wishlist'.includes(pillarFilter.toLowerCase()) || 'ask'.includes(pillarFilter.toLowerCase())) && (
            <button onClick={() => setActivePillar('__wishlist__')} style={{ ...s.pillarCard, border: '2px solid #e0f0d0' }}>
              <span style={{ fontSize: 28 }}>🎁</span>
              <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>Wishlist</span>
              <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>Save toward what you want</span>
            </button>
          )}
        </div>

        {/* Programs, Career & Economy */}
        <h2 style={{ ...s.sectionTitle, marginTop: 32 }}>Programs, Career & Economy</h2>
        <div className="pillar-grid-desktop">
          {(!pillarFilter || 'bounty board'.includes(pillarFilter.toLowerCase())) && (
            <button onClick={() => setActivePillar('__economy__')} style={{ ...s.pillarCard, border: '2px solid #f0e6d0' }}>
              <span style={{ fontSize: 28 }}>💵</span>
              <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>Bounty Board</span>
              <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>Behavior &middot; Bounties &middot; Earnings</span>
            </button>
          )}
          {(!pillarFilter || 'programs'.includes(pillarFilter.toLowerCase()) || 'military'.includes(pillarFilter.toLowerCase()) || 'pmcs'.includes(pillarFilter.toLowerCase()) || 'research'.includes(pillarFilter.toLowerCase()) || 'marriage'.includes(pillarFilter.toLowerCase()) || 'catholic'.includes(pillarFilter.toLowerCase())) && (
            <button onClick={() => setActivePillar('__programs__')} style={{ ...s.pillarCard, border: '2px solid #d0e6f0' }}>
              <span style={{ fontSize: 28 }}>📋</span>
              <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>Programs</span>
              <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>Structured tracks</span>
            </button>
          )}
          {(!pillarFilter || 'career'.includes(pillarFilter.toLowerCase())) && (
            <button onClick={() => setActivePillar('education')} style={{ ...s.pillarCard, border: '2px solid #e0d0f0' }}>
              <span style={{ fontSize: 28 }}>💼</span>
              <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>Career</span>
              <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>Discernment &middot; Formation</span>
            </button>
          )}
        </div>

        {/* Lesson Plans */}
        <h2 style={{ ...s.sectionTitle, marginTop: 32 }}>Lesson Plans</h2>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          <button onClick={() => { if (!lessons.length) fetchLessons(id).then(d => Array.isArray(d) && setLessons(d)); setActivePillar('__lessons__') }} style={{ ...s.pillarCard, border: '2px solid #e8f4e8', minWidth: 200 }}>
            <span style={{ fontSize: 28 }}>📖</span>
            <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>Lesson Plans</span>
            <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>Transcript study → Rebrief → Expand → Teach</span>
          </button>
        </div>

        {/* Discernment */}
        <h2 style={{ ...s.sectionTitle, marginTop: 32 }}>Discernment & Reflections</h2>
        <div className="pillar-grid-desktop">
          {[
            { key: 'health', icon: '🫀', label: 'Health' },
            { key: 'math', icon: '📐', label: 'Math' },
            { key: 'science', icon: '🔬', label: 'Science' },
            { key: 'civics', icon: '🏛️', label: 'Civics' },
            { key: 'relationships', icon: '🤝', label: 'Relationships' },
            { key: 'faith', icon: '🕯️', label: 'Faith' },
            { key: 'tradition', icon: '⚓', label: 'Tradition' },
            { key: 'law', icon: '⚖️', label: 'Law' },
            { key: 'network', icon: '🕸️', label: 'Network' },
            { key: 'calling', icon: '📣', label: 'Calling' },
          ].filter(d => !pillarFilter || d.label.toLowerCase().includes(pillarFilter.toLowerCase()) || 'discernment'.includes(pillarFilter.toLowerCase())).map(d => (
            <button key={d.key} onClick={() => { setActiveDiscern(d.key); setActivePillar('__discernment__') }} style={{ ...s.pillarCard, border: '2px solid #e8e0f0' }}>
              <span style={{ fontSize: 28 }}>{d.icon}</span>
              <span style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>{d.label}</span>
              <span style={{ fontSize: 11, color: '#888', marginTop: 4 }}>Discernment</span>
            </button>
          ))}
        </div>
      </div>
    )
  }

  // Life Maps view — visual dashboard cards, not development pillars
  if (activePillar === '__life_chart__') {
    return (
      <div style={s.container}>
        <button onClick={() => setActivePillar(null)} style={s.backBtn}>&larr; Back to Dashboard</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0 16px' }}>
          <span style={{ fontSize: 32 }}>🕰️</span>
          <div>
            <h2 style={{ margin: 0 }}>Life Chart Card</h2>
            <p style={{ margin: '4px 0 0', fontSize: 14, color: '#666' }}>You came from a story that started before you. You are living your part now. One day, others will inherit what you helped build, repair, protect, or damage.</p>
          </div>
        </div>

        <section style={s.mapHeroCard}>
          <div style={s.mapHeaderRow}>
            <div>
              <p style={s.learningEyebrow}>life_chart_card · visual_dashboard_card</p>
              <h3 style={s.learningTitle}>Life Chart Card</h3>
              <p style={s.learningText}>You came from a story that started before you. You are living your part of the story now. One day, others will inherit what you helped build, repair, protect, or damage.</p>
            </div>
            <span style={s.mapBadge}>Life overview</span>
          </div>
          <img
            src="/reference_images/life_chart_card.png"
            alt="Life Chart Card poster showing before conception, conception to birth, childhood and formation, adulthood and responsibility, death, and after death or legacy."
            style={s.mapImage}
          />
          <div style={s.mapGrid}>
            {LIFE_CHART_SECTIONS.map(section => (
              <div key={section.title} style={s.mapMiniCard}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={s.mapNumber}>{section.number}</span>
                  <strong style={{ fontSize: 13 }}>{section.title}</strong>
                </div>
                <p style={{ margin: '0 0 8px', fontSize: 12, color: '#4d5b6b', fontStyle: 'italic', lineHeight: 1.5 }}>{section.question}</p>
                <p style={{ margin: 0, fontSize: 11, color: '#7a8795', lineHeight: 1.5 }}>{section.examples.join(' · ')}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    )
  }

  if (activePillar === '__belonging__') {
    const belonging = BELONGING_VARIANTS[belongingVariant]
    return (
      <div style={s.container}>
        <button onClick={() => setActivePillar(null)} style={s.backBtn}>&larr; Back to Dashboard</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0 16px' }}>
          <span style={{ fontSize: 32 }}>◎</span>
          <div>
            <h2 style={{ margin: 0 }}>Expanding Breadth of Belonging</h2>
            <p style={{ margin: '4px 0 0', fontSize: 14, color: '#666' }}>As our vision expands beyond the self, our responsibilities and sense of belonging widen.</p>
          </div>
        </div>

        <section style={{ ...s.mapHeroCard, background: '#fbf8ff', borderColor: '#eadfff' }}>
          <div style={s.mapHeaderRow}>
            <div>
              <p style={{ ...s.learningEyebrow, color: '#7a4ed4' }}>breadth_of_belonging · visual_board + bounty_series</p>
              <h3 style={s.learningTitle}>Expanding Breadth of Belonging</h3>
              <p style={s.learningText}>As our vision expands beyond the self, our responsibilities and sense of belonging widen.</p>
            </div>
            <span style={{ ...s.mapBadge, background: '#f1eaff', color: '#6c3fc4' }}>Formation bounties</span>
          </div>

          <div style={s.variantRow}>
            {Object.entries(BELONGING_VARIANTS).map(([key, variant]) => (
              <button key={key} onClick={() => setBelongingVariant(key)} style={belongingVariant === key ? s.variantActive : s.variantBtn}>{variant.label}</button>
            ))}
          </div>

          <p style={{ margin: '0 0 12px', fontSize: 13, color: '#555', fontWeight: 600 }}>{belonging.summary}</p>
          <img src={belonging.image} alt={belonging.alt} style={s.mapImage} />

          <div style={s.mapGrid}>
            {belonging.rings.map(([ring, meaning], idx) => (
              <div key={ring} style={s.mapMiniCard}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ ...s.mapNumber, background: '#efe7ff', color: '#6c3fc4' }}>{idx + 1}</span>
                  <strong style={{ fontSize: 13 }}>{ring}</strong>
                </div>
                <p style={{ margin: 0, fontSize: 12, color: '#4d5b6b', lineHeight: 1.5 }}>{meaning}</p>
              </div>
            ))}
          </div>

          <details style={{ ...s.aboutDropdown, margin: '16px 0 0', background: '#fff', borderColor: '#eadfff' }}>
            <summary style={s.aboutSummary}>💰 Bounty Series Template</summary>
            <p style={{ margin: '0 0 8px', fontSize: 13, color: '#555', lineHeight: 1.6 }}>For each ring, create a fact sheet or family discussion entry. The bounty is complete when the child can explain both belonging and responsibility for that circle.</p>
            <ul style={{ margin: '0 0 12px', paddingLeft: 18, fontSize: 13, color: '#444', lineHeight: 1.7 }}>
              {BELONGING_BOUNTY_TEMPLATE.map(item => <li key={item}>{item}</li>)}
            </ul>
          </details>
        </section>
      </div>
    )
  }

  // Lesson Plans view
  if (activePillar === '__lessons__') {
    const loadLessons = () => fetchLessons(id).then(d => Array.isArray(d) && setLessons(d))
    if (!lessons.length) loadLessons()

    const handleCreateLesson = async (e) => {
      e.preventDefault()
      if (!lessonForm.title.trim() || !lessonForm.transcript.trim()) return
      await createLesson(id, { ...lessonForm, pillar: lessonForm.pillar || null, age_band: lessonForm.age_band || null, url: lessonForm.url || null })
      setLessonForm({ title: '', source: '', url: '', transcript: '', notes: '', pillar: '', age_band: '' })
      setShowLessonForm(false)
      loadLessons()
    }

    const handleSubmitResponse = async (e) => {
      e.preventDefault()
      if (!lessonResponseForm.content.trim()) return
      await createLessonResponse(id, activeLesson.id, lessonResponseForm)
      setLessonResponseForm({ response_type: 'rebrief', content: '' })
      const updated = await fetchLessons(id)
      if (Array.isArray(updated)) {
        setLessons(updated)
        setActiveLesson(updated.find(l => l.id === activeLesson.id) || null)
      }
    }

    if (activeLesson) {
      const lesson = lessons.find(l => l.id === activeLesson.id) || activeLesson
      const STATUS_LABELS = { assigned: '📋 Assigned', in_progress: '🔄 In Progress', rebrief_done: '✅ Rebrief Done', expansion_done: '✅ Expansion Done', teachback_done: '✅ Teachback Done', complete: '🏆 Complete' }
      return (
        <div style={s.container}>
          <button onClick={() => setActiveLesson(null)} style={s.backBtn}>&larr; Back to Lessons</button>
          <div style={{ margin: '24px 0 16px' }}>
            <h2 style={{ margin: 0 }}>{lesson.title}</h2>
            <p style={{ margin: '4px 0', fontSize: 13, color: '#888' }}>{lesson.source || 'No source'} · {lesson.pillar || 'General'} · {STATUS_LABELS[lesson.status] || lesson.status}</p>
            {lesson.url && <p style={{ margin: '4px 0' }}><a href={lesson.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: '#2a7ae2' }}>▶ Watch Original</a></p>}
            {lesson.notes && <p style={{ margin: '8px 0', fontSize: 13, color: '#555', fontStyle: 'italic' }}>📝 {lesson.notes}</p>}
          </div>
          <details style={{ marginBottom: 16, background: '#f9f9f9', padding: 12, borderRadius: 8, border: '1px solid #eee' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: 14 }}>📄 Transcript</summary>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.6, marginTop: 8, maxHeight: 400, overflow: 'auto' }}>{lesson.transcript}</pre>
          </details>
          <h3 style={{ margin: '16px 0 8px' }}>Responses</h3>
          {lesson.responses && lesson.responses.map(r => (
            <div key={r.id} style={{ padding: 10, marginBottom: 8, background: r.response_type === 'rebrief' ? '#f0f8ff' : r.response_type === 'expansion' ? '#f8fff0' : '#fff8f0', borderRadius: 8, border: '1px solid #eee' }}>
              <strong style={{ fontSize: 12, textTransform: 'uppercase', color: '#666' }}>{r.response_type}</strong>
              <p style={{ margin: '4px 0 0', fontSize: 13, whiteSpace: 'pre-wrap' }}>{r.content}</p>
            </div>
          ))}
          <form onSubmit={handleSubmitResponse} style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <select value={lessonResponseForm.response_type} onChange={e => setLessonResponseForm({ ...lessonResponseForm, response_type: e.target.value })} style={s.input}>
                <option value="rebrief">📝 Rebrief (summarize in own words)</option>
                <option value="expansion">🔭 Expansion (connect, question, deepen)</option>
                <option value="teachback">🎓 Teachback (teach it to someone)</option>
              </select>
            </div>
            <textarea value={lessonResponseForm.content} onChange={e => setLessonResponseForm({ ...lessonResponseForm, content: e.target.value })} placeholder="Write your response..." style={{ ...s.input, minHeight: 100, resize: 'vertical' }} />
            <button type="submit" style={s.submitBtn}>Submit Response</button>
          </form>
        </div>
      )
    }

    return (
      <div style={s.container}>
        <button onClick={() => setActivePillar(null)} style={s.backBtn}>&larr; Back to Dashboard</button>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '24px 0 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 32 }}>📖</span>
            <div>
              <h2 style={{ margin: 0 }}>Lesson Plans</h2>
              <p style={{ margin: '4px 0 0', fontSize: 14, color: '#666' }}>Transcript-based lessons: read, rebrief, expand, teach.</p>
            </div>
          </div>
          <button onClick={() => setShowLessonForm(!showLessonForm)} style={s.addBtn}>{showLessonForm ? 'Cancel' : '+ New Lesson'}</button>
        </div>
        {showLessonForm && (
          <form onSubmit={handleCreateLesson} style={{ ...s.form, marginBottom: 16 }}>
            <input value={lessonForm.title} onChange={e => setLessonForm({ ...lessonForm, title: e.target.value })} placeholder="Lesson title" style={s.input} required />
            <input value={lessonForm.source} onChange={e => setLessonForm({ ...lessonForm, source: e.target.value })} placeholder="Source (e.g., YouTube: Channel Name)" style={s.input} />
            <input value={lessonForm.url} onChange={e => setLessonForm({ ...lessonForm, url: e.target.value })} placeholder="URL (link to original video/article)" style={s.input} />
            <textarea value={lessonForm.transcript} onChange={e => setLessonForm({ ...lessonForm, transcript: e.target.value })} placeholder="Paste transcript here..." style={{ ...s.input, minHeight: 120, resize: 'vertical' }} required />
            <textarea value={lessonForm.notes} onChange={e => setLessonForm({ ...lessonForm, notes: e.target.value })} placeholder="Notes for child (what to focus on)..." style={{ ...s.input, minHeight: 50, resize: 'vertical' }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <select value={lessonForm.pillar} onChange={e => setLessonForm({ ...lessonForm, pillar: e.target.value })} style={{ ...s.input, maxWidth: 200 }}>
                <option value="">Pillar (optional)</option>
                {PILLARS.map(p => <option key={p.key} value={p.key}>{p.icon} {p.label}</option>)}
              </select>
              <select value={lessonForm.age_band} onChange={e => setLessonForm({ ...lessonForm, age_band: e.target.value })} style={{ ...s.input, maxWidth: 120 }}>
                <option value="">Age band</option>
                <option value="0-2">0–2</option><option value="2-3">2–3</option><option value="3-5">3–5</option>
                <option value="6-12">6–12</option><option value="13-18">13–18</option><option value="18-25">18–25</option><option value="25-35">25–35</option>
              </select>
            </div>
            <button type="submit" style={s.submitBtn}>Create Lesson</button>
          </form>
        )}
        {lessons.length === 0 && !showLessonForm && <p style={{ color: '#888', fontSize: 14 }}>No lesson plans yet. Click "+ New Lesson" to paste a transcript.</p>}
        {lessons.map(lesson => {
          const STATUS_COLORS = { assigned: '#e0e0e0', in_progress: '#fff3cd', rebrief_done: '#d1ecf1', expansion_done: '#d4edda', teachback_done: '#cce5ff', complete: '#d4edda' }
          return (
            <div key={lesson.id} onClick={() => setActiveLesson(lesson)} style={{ padding: 12, marginBottom: 8, background: STATUS_COLORS[lesson.status] || '#f9f9f9', borderRadius: 8, border: '1px solid #eee', cursor: 'pointer' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ fontSize: 14 }}>{lesson.title}</strong>
                <span style={{ fontSize: 11, color: '#666', textTransform: 'uppercase' }}>{lesson.status.replace(/_/g, ' ')}</span>
              </div>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#666' }}>{lesson.source || ''} {lesson.pillar ? `· ${lesson.pillar}` : ''} · {(lesson.responses || []).length} responses</p>
            </div>
          )
        })}
      </div>
    )
  }

  // Programs view
  if (activePillar === '__programs__') {
    if (!programs.length) { fetchPrograms(id).then(d => Array.isArray(d) && setPrograms(d)); fetchResearchTopics(id).then(setResearchTopics) }
    if (activeProgram) {
      const prog = programs.find(p => p.key === activeProgram)
      if (!prog) return <div style={s.container}><button onClick={() => setActiveProgram(null)} style={s.backBtn}>&larr; Back</button><p>Loading...</p></div>
      return (
        <div style={s.container}>
          <button onClick={() => setActiveProgram(null)} style={s.backBtn}>&larr; Back to Programs</button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0 16px' }}>
            <span style={{ fontSize: 32 }}>{prog.icon}</span>
            <div style={{ flex: 1 }}>
              <h2 style={{ margin: 0 }}>{prog.title}</h2>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#888' }}>{prog.completed}/{prog.total} tasks engaged</p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: 20, fontWeight: 700, color: '#2ecc71' }}>${(prog.total_reward / 100).toLocaleString()}{prog.has_repeatable ? <span style={{ fontSize: 12, color: '#999', fontWeight: 400 }}> +🔄</span> : ''}</span>
              <p style={{ margin: '2px 0 0', fontSize: 10, color: '#999', textTransform: 'uppercase' }}>Total Rewardable</p>
            </div>
          </div>
          <div style={{ width: '100%', height: 6, background: '#eee', borderRadius: 3, marginBottom: 20 }}>
            <div style={{ width: `${prog.total ? (prog.completed / prog.total * 100) : 0}%`, height: 6, background: '#2ecc71', borderRadius: 3 }} />
          </div>
          {(() => {
            let lastTier = null
            return prog.bounties.map(b => {
              const showPhaseHeader = b.tier !== lastTier && prog.phases && prog.phases[b.tier]
              lastTier = b.tier
              return (
                <div key={b.id}>
                  {showPhaseHeader && <h4 style={{ margin: '16px 0 8px', fontSize: 13, color: '#4a90d9', fontWeight: 600, borderBottom: '1px solid #e8e8e8', paddingBottom: 4 }}>{prog.phases[b.tier]}</h4>}
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 12px', background: '#fff', borderRadius: 8, marginBottom: 6, borderLeft: `3px solid ${b.status === 'retired' ? '#999' : b.status === 'paid' || (b.repeatable && b.times_completed > 0) ? '#2ecc71' : b.status === 'claimed' ? '#f5a623' : b.status === 'complete' ? '#27ae60' : '#ddd'}` }}>
              {editingPBounty === b.id ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <select value={editPBForm.status} onChange={e => setEditPBForm({ ...editPBForm, status: e.target.value })} style={{ ...s.input, maxWidth: 110, margin: 0 }}>
                      <option value="available">Available</option><option value="claimed">Claimed</option><option value="complete">Complete</option><option value="paid">Paid</option><option value="retired">Retired</option>
                    </select>
                    <select value={editPBForm.age_band} onChange={e => setEditPBForm({ ...editPBForm, age_band: e.target.value })} style={{ ...s.input, maxWidth: 100, margin: 0 }}>
                      <option value="">Age band</option><option value="0-2">0–2</option><option value="2-3">2–3</option><option value="3-5">3–5</option><option value="6-12">6–12</option><option value="13-18">13–18</option><option value="18-25">18–25</option><option value="25-35">25–35</option>
                    </select>
                    <input value={editPBForm.reward_amount} onChange={e => setEditPBForm({ ...editPBForm, reward_amount: e.target.value })} type="number" step="0.25" min="0" placeholder="$" style={{ ...s.input, maxWidth: 80, margin: 0 }} />
                  </div>
                  <input value={editPBForm.title} onChange={e => setEditPBForm({ ...editPBForm, title: e.target.value })} style={{ ...s.input, margin: 0 }} />
                  <textarea value={editPBForm.description} onChange={e => setEditPBForm({ ...editPBForm, description: e.target.value })} style={{ ...s.input, margin: 0, minHeight: 60, resize: 'vertical' }} />
                  {b.category && researchTopics[b.category] && (() => {
                    const completedTopics = prog.bounties.filter(x => x.category === b.category && x.description && x.description.startsWith('Topic:')).map(x => x.description.replace('Topic: ', '').replace(' [OWN DISCOVERY]', ''))
                    const available = researchTopics[b.category].filter(t => !completedTopics.includes(t))
                    return (
                      <div style={{ background: '#f9f9ff', padding: '8px 12px', borderRadius: 8, border: '1px solid #e8e8f0' }}>
                        <label style={{ fontSize: 12, fontWeight: 600, color: '#555' }}>Select topic ({b.category}):</label>
                        <select value="" onChange={e => { if (e.target.value) setEditPBForm({ ...editPBForm, description: `Topic: ${e.target.value}` }) }} style={{ ...s.input, margin: '6px 0 0' }}>
                          <option value="">— Pick a topic —</option>
                          {available.map(t => <option key={t} value={t}>{t}</option>)}
                          {completedTopics.length > 0 && <option disabled>── Completed ──</option>}
                          {completedTopics.map(t => <option key={t} disabled>{t} ✓</option>)}
                        </select>
                      </div>
                    )
                  })()}
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button onClick={async () => { await updateBounty(id, b.id, { title: editPBForm.title.trim(), description: editPBForm.description.trim() || null, reward_amount: Math.round((parseFloat(editPBForm.reward_amount) || 0) * 100), status: editPBForm.status, age_band: editPBForm.age_band || null }); setEditingPBounty(null); fetchPrograms(id).then(d => Array.isArray(d) && setPrograms(d)) }} style={{ ...s.submitBtn, padding: '6px 14px', fontSize: 12 }}>Save</button>
                    <button onClick={async () => { await updateBounty(id, b.id, { status: 'available', times_completed: 0, streak_count: 0, description: b.category ? null : undefined }); setEditingPBounty(null); fetchPrograms(id).then(d => Array.isArray(d) && setPrograms(d)) }} style={{ padding: '6px 14px', fontSize: 12, background: '#fff3e0', border: '1px solid #f5a623', borderRadius: 6, cursor: 'pointer', color: '#b37400' }}>Reset</button>
                    <button onClick={() => setEditingPBounty(null)} style={{ padding: '6px 14px', fontSize: 12, background: '#eee', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Cancel</button>
                  </div>
                </div>
              ) : (
                <>
                  <button onClick={async () => { if (b.status === 'retired') return; if (b.category && researchTopics[b.category] && b.status === 'available') { setEditingPBounty(b.id); setEditPBForm({ title: b.title, description: b.description || '', reward_amount: (b.reward_amount / 100).toFixed(2), age_band: b.age_band || '', status: 'claimed' }); return; } const next = { available: 'claimed', claimed: 'complete', complete: 'paid' }[b.status]; if (next) { await updateBounty(id, b.id, { status: next }); fetchPrograms(id).then(d => Array.isArray(d) && setPrograms(d)) } }} style={{ background: 'none', border: 'none', cursor: b.status === 'retired' ? 'default' : 'pointer', padding: 2, fontSize: 16, opacity: b.status === 'retired' ? 0.4 : 1 }} title={b.status === 'retired' ? 'Retired' : `${b.status} — click to advance`}>
                    <span style={{ color: b.status === 'retired' ? '#999' : b.status === 'paid' ? '#2ecc71' : b.status === 'complete' ? '#27ae60' : b.status === 'claimed' ? '#f5a623' : '#ddd' }}>
                      {b.status === 'retired' ? '🔒' : b.status === 'paid' ? '✓' : b.status === 'complete' ? '●' : b.status === 'claimed' ? '◐' : '○'}
                    </span>
                  </button>
                  <div style={{ flex: 1, opacity: b.status === 'retired' ? 0.5 : 1 }}>
                    <span style={{ fontWeight: 500 }}>{b.title}</span>
                    {b.age_band && <span style={{ fontSize: 10, marginLeft: 6, padding: '1px 5px', borderRadius: 6, background: '#f0f4ff', color: '#4a90d9' }}>{b.age_band}</span>}
                    {b.repeatable ? <span style={{ fontSize: 10, marginLeft: 6, color: '#999' }}>🔄×{b.times_completed}{b.streak_count > 0 ? <span style={{ color: b.streak_count >= 12 ? '#ffd700' : '#2ecc71' }}> 🔥{b.streak_count}</span> : ''}</span> : null}
                    {b.description && <MiniMarkdown text={b.description} maxHeight={120} />}
                  </div>
                  <div style={{ textAlign: 'right', flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                    <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 8, background: '#f5f5f5', color: '#888' }}>{b.tier}</span>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{b.reward_amount ? `$${(b.current_reward / 100).toFixed(2)}` : '🏆'}</div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button onClick={() => { setEditingPBounty(b.id); setEditPBForm({ title: b.title, description: b.description || '', reward_amount: (b.reward_amount / 100).toFixed(2), age_band: b.age_band || '', status: b.status }) }} style={{ background: 'none', border: 'none', color: '#aaa', fontSize: 12, cursor: 'pointer' }} title="Edit">✎</button>
                      <button onClick={async () => { if (confirm('Delete this bounty?')) { await deleteBounty(id, b.id); fetchPrograms(id).then(d => Array.isArray(d) && setPrograms(d)) } }} style={{ background: 'none', border: 'none', color: '#ccc', fontSize: 16, cursor: 'pointer' }} title="Delete">&times;</button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
              )
            })
          })()}
        </div>
      )
    }
    return (
      <div style={s.container}>
        <button onClick={() => { setActivePillar(null); setPrograms([]) }} style={s.backBtn}>&larr; Back to Dashboard</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0 16px' }}>
          <span style={{ fontSize: 32 }}>📋</span>
          <h2 style={{ margin: 0 }}>Programs</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 12 }}>
          {programs.map(prog => (
            <button key={prog.key} onClick={() => setActiveProgram(prog.key)} style={{ ...s.pillarCard, alignItems: 'flex-start', textAlign: 'left' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%' }}>
                <span style={{ fontSize: 24 }}>{prog.icon}</span>
                <div style={{ flex: 1 }}>
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{prog.title}</span>
                  <p style={{ margin: '2px 0 0', fontSize: 11, color: '#888' }}>{prog.completed}/{prog.total} engaged</p>
                </div>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#2ecc71' }}>${(prog.total_reward / 100).toLocaleString()}{prog.has_repeatable ? <span style={{ fontSize: 10, color: '#999', fontWeight: 400 }}> +🔄</span> : ''}</span>
              </div>
              <div style={{ width: '100%', height: 4, background: '#eee', borderRadius: 2, marginTop: 10 }}>
                <div style={{ width: `${prog.total ? (prog.completed / prog.total * 100) : 0}%`, height: 4, background: '#2ecc71', borderRadius: 2 }} />
              </div>
              <p style={{ margin: '8px 0 0', fontSize: 11, color: '#888' }}>{prog.description}</p>
            </button>
          ))}
        </div>
      </div>
    )
  }

  // Discernment view
  if (activePillar === '__discernment__' && activeDiscern) {
    const catMeta = { health: { icon: '🫀', title: 'Health', question: 'What is my body doing and what does it need?' }, math: { icon: '📐', title: 'Math', question: 'What mathematical patterns govern the decisions I\'m making?' }, science: { icon: '🔬', title: 'Science', question: 'How do I know what I think I know?' }, civics: { icon: '🏛️', title: 'Civics', question: 'What systems am I participating in?' }, relationships: { icon: '🤝', title: 'Relationships', question: 'Who am I becoming because of the people around me?' }, faith: { icon: '🕯️', title: 'Faith', question: 'What do I believe about what I cannot see?' }, tradition: { icon: '⚓', title: 'Tradition', question: 'What was built before me, why was it built, and what breaks if I tear it down?' }, law: { icon: '⚖️', title: 'Law', question: 'What rules bind me, who made them, and what is the difference between legal and just?' }, network: { icon: '🕸️', title: 'Network', question: 'What holds this group together, what happens if I dissent, and can I survive alone if I must?' }, calling: { icon: '📣', title: 'Calling', question: 'What is pulling me toward this path, who benefits from my decision, and what does the full picture look like?' } }
    const meta = catMeta[activeDiscern] || {}
    const loadDiscern = () => fetchDiscernmentEntries(id, activeDiscern).then(d => Array.isArray(d) && setDiscernEntries(d))
    if (!discernEntries.length || (discernEntries[0] && discernEntries[0].category !== activeDiscern)) loadDiscern()

    const discernBounties = pillarBounties.filter(b => b.category === activeDiscern)
    const cleanBountyTitle = (title = '') => title.replace(/^[a-z ]+\s+(reflection|assessment):\s*/i, '').trim()
    const titleCase = (value = '') => value ? value.charAt(0).toUpperCase() + value.slice(1) : value
    const statusLabel = { available: 'Available — click to claim', claimed: 'Claimed — click when finished', complete: 'Complete — click when paid', paid: 'Paid' }
    const statusIcon = { available: '○', claimed: '◐', complete: '●', paid: '✓' }
    const resetLabel = (b) => b.reset_days ? `resets every ${b.reset_days} days` : 'no automatic reset'

    const handleSubmitDiscern = async (e) => {
      e.preventDefault()
      if (!discernForm.title.trim() || !discernForm.reflection.trim()) return
      await createDiscernmentEntry(id, { category: activeDiscern, title: discernForm.title.trim(), reflection: discernForm.reflection.trim(), age_at_entry: age })
      setDiscernForm({ title: '', reflection: '' })
      loadDiscern()
    }

    return (
      <div style={s.container}>
        <button onClick={() => { setActivePillar(null); setActiveDiscern(null); setDiscernEntries([]) }} style={s.backBtn}>&larr; Back to Dashboard</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0 8px' }}>
          <span style={{ fontSize: 32 }}>{meta.icon}</span>
          <div>
            <h2 style={{ margin: 0 }}>{meta.title}</h2>
            <p style={{ margin: '4px 0 0', fontSize: 14, color: '#666', fontStyle: 'italic' }}>{meta.question}</p>
          </div>
        </div>

        {/* Civic symbol literacy image */}
        {activeDiscern === 'civics' && (
          <div style={{ marginTop: 16, textAlign: 'center', padding: 16, background: '#f8f8ff', border: '1px solid #e0e0f0', borderRadius: 10 }}>
            <img src="/reference_images/true-power.jpg" alt="Political cartoon: a crowd unknowingly supports the plank a politician stands on over a cliff. Caption: THE PEOPLE DON'T KNOW THEIR TRUE POWER." style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 8 }} />
            <p style={{ margin: '10px 0 0', fontSize: 12, color: '#555', lineHeight: 1.5 }}>
              <strong>The Central Question:</strong> Who is supporting whom? What happens if the crowd disperses? What systems of power depend not on command from above, but on participation, attention, money, labor, or consent from below?
            </p>
          </div>
        )}

        {/* Linked bounties */}
        {discernBounties.length > 0 && (
          <div style={{ marginTop: 16, padding: '12px 16px', background: '#f8faf5', border: '1px solid #e0e8d8', borderRadius: 10 }}>
            <h4 style={{ margin: '0 0 4px', fontSize: 14, color: '#3d5a2a' }}>💰 Earn While You Learn</h4>
            <p style={{ margin: '0 0 10px', fontSize: 12, color: '#66745d', lineHeight: 1.5 }}>Complete a thoughtful {meta.title || activeDiscern} reflection, save what you learned below, then advance the bounty status as the work moves from claimed to complete to paid.</p>
            {discernBounties.map(b => (
              <div key={b.id} style={{ display: 'grid', gridTemplateColumns: 'auto 1fr auto', alignItems: 'center', gap: 12, padding: '10px 0', borderTop: '1px solid #e6eedf' }}>
                <button onClick={async () => { const next = { available: 'claimed', claimed: 'complete', complete: 'paid' }[b.status]; if (next) { await updateBounty(id, b.id, { status: next }); fetchBounties(id).then(d => Array.isArray(d) && setPillarBounties(d)) } }} style={{ width: 34, height: 34, borderRadius: 17, border: '1px solid #d9e8cf', background: '#fff', cursor: b.status === 'paid' ? 'default' : 'pointer', fontSize: 16 }} title={statusLabel[b.status] || b.status}>
                  <span style={{ color: b.status === 'paid' ? '#2ecc71' : b.status === 'complete' ? '#27ae60' : b.status === 'claimed' ? '#f5a623' : '#bbb' }}>{statusIcon[b.status] || '○'}</span>
                </button>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11, color: '#6b7c5f', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4 }}>{meta.title || titleCase(b.category)} reflection bounty</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#263320', marginTop: 2 }}>{titleCase(cleanBountyTitle(b.title))}</div>
                  <div style={{ fontSize: 11, color: '#7b8772', marginTop: 4 }}>{statusLabel[b.status] || b.status}{b.repeatable ? ` · repeatable, completed ${b.times_completed || 0} time${(b.times_completed || 0) === 1 ? '' : 's'} · ${resetLabel(b)}` : ''}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#2ecc71' }}>${(b.current_reward / 100).toFixed(2)}</div>
                  <div style={{ fontSize: 10, color: '#8a9683' }}>current reward</div>
                </div>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmitDiscern} style={{ ...s.form, marginTop: 20 }}>
          <label style={{ fontSize: 13, fontWeight: 600, color: '#555' }}>New Reflection</label>
          <input placeholder="Summary (e.g. 'What I understand about my body now')" value={discernForm.title} onChange={e => setDiscernForm({ ...discernForm, title: e.target.value })} style={s.input} />
          <textarea placeholder="Write your reflection... What do you understand? What changed? What don't you know yet?" value={discernForm.reflection} onChange={e => setDiscernForm({ ...discernForm, reflection: e.target.value })} style={{ ...s.input, minHeight: 100, resize: 'vertical' }} />
          <button type="submit" style={s.submitBtn}>Save Reflection</button>
        </form>

        {discernEntries.length === 0 && <p style={{ color: '#888', textAlign: 'center', padding: 20 }}>No reflections yet. Write your first one above.</p>}

        {discernEntries.map(entry => (
          <div key={entry.id} style={{ padding: '16px', background: '#fff', borderRadius: 10, marginBottom: 12, borderLeft: '3px solid #9b59b6' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{entry.title}</span>
                {entry.age_at_entry != null && <span style={{ fontSize: 11, color: '#999', marginLeft: 8 }}>age {entry.age_at_entry}</span>}
              </div>
              <button onClick={async () => { if (confirm('Delete this reflection?')) { await deleteDiscernmentEntry(id, entry.id); loadDiscern() } }} style={{ background: 'none', border: 'none', color: '#ccc', fontSize: 18, cursor: 'pointer' }}>&times;</button>
            </div>
            <p style={{ margin: '8px 0 0', fontSize: 13, color: '#444', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{entry.reflection}</p>
            <span style={{ fontSize: 10, color: '#bbb' }}>{new Date(entry.created_at).toLocaleDateString()}</span>
          </div>
        ))}
      </div>
    )
  }

  // Wishlist standalone view
  if (activePillar === '__wishlist__') {
    return (
      <div style={s.container}>
        <button onClick={() => setActivePillar(null)} style={s.backBtn}>&larr; Back to Dashboard</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0 16px' }}>
          <span style={{ fontSize: 32 }}>🎁</span>
          <h2 style={{ margin: 0 }}>Ask and You Shall Receive</h2>
        </div>
        <p style={{ fontSize: 14, color: '#666', marginBottom: 20, fontStyle: 'italic' }}>What do you want to save toward? Add it here. Watch your earnings grow toward it.</p>
        <Economy profileId={id} wishlistOnly={true} />
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
  const bandOrder = ['0-2', '2-3', '3-5', '6-12', '13-18', '18-25', '25-35', 'Other']

  const renderItem = (item, showDelete = true, isChild = false) => {
    if (editing === item.id) {
      return (
        <div key={item.id} style={{ ...s.milestone, flexDirection: 'column', alignItems: 'stretch', borderLeft: `3px solid ${STATUS_COLORS[item.status]}` }}>
          <input value={editTitle} onChange={e => setEditTitle(e.target.value)} style={s.input} />
          <textarea value={editContent} onChange={e => setEditContent(e.target.value)} placeholder="Notes/observations..." style={{ ...s.input, minHeight: 50, resize: 'vertical', marginTop: 8 }} />
          <select value={editStatus} onChange={e => setEditStatus(e.target.value)} style={{ ...s.input, marginTop: 8, maxWidth: 180 }}>
            <option value="not_started">Not Started</option>
            <option value="introduced">Introduced</option>
            <option value="in_progress">In Progress</option>
            <option value="practicing">Practicing</option>
            <option value="complete">Complete</option>
            <option value="mastered">Mastered</option>
          </select>
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
        <div className="milestone-item" style={{ borderLeft: `3px solid ${STATUS_COLORS[item.status] || '#e0e0e0'}` }}>
          <button onClick={() => handleStatusToggle(item)} style={{ ...s.statusBtn, minWidth: 28 }} title={`Status: ${STATUS_DISPLAY[item.status] || item.status} (click to advance)`}>
            <span style={{ color: STATUS_COLORS[item.status] || '#e0e0e0', fontSize: 18 }}>{STATUS_LABELS[item.status] || '○'}</span>
          </button>
          <div style={{ flex: 1, cursor: isMilestone ? 'pointer' : 'default', minWidth: 0 }} onClick={() => isMilestone && toggleMilestoneExpand(item.id)}>
            <span style={{ textDecoration: item.status === 'complete' || item.status === 'mastered' ? 'line-through' : 'none', color: item.status === 'mastered' ? '#1a7a4c' : item.status === 'complete' ? '#888' : '#1a1a1a', wordBreak: 'break-word' }}>{item.title}</span>
            {item.content && <p style={{ margin: '4px 0 0', fontSize: 12, color: '#888', wordBreak: 'break-word' }}>{item.content}</p>}
            {isMilestone && <span style={{ fontSize: 10, color: '#bbb', marginLeft: 4 }}>{isExpanded ? '▾' : '▸'} details</span>}
          </div>
          <div className="milestone-actions">
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

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '24px 0 16px', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 32 }}>{currentPillar.icon}</span>
          <h2 style={{ margin: 0, fontSize: 20 }}>{currentPillar.label}</h2>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {pillarTab === 'milestones' && <button onClick={() => { setShowForm(!showForm); setFormType('milestone') }} style={s.addBtn}>{showForm ? 'Cancel' : '+ Milestone'}</button>}
        </div>
      </div>

      <details style={s.aboutDropdown}>
        <summary style={s.aboutSummary}>About this Pillar</summary>
        <p style={s.aboutText}>{currentPillar.about}</p>
      </details>

      {activePillar === 'civic' && (
        <div style={s.learningCard}>
          <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <img
              src="/reference_images/true-power.jpg"
              alt="Black-and-white political cartoon showing a politician speaking at a lectern on the end of a plank hanging over a cliff, while a crowd standing on the other end of the plank unknowingly keeps him from falling. Caption: The people don't know their true power."
              style={s.learningImage}
            />
            <div style={{ flex: 1, minWidth: 240 }}>
              <p style={s.learningEyebrow}>Civic symbol literacy</p>
              <h3 style={s.learningTitle}>Who is really holding the plank?</h3>
              <p style={s.learningText}>This cartoon teaches a civic lesson: visible authority often depends on hidden support from ordinary people. Money, attention, obedience, work, votes, silence, and participation can all hold a system in place.</p>
              <p style={s.learningText}>Before you decide that someone is powerless, ask what they are supporting. Before you decide that someone is powerful, ask who is holding them up.</p>
              <ul style={s.learningList}>
                <li>What is the crowd doing without realizing it?</li>
                <li>What would change if enough people stepped off the plank?</li>
                <li>Where do you see this pattern in school, media, markets, or government?</li>
              </ul>
              <p style={s.learningSource}>Source note: commonly circulated as “The People Don’t Know Their True Power”; original artist not clearly verified.</p>
            </div>
          </div>
        </div>
      )}

      {guideContent && (
        <details style={{ ...s.aboutDropdown, marginTop: 8 }}>
          <summary style={s.aboutSummary}>📖 Pillar Guide</summary>
          <div style={{ padding: '12px 16px', fontSize: 14, lineHeight: 1.7, color: '#333', maxHeight: 500, overflow: 'auto' }}>
            {(() => {
              const lines = guideContent.split('\n')
              const elements = []
              let i = 0
              while (i < lines.length) {
                const line = lines[i]
                // Code block
                if (line.startsWith('```')) {
                  const codeLines = []
                  i++
                  while (i < lines.length && !lines[i].startsWith('```')) { codeLines.push(lines[i]); i++ }
                  i++ // skip closing ```
                  elements.push(<pre key={elements.length} style={{ background: '#f5f5f5', padding: '10px 14px', borderRadius: 6, fontSize: 13, overflow: 'auto', whiteSpace: 'pre-wrap', margin: '8px 0' }}>{codeLines.join('\n')}</pre>)
                  continue
                }
                // Table
                if (line.includes('|') && line.trim().startsWith('|') && i + 1 < lines.length && lines[i + 1].includes('---')) {
                  const tableRows = []
                  while (i < lines.length && lines[i].includes('|') && lines[i].trim().startsWith('|')) {
                    tableRows.push(lines[i]); i++
                  }
                  const parseRow = r => r.split('|').filter((_, idx) => idx > 0 && idx < r.split('|').length - 1).map(c => c.trim())
                  const headerCells = parseRow(tableRows[0])
                  const bodyRows = tableRows.slice(2).map(parseRow)
                  elements.push(
                    <table key={elements.length} style={{ borderCollapse: 'collapse', margin: '8px 0', fontSize: 13, width: '100%' }}>
                      <thead><tr>{headerCells.map((c, j) => <th key={j} style={{ border: '1px solid #ddd', padding: '6px 10px', background: '#f8f8f8', textAlign: 'left', fontWeight: 600 }}>{c}</th>)}</tr></thead>
                      <tbody>{bodyRows.map((row, ri) => <tr key={ri}>{row.map((c, j) => <td key={j} style={{ border: '1px solid #ddd', padding: '6px 10px' }}>{c}</td>)}</tr>)}</tbody>
                    </table>
                  )
                  continue
                }
                // Headings
                if (line.startsWith('# ')) { elements.push(<h2 key={elements.length} style={{ fontSize: 18, margin: '16px 0 8px', color: '#1a1a1a' }}>{line.slice(2)}</h2>); i++; continue }
                if (line.startsWith('## ')) { elements.push(<h3 key={elements.length} style={{ fontSize: 15, margin: '14px 0 6px', color: '#333' }}>{line.slice(3)}</h3>); i++; continue }
                if (line.startsWith('### ')) { elements.push(<h4 key={elements.length} style={{ fontSize: 14, margin: '10px 0 4px', color: '#555', fontWeight: 600 }}>{line.slice(4)}</h4>); i++; continue }
                // HR
                if (line.trim() === '---') { elements.push(<hr key={elements.length} style={{ margin: '12px 0', border: 'none', borderTop: '1px solid #eee' }} />); i++; continue }
                // List items
                if (line.startsWith('- ')) { elements.push(<li key={elements.length} style={{ marginLeft: 16, marginBottom: 2 }}>{renderInline(line.slice(2))}</li>); i++; continue }
                // Blank line
                if (line.trim() === '') { i++; continue }
                // Paragraph
                elements.push(<p key={elements.length} style={{ margin: '4px 0' }}>{renderInline(line)}</p>)
                i++
              }
              return elements
            })()}
          </div>
        </details>
      )}

      {/* Tab toggle */}
      <div style={s.tabRow}>
        <button onClick={() => setPillarTab('milestones')} style={pillarTab === 'milestones' ? s.tabActive : s.tab}>Milestones</button>
        <button onClick={() => setPillarTab('bounties')} style={pillarTab === 'bounties' ? s.tabActive : s.tab}>Bounties</button>
      </div>

      {pillarTab === 'bounties' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginBottom: 12 }}>
            <button onClick={handleReseedProfile} style={{ ...s.addBtn, background: '#6c7a89' }} title="Add any newly seeded milestones and bounties to this existing profile">Sync Seeded Bounties</button>
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
                  <option value="diamond">Diamond</option>
                </select>
                <select value={pBountyForm.age_band} onChange={e => setPBountyForm({ ...pBountyForm, age_band: e.target.value })} style={{ ...s.input, maxWidth: 110 }}>
                  <option value="">Age band</option>
                  <option value="0-2">0–2</option>
                  <option value="2-3">2–3</option>
                  <option value="3-5">3–5</option>
                  <option value="6-12">6–12</option>
                  <option value="13-18">13–18</option>
                  <option value="18-25">18–25</option>
                  <option value="25-35">25–35</option>
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
            <div key={b.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', background: '#fff', borderRadius: 6, marginBottom: 4, flexWrap: editingPBounty === b.id ? 'wrap' : 'nowrap' }}>
              {editingPBounty === b.id ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <select value={editPBForm.status} onChange={e => setEditPBForm({ ...editPBForm, status: e.target.value })} style={{ ...s.input, maxWidth: 110, margin: 0 }}>
                      <option value="available">Available</option><option value="claimed">Claimed</option><option value="complete">Complete</option><option value="paid">Paid</option>
                    </select>
                    <select value={editPBForm.tier} onChange={e => setEditPBForm({ ...editPBForm, tier: e.target.value })} style={{ ...s.input, maxWidth: 110, margin: 0 }}>
                      <option value="bronze">Bronze</option><option value="silver">Silver</option><option value="gold">Gold</option><option value="platinum">Platinum</option><option value="diamond">Diamond</option>
                    </select>
                    <select value={editPBForm.age_band} onChange={e => setEditPBForm({ ...editPBForm, age_band: e.target.value })} style={{ ...s.input, maxWidth: 100, margin: 0 }}>
                      <option value="">Age band</option><option value="0-2">0–2</option><option value="2-3">2–3</option><option value="3-5">3–5</option><option value="6-12">6–12</option><option value="13-18">13–18</option><option value="18-25">18–25</option><option value="25-35">25–35</option>
                    </select>
                    <input value={editPBForm.reward_amount} onChange={e => setEditPBForm({ ...editPBForm, reward_amount: e.target.value })} type="number" step="0.25" min="0" placeholder="$" style={{ ...s.input, maxWidth: 80, margin: 0 }} />
                  </div>
                  <input value={editPBForm.title} onChange={e => setEditPBForm({ ...editPBForm, title: e.target.value })} style={{ ...s.input, margin: 0 }} />
                  <input value={editPBForm.description} onChange={e => setEditPBForm({ ...editPBForm, description: e.target.value })} placeholder="Description" style={{ ...s.input, margin: 0 }} />
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button onClick={() => saveEditPBounty(b)} style={{ ...s.submitBtn, padding: '6px 14px', fontSize: 12 }}>Save</button>
                    <button onClick={async () => { await updateBounty(id, b.id, { status: 'available', times_completed: 0, streak_count: 0 }); setEditingPBounty(null); fetchBounties(id, activePillar).then(d => Array.isArray(d) && setPillarBounties(d)) }} style={{ padding: '6px 14px', fontSize: 12, background: '#fff3e0', border: '1px solid #f5a623', borderRadius: 6, cursor: 'pointer', color: '#b37400' }}>Reset</button>
                    <button onClick={() => setEditingPBounty(null)} style={{ padding: '6px 14px', fontSize: 12, background: '#eee', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Cancel</button>
                  </div>
                </div>
              ) : (
                <>
                  <button onClick={() => cyclePillarBountyStatus(b)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2 }} title={`${b.status} — click to advance`}>
                    <span style={{ fontSize: 16, color: b.status === 'paid' ? '#2ecc71' : b.status === 'complete' ? '#27ae60' : b.status === 'claimed' ? '#f5a623' : '#ddd' }}>
                      {b.status === 'paid' ? '✓' : b.status === 'complete' ? '●' : b.status === 'claimed' ? '◐' : '○'}
                    </span>
                  </button>
                  <div style={{ flex: 1 }}>
                    <span style={{ textDecoration: b.status === 'paid' ? 'line-through' : 'none' }}>{b.title}</span>
                    {b.repeatable ? <span style={{ fontSize: 10, marginLeft: 6, color: '#999' }}>🔄 ×{b.times_completed}</span> : null}
                    {b.description && <p style={{ margin: '2px 0 0', fontSize: 12, color: '#888' }}>{b.description}</p>}
                  </div>
                  <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 8, background: {'bronze':'#fdf0e0','silver':'#f0f0f0','gold':'#fff8e0','platinum':'#e8f0ff','diamond':'#effcff'}[b.tier], color: {'bronze':'#cd7f32','silver':'#888','gold':'#b8860b','platinum':'#4a90d9','diamond':'#0088aa'}[b.tier] }}>{b.tier}</span>
                  {b.age_band && <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 8, background: '#f0f4ff', color: '#4a90d9' }}>{b.age_band}</span>}
                  <span style={{ fontWeight: 600, fontSize: 14 }}>${((b.current_reward ?? b.reward_amount) / 100).toFixed(2)}{b.repeatable && b.current_reward !== b.reward_amount ? <span style={{ fontSize: 10, color: '#999', textDecoration: 'line-through', marginLeft: 4 }}>${(b.reward_amount / 100).toFixed(2)}</span> : null}</span>
                  <button onClick={() => startEditPBounty(b)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: '#aaa' }} title="Edit">✎</button>
                  <button onClick={() => handleDeletePillarBounty(b.id)} style={{ background: 'none', border: 'none', color: '#ccc', fontSize: 18, cursor: 'pointer' }}>&times;</button>
                </>
              )}
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
              <option value="0-2">0–2</option>
              <option value="2-3">2–3</option>
              <option value="3-5">3–5</option>
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
  learningCard: { marginBottom: 16, padding: 16, background: '#f7fbff', border: '1px solid #dcecff', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' },
  learningImage: { width: 260, maxWidth: '100%', borderRadius: 10, border: '1px solid #d8e4f0', background: '#fff' },
  learningEyebrow: { margin: '0 0 4px', fontSize: 11, fontWeight: 700, color: '#4a90d9', textTransform: 'uppercase', letterSpacing: 0.5 },
  learningTitle: { margin: '0 0 8px', fontSize: 18, color: '#1f344a' },
  learningText: { margin: '0 0 8px', fontSize: 13, lineHeight: 1.6, color: '#34495e' },
  learningList: { margin: '8px 0', paddingLeft: 18, fontSize: 13, lineHeight: 1.6, color: '#34495e' },
  learningSource: { margin: '10px 0 0', fontSize: 10, color: '#7f8c8d', fontStyle: 'italic' },
  mapHeroCard: { marginBottom: 20, padding: 18, background: '#f7fbff', border: '1px solid #dcecff', borderRadius: 14, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' },
  mapHeaderRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap', marginBottom: 12 },
  mapBadge: { fontSize: 11, padding: '4px 10px', borderRadius: 999, background: '#e8f2ff', color: '#3f6fa8', fontWeight: 700, whiteSpace: 'nowrap' },
  mapImage: { width: '100%', maxHeight: 520, objectFit: 'contain', background: '#fff', border: '1px solid #d8e4f0', borderRadius: 12, marginBottom: 14 },
  mapGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 10 },
  mapMiniCard: { padding: 12, background: '#fff', border: '1px solid #edf1f5', borderRadius: 10 },
  mapNumber: { width: 24, height: 24, borderRadius: '50%', background: '#e8f2ff', color: '#3f6fa8', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, flexShrink: 0 },
  variantRow: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 },
  variantBtn: { padding: '8px 14px', background: '#fff', border: '1px solid #ddd', borderRadius: 999, cursor: 'pointer', fontSize: 13, color: '#666', fontWeight: 600 },
  variantActive: { padding: '8px 14px', background: '#6c3fc4', border: '1px solid #6c3fc4', borderRadius: 999, cursor: 'pointer', fontSize: 13, color: '#fff', fontWeight: 700 },
  tabRow: { display: 'flex', gap: 0, marginBottom: 16, borderBottom: '2px solid #e8e8e8' },
  tab: { padding: '10px 20px', background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: '#888', borderBottom: '2px solid transparent', marginBottom: -2 },
  tabActive: { padding: '10px 20px', background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: '#4a90d9', fontWeight: 600, borderBottom: '2px solid #4a90d9', marginBottom: -2 },
}
