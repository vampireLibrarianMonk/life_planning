import { useEffect, useState } from 'react'
import { fetchBehavior, createBehavior, updateBehavior, fetchEligibility, fetchBounties, createBounty, updateBounty, deleteBounty, fetchEarnings, fetchWishlist, createWishlistItem, updateWishlistItem, deleteWishlistItem, fetchIncidents, createIncident, deleteIncident, fetchResearchTopics, fetchBountyLogs, createBountyLog, deleteBountyLog, fetchFunds, createFund, deleteFund, fetchFundTransactions, createFundTransaction, deleteFundTransaction } from '../services/api'
import MiniMarkdown from '../components/MiniMarkdown'

const TRAITS = ['integrity', 'honesty', 'responsibility', 'respect', 'school_effort', 'citizenship']
const TRAIT_LABELS = { integrity: 'Integrity', honesty: 'Honesty', responsibility: 'Responsibility', respect: 'Respect', school_effort: 'School Effort', citizenship: 'Citizenship' }
const TIER_COLORS = { bronze: '#cd7f32', silver: '#a0a0a0', gold: '#ffd700', platinum: '#4a90d9', diamond: '#b9f2ff', obsidian: '#1a1a2e', legendary: '#ff4500', covenant: '#7b2d8b', ooh_shiny: '#ff69b4', ironforged: '#4a5568' }
const TIER_ORDER = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'obsidian', 'legendary', 'covenant', 'ooh_shiny', 'ironforged']
const BEHAVIOR_GATED_TIERS = ['bronze', 'silver', 'gold', 'platinum']
const BOUNTY_STATUS_CYCLE = { available: 'claimed', claimed: 'complete', complete: 'paid' }
const BOUNTY_STATUSES = ['available', 'claimed', 'complete', 'paid', 'retired']

function getVisibleTiers(eligibleTier, isAdmin) {
  if (isAdmin) return TIER_ORDER
  const eligIdx = BEHAVIOR_GATED_TIERS.indexOf(eligibleTier)
  const gatedVisible = BEHAVIOR_GATED_TIERS.slice(0, eligIdx + 1)
  const ungated = TIER_ORDER.filter(t => !BEHAVIOR_GATED_TIERS.includes(t))
  return [...gatedVisible, ...ungated]
}

export default function Economy({ profileId, isAdmin = true, wishlistOnly = false }) {
  const [eligibility, setEligibility] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [bounties, setBounties] = useState([])
  const [earnings, setEarnings] = useState(null)
  const [showIncidentForm, setShowIncidentForm] = useState(false)
  const [incForm, setIncForm] = useState({ trait: 'integrity', positive: 1, description: '', date: new Date().toISOString().split('T')[0] })
  const [showBountyForm, setShowBountyForm] = useState(false)
  const [bountyForm, setBountyForm] = useState({ tier: 'bronze', title: '', description: '', reward_amount: '', age_band: '', category: '', repeatable: false, decay_divisor: '2', reset_days: '' })
  const [wishlist, setWishlist] = useState([])
  const [showWishForm, setShowWishForm] = useState(false)
  const [editingBounty, setEditingBounty] = useState(null) // bounty id being edited
  const [editBountyForm, setEditBountyForm] = useState({})
  const [wishForm, setWishForm] = useState({ title: '', description: '', cost_cents: '', url: '', priority: 2 })
  const [researchTopics, setResearchTopics] = useState({})
  const [claimingBounty, setClaimingBounty] = useState(null) // bounty being claimed (for topic picker)
  const [selectedTopic, setSelectedTopic] = useState('')
  const [customTopic, setCustomTopic] = useState('')
  const [expandedLog, setExpandedLog] = useState(null) // bounty id with log open
  const [bountyLogs, setBountyLogs] = useState([])
  const [logForm, setLogForm] = useState({ content: '', entry_type: 'note', author: 'parent' })
  const [funds, setFunds] = useState([])
  const [showFundForm, setShowFundForm] = useState(false)
  const [fundForm, setFundForm] = useState({ name: '', description: '', starting_balance: '' })
  const [expandedFund, setExpandedFund] = useState(null)
  const [fundTxns, setFundTxns] = useState([])
  const [txnForm, setTxnForm] = useState({ amount: '', description: '', date: new Date().toISOString().split('T')[0] })

  const load = () => {
    fetchEligibility(profileId).then(setEligibility)
    fetchIncidents(profileId).then(d => Array.isArray(d) && setIncidents(d))
    fetchBounties(profileId).then(d => Array.isArray(d) && setBounties(d))
    fetchEarnings(profileId).then(setEarnings)
    fetchWishlist(profileId).then(d => Array.isArray(d) && setWishlist(d))
    fetchFunds(profileId).then(d => Array.isArray(d) && setFunds(d))
  }

  useEffect(() => { load(); fetchResearchTopics(profileId).then(setResearchTopics) }, [profileId])

  const handleIncidentSubmit = async (e) => {
    e.preventDefault()
    if (!incForm.description.trim()) return
    await createIncident(profileId, { ...incForm, description: incForm.description.trim() })
    setShowIncidentForm(false)
    setIncForm({ trait: 'integrity', positive: 1, description: '', date: new Date().toISOString().split('T')[0] })
    load()
  }

  const handleDeleteIncident = async (id) => {
    if (!confirm('Delete this incident?')) return
    await deleteIncident(profileId, id); load()
  }

  const handleBountySubmit = async (e) => {
    e.preventDefault()
    if (!bountyForm.title.trim()) return
    await createBounty(profileId, { ...bountyForm, title: bountyForm.title.trim(), description: bountyForm.description.trim() || null, reward_amount: Math.round((parseFloat(bountyForm.reward_amount) || 0) * 100), age_band: bountyForm.age_band || null, category: bountyForm.category || null, repeatable: bountyForm.repeatable ? 1 : 0, decay_divisor: parseInt(bountyForm.decay_divisor) || 2, reset_days: bountyForm.reset_days ? parseInt(bountyForm.reset_days) : null })
    setShowBountyForm(false)
    setBountyForm({ tier: 'bronze', title: '', description: '', reward_amount: '', age_band: '', category: '', repeatable: false, decay_divisor: '2', reset_days: '' })
    load()
  }

  const cycleBountyStatus = async (b) => {
    if (b.status === 'retired') return
    // Check prerequisites client-side
    if (b.prerequisites && b.prerequisites.length > 0) {
      const unmet = b.prerequisites.filter(pid => {
        const prereq = bounties.find(x => x.id === pid)
        return prereq && prereq.status !== 'paid' && !(prereq.repeatable && prereq.times_completed > 0)
      })
      if (unmet.length > 0) {
        const names = unmet.map(pid => { const p = bounties.find(x => x.id === pid); return p ? p.title : `#${pid}` })
        alert(`Prerequisites not met:\n\n${names.join('\n')}`)
        return
      }
    }
    const next = BOUNTY_STATUS_CYCLE[b.status]
    if (!next) return
    // For research bounties being claimed, show topic picker
    if (b.category && b.status === 'available') {
      setClaimingBounty(b)
      setSelectedTopic('')
      setCustomTopic('')
      return
    }
    await updateBounty(profileId, b.id, { status: next })
    load()
  }

  const confirmClaim = async () => {
    if (!claimingBounty) return
    const topic = selectedTopic === '__custom__' ? customTopic.trim() : selectedTopic
    if (!topic) return
    const bonus = selectedTopic === '__custom__' ? ' [OWN DISCOVERY]' : ''
    await updateBounty(profileId, claimingBounty.id, { status: 'claimed', description: `Topic: ${topic}${bonus}` })
    setClaimingBounty(null)
    setSelectedTopic('')
    setCustomTopic('')
    load()
  }

  const handleDeleteBounty = async (id) => {
    if (!confirm('Delete this bounty?')) return
    await deleteBounty(profileId, id); load()
  }

  const startEditBounty = (b) => {
    setEditingBounty(b.id)
    setEditBountyForm({ title: b.title, description: b.description || '', reward_amount: (b.reward_amount / 100).toFixed(2), tier: b.tier, age_band: b.age_band || '', status: b.status, repeatable: !!b.repeatable, decay_divisor: String(b.decay_divisor || 2), reset_days: b.reset_days ? String(b.reset_days) : '' })
  }

  const saveEditBounty = async (b) => {
    await updateBounty(profileId, b.id, {
      title: editBountyForm.title.trim(),
      description: editBountyForm.description.trim() || null,
      reward_amount: Math.round((parseFloat(editBountyForm.reward_amount) || 0) * 100),
      status: editBountyForm.status,
      age_band: editBountyForm.age_band || null,
      repeatable: editBountyForm.repeatable ? 1 : 0,
      decay_divisor: parseInt(editBountyForm.decay_divisor) || 2,
      reset_days: editBountyForm.reset_days ? parseInt(editBountyForm.reset_days) : null,
    })
    setEditingBounty(null)
    load()
  }

  const resetBountyDecay = async (b) => {
    await updateBounty(profileId, b.id, { times_completed: 0, streak_count: 0 })
    setEditingBounty(null)
    load()
  }

  const toggleBountyLog = async (b) => {
    if (expandedLog === b.id) { setExpandedLog(null); return }
    setExpandedLog(b.id)
    const logs = await fetchBountyLogs(profileId, b.id)
    setBountyLogs(Array.isArray(logs) ? logs : [])
  }

  const submitLog = async (bountyId) => {
    if (!logForm.content.trim()) return
    await createBountyLog(profileId, bountyId, { ...logForm, content: logForm.content.trim() })
    setLogForm({ content: '', entry_type: 'note', author: 'parent' })
    const logs = await fetchBountyLogs(profileId, bountyId)
    setBountyLogs(Array.isArray(logs) ? logs : [])
  }

  const removeLog = async (bountyId, logId) => {
    await deleteBountyLog(profileId, bountyId, logId)
    const logs = await fetchBountyLogs(profileId, bountyId)
    setBountyLogs(Array.isArray(logs) ? logs : [])
  }

  const handleWishSubmit = async (e) => {
    e.preventDefault()
    if (!wishForm.title.trim()) return
    await createWishlistItem(profileId, {
      title: wishForm.title.trim(),
      description: wishForm.description.trim() || null,
      cost_cents: Math.round((parseFloat(wishForm.cost_cents) || 0) * 100),
      url: wishForm.url.trim() || null,
      priority: wishForm.priority,
    })
    setShowWishForm(false)
    setWishForm({ title: '', description: '', cost_cents: '', url: '', priority: 2 })
    load()
  }

  const cycleWishStatus = async (item) => {
    const next = { saving: 'approved', approved: 'purchased' }[item.status]
    if (!next) return
    await updateWishlistItem(profileId, item.id, { status: next })
    load()
  }

  const handleDeleteWish = async (id) => {
    if (!confirm('Remove from wishlist?')) return
    await deleteWishlistItem(profileId, id); load()
  }

  if (wishlistOnly) {
    return (
      <div>
        {showWishForm && (
          <form onSubmit={handleWishSubmit} style={st.form}>
            <input placeholder="What do you want?" value={wishForm.title} onChange={e => setWishForm({ ...wishForm, title: e.target.value })} style={st.input} autoFocus />
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <input placeholder="$ cost" type="number" step="0.01" min="0" value={wishForm.cost_cents} onChange={e => setWishForm({ ...wishForm, cost_cents: e.target.value })} style={{ ...st.input, maxWidth: 100 }} />
              <input placeholder="Link/URL (optional)" value={wishForm.url} onChange={e => setWishForm({ ...wishForm, url: e.target.value })} style={{ ...st.input, flex: 1 }} />
              <select value={wishForm.priority} onChange={e => setWishForm({ ...wishForm, priority: parseInt(e.target.value) })} style={{ ...st.input, maxWidth: 120 }}>
                <option value={1}>Low priority</option>
                <option value={2}>Medium</option>
                <option value={3}>High priority</option>
              </select>
            </div>
            <input placeholder="Why do you want it? (optional)" value={wishForm.description} onChange={e => setWishForm({ ...wishForm, description: e.target.value })} style={st.input} />
            <button type="submit" style={{ ...st.submitBtn, background: '#8e44ad' }}>Add to Wishlist</button>
          </form>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
          <button onClick={() => setShowWishForm(!showWishForm)} style={{ ...st.btn, background: '#8e44ad' }}>{showWishForm ? 'Cancel' : '+ Add Item'}</button>
        </div>
        {wishlist.length === 0 && !showWishForm && <p style={{ color: '#888', textAlign: 'center', padding: 20 }}>No wishlist items yet. What are you saving toward?</p>}
        {wishlist.map(item => {
          const earned = earnings ? earnings.total_earned_cents : 0
          const pct = item.cost_cents > 0 ? Math.min(100, Math.round((earned / item.cost_cents) * 100)) : 0
          const priorityLabel = { 1: '⭐', 2: '⭐⭐', 3: '⭐⭐⭐' }[item.priority] || ''
          return (
            <div key={item.id} style={{ ...st.bountyItem, borderLeft: `3px solid ${item.status === 'purchased' ? '#2ecc71' : item.status === 'approved' ? '#f5a623' : '#e0e0e0'}` }}>
              <button onClick={() => cycleWishStatus(item)} style={st.statusDot} title={item.status}>
                <span style={{ fontSize: 16 }}>{item.status === 'purchased' ? '✓' : item.status === 'approved' ? '👍' : '💭'}</span>
              </button>
              <div style={{ flex: 1 }}>
                <span style={{ textDecoration: item.status === 'purchased' ? 'line-through' : 'none' }}>{item.title}</span>
                <span style={{ fontSize: 11, marginLeft: 6 }}>{priorityLabel}</span>
                {item.description && <p style={{ margin: '2px 0 0', fontSize: 12, color: '#888' }}>{item.description}</p>}
                {item.cost_cents > 0 && item.status === 'saving' && (
                  <div style={{ marginTop: 4 }}>
                    <div style={{ width: '100%', height: 4, background: '#eee', borderRadius: 2 }}>
                      <div style={{ width: `${pct}%`, height: 4, background: '#8e44ad', borderRadius: 2 }} />
                    </div>
                    <span style={{ fontSize: 10, color: '#888' }}>{pct}% of ${(item.cost_cents / 100).toFixed(2)}</span>
                  </div>
                )}
              </div>
              {item.cost_cents > 0 && <span style={{ fontWeight: 600, fontSize: 14 }}>${(item.cost_cents / 100).toFixed(2)}</span>}
              <button onClick={() => handleDeleteWish(item.id)} style={st.delBtn}>&times;</button>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div>
      {/* Eligibility Banner */}
      {eligibility && (
        <div style={{ ...st.banner, borderColor: TIER_COLORS[eligibility.eligible_tier] }}>
          <div>
            <span style={{ fontSize: 12, color: '#888', textTransform: 'uppercase' }}>Current Eligibility</span>
            <h3 style={{ margin: '4px 0 0', color: TIER_COLORS[eligibility.eligible_tier], textTransform: 'capitalize' }}>{eligibility.eligible_tier} Tier</h3>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: 12, color: '#888' }}>Overall Score</span>
            <h3 style={{ margin: '4px 0 0' }}>{eligibility.percentage}%</h3>
          </div>
        </div>
      )}

      {/* Per-trait breakdown */}
      {eligibility && eligibility.trait_scores && Object.keys(eligibility.trait_scores).length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8, marginBottom: 20 }}>
          {TRAITS.map(t => {
            const ts = eligibility.trait_scores[t] || { positive: 0, negative: 0, ratio: 100 }
            return (
              <div key={t} style={{ padding: 10, background: '#fff', border: '1px solid #e8e8e8', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#888' }}>{TRAIT_LABELS[t]}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: ts.ratio >= 90 ? '#1a7a4c' : ts.ratio >= 70 ? '#f5a623' : ts.ratio >= 50 ? '#e67e22' : '#c0392b' }}>{ts.ratio}%</div>
                <div style={{ fontSize: 10, color: '#aaa' }}>✓{ts.positive} ✗{ts.negative}</div>
              </div>
            )
          })}
        </div>
      )}

      {/* Tier requirements */}
      <details style={{ marginBottom: 16, background: '#f8f9ff', border: '1px solid #e8e8f0', borderRadius: 10, padding: '0 16px' }}>
        <summary style={{ padding: '12px 0', cursor: 'pointer', fontSize: 13, fontWeight: 600, color: '#666' }}>How Tiers Work</summary>
        <p style={{ margin: '0 0 8px', fontSize: 13, color: '#444', lineHeight: 1.6 }}>
          Record positive (✓) and negative (✗) incidents for each trait. Your <strong>eligibility tier</strong> is determined by the ratio of positives to total incidents over the last 30 days. Higher tiers unlock visibility to more advanced bounties:
        </p>
        <table style={{ ...st.table, marginBottom: 12 }}>
          <tbody>
            <tr><td style={st.td}>🥉 <strong>Bronze</strong> (&lt;50%)</td><td style={st.td}>Household help, entry-level tasks. Default starting tier — earn your way up.</td></tr>
            <tr><td style={st.td}>🥈 <strong>Silver</strong> (50–69%)</td><td style={st.td}>Property care, organization, research bounties, repeatable tasks.</td></tr>
            <tr><td style={st.td}>🥇 <strong>Gold</strong> (70–89%)</td><td style={st.td}>Skilled projects, template design, service tasks, teaching others.</td></tr>
            <tr><td style={st.td}>💎 <strong>Platinum</strong> (90%+)</td><td style={st.td}>Technical mastery, propose your own projects, negotiate rates, leadership tasks.</td></tr>
          </tbody>
        </table>
        <p style={{ margin: '0 0 8px', fontSize: 12, color: '#666', lineHeight: 1.5 }}>
          <strong>Higher tiers (unlocked by sustained performance, not just percentage):</strong>
        </p>
        <table style={{ ...st.table, marginBottom: 12 }}>
          <tbody>
            <tr><td style={st.td}>💠 <strong>Diamond</strong></td><td style={st.td}>Requires: Platinum eligibility for 90+ consecutive days AND at least one Gold-tier program bounty completed.</td></tr>
            <tr><td style={st.td}>⬛ <strong>Obsidian</strong></td><td style={st.td}>Requires: Diamond unlocked AND 6+ months at Platinum AND demonstrated real-world financial commitment (spending own money on a task).</td></tr>
            <tr><td style={st.td}>🔥 <strong>Legendary</strong></td><td style={st.td}>Requires: Obsidian unlocked AND completion of a physical/spiritual endurance trial approved by parent. No shortcuts.</td></tr>
            <tr><td style={st.td}>💜 <strong>Covenant</strong></td><td style={st.td}>Requires: Age 18+ AND full completion of either Marriage Prep program (Catholic or Secular). Life-altering, once-in-a-lifetime.</td></tr>
            <tr><td style={st.td}>✨ <strong>Ooh Shiny!</strong></td><td style={st.td}>Requires: 7-year unbroken PMCS streak (364 consecutive weeks with buffer rules). Decade-scale discipline earns a vehicle.</td></tr>
            <tr><td style={st.td}>⚙️ <strong>Ironforged</strong></td><td style={st.td}>Requires: All 5 phases of Military Preparation program complete. Every knowledge test passed, every inspection passed, decision brief delivered.</td></tr>
          </tbody>
        </table>
        <p style={{ margin: 0, fontSize: 11, color: '#999', fontStyle: 'italic' }}>
          Bronze–Platinum are behavior-gated (30-day incident ratio). Diamond and above are earned through program completion, sustained streaks, and life milestones — not just good behavior scores.
        </p>
      </details>

      {/* Earnings Summary */}
      {earnings && (
        <div style={st.earningsRow}>
          <div style={st.earnCard}><span style={st.earnLabel}>Total Earned</span><span style={st.earnValue}>{earnings.total_earned}</span></div>
          <div style={st.earnCard}><span style={st.earnLabel}>Paid Out</span><span style={st.earnValue}>{earnings.paid_out}</span></div>
          <div style={st.earnCard}><span style={st.earnLabel}>Pending</span><span style={st.earnValue}>{earnings.pending_payout}</span></div>
          <div style={st.earnCard}><span style={st.earnLabel}>Completed</span><span style={st.earnValue}>{earnings.bounties_completed}</span></div>
        </div>
      )}

      {/* Behavior Incidents */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '24px 0 12px' }}>
        <h3 style={{ margin: 0 }}>Behavior Log</h3>
        <button onClick={() => setShowIncidentForm(!showIncidentForm)} style={st.btn}>{showIncidentForm ? 'Cancel' : '+ Record Incident'}</button>
      </div>

      {showIncidentForm && (
        <form onSubmit={handleIncidentSubmit} style={st.form}>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <select value={incForm.trait} onChange={e => setIncForm({ ...incForm, trait: e.target.value })} style={{ ...st.input, maxWidth: 160 }}>
              {TRAITS.map(t => <option key={t} value={t}>{TRAIT_LABELS[t]}</option>)}
            </select>
            <div style={{ display: 'flex', gap: 8 }}>
              <label style={{ fontSize: 13, cursor: 'pointer', padding: '6px 12px', borderRadius: 6, background: incForm.positive ? '#e8f8f0' : '#fff', border: '1px solid #ccc' }}>
                <input type="radio" name="positive" checked={incForm.positive === 1} onChange={() => setIncForm({ ...incForm, positive: 1 })} style={{ display: 'none' }} /> ✓ Positive
              </label>
              <label style={{ fontSize: 13, cursor: 'pointer', padding: '6px 12px', borderRadius: 6, background: !incForm.positive ? '#fde8e8' : '#fff', border: '1px solid #ccc' }}>
                <input type="radio" name="positive" checked={incForm.positive === 0} onChange={() => setIncForm({ ...incForm, positive: 0 })} style={{ display: 'none' }} /> ✗ Negative
              </label>
            </div>
            <input type="date" value={incForm.date} onChange={e => setIncForm({ ...incForm, date: e.target.value })} style={{ ...st.input, maxWidth: 150 }} />
          </div>
          <input placeholder="What happened? e.g. 'Told the truth about breaking the vase'" value={incForm.description} onChange={e => setIncForm({ ...incForm, description: e.target.value })} style={st.input} autoFocus />
          <button type="submit" style={st.submitBtn}>Save Incident</button>
        </form>
      )}

      {incidents.length > 0 && (
        <div style={{ maxHeight: 300, overflowY: 'auto', marginBottom: 20 }}>
          {incidents.map(inc => (
            <div key={inc.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderBottom: '1px solid #f0f0f0' }}>
              <span style={{ fontSize: 14 }}>{inc.positive ? '✓' : '✗'}</span>
              <span style={{ fontSize: 11, color: '#888', minWidth: 70 }}>{TRAIT_LABELS[inc.trait]?.slice(0, 8)}</span>
              <span style={{ flex: 1, fontSize: 13 }}>{inc.description}</span>
              <span style={{ fontSize: 11, color: '#bbb' }}>{inc.date}</span>
              <button onClick={() => handleDeleteIncident(inc.id)} style={st.delBtn}>&times;</button>
            </div>
          ))}
        </div>
      )}

      {/* Bounties */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '32px 0 12px' }}>
        <h3 style={{ margin: 0 }}>Bounties</h3>
        <button onClick={() => setShowBountyForm(!showBountyForm)} style={st.btn}>{showBountyForm ? 'Cancel' : '+ New Bounty'}</button>
      </div>

      {showBountyForm && (
        <form onSubmit={handleBountySubmit} style={st.form}>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <select value={bountyForm.tier} onChange={e => setBountyForm({ ...bountyForm, tier: e.target.value })} style={{ ...st.input, maxWidth: 140 }}>
              {TIER_ORDER.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
            </select>
            <select value={bountyForm.age_band} onChange={e => setBountyForm({ ...bountyForm, age_band: e.target.value })} style={{ ...st.input, maxWidth: 110 }}>
              <option value="">Age band</option>
              <option value="0-2">0–2</option>
              <option value="2-3">2–3</option>
              <option value="3-5">3–5</option>
              <option value="6-12">6–12</option>
              <option value="13-18">13–18</option>
              <option value="18-25">18–25</option>
              <option value="25-35">25–35</option>
            </select>
            <select value={bountyForm.category} onChange={e => setBountyForm({ ...bountyForm, category: e.target.value })} style={{ ...st.input, maxWidth: 120 }}>
              <option value="">Category</option>
              <option value="saint">Saint</option>
              <option value="paradox">Paradox</option>
              <option value="effect">Effect</option>
              <option value="sin">Deadly Sin</option>
              <option value="jury_case_review">Jury Case Review</option>
              <option value="formation_study">Formation Study</option>
              <option value="summer_capstone">Summer Capstone</option>
            </select>
            <input placeholder="Task title" value={bountyForm.title} onChange={e => setBountyForm({ ...bountyForm, title: e.target.value })} style={{ ...st.input, flex: 1 }} />
            <input placeholder="$ amount" type="number" step="0.25" min="0" value={bountyForm.reward_amount} onChange={e => setBountyForm({ ...bountyForm, reward_amount: e.target.value })} style={{ ...st.input, maxWidth: 100 }} />
          </div>
          <input placeholder="Description (optional)" value={bountyForm.description} onChange={e => setBountyForm({ ...bountyForm, description: e.target.value })} style={st.input} />
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <label style={{ fontSize: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
              <input type="checkbox" checked={bountyForm.repeatable} onChange={e => setBountyForm({ ...bountyForm, repeatable: e.target.checked })} /> Repeatable
            </label>
            {bountyForm.repeatable && <>
              <label style={{ fontSize: 14, color: '#333' }}>Divide by <input type="number" min="2" value={bountyForm.decay_divisor} onChange={e => setBountyForm({ ...bountyForm, decay_divisor: e.target.value })} style={{ ...st.input, width: 55, margin: '0 4px', display: 'inline', fontSize: 14 }} /> each time</label>
              <label style={{ fontSize: 14, color: '#333' }}>Reset after <input type="number" min="1" placeholder="days" value={bountyForm.reset_days} onChange={e => setBountyForm({ ...bountyForm, reset_days: e.target.value })} style={{ ...st.input, width: 65, margin: '0 4px', display: 'inline', fontSize: 14 }} /> days</label>
            </>}
          </div>
          <button type="submit" style={st.submitBtn}>Create Bounty</button>
        </form>
      )}

      {bounties.length === 0 && !showBountyForm && (
        <p style={{ color: '#888', textAlign: 'center', padding: 20 }}>No bounties yet. Create one above.</p>
      )}

      {/* Topic picker for research bounties */}
      {claimingBounty && (
        <div style={{ padding: 20, background: '#fffbf0', border: '1px solid #f0e6d0', borderRadius: 12, marginBottom: 20 }}>
          <h4 style={{ margin: '0 0 12px', fontSize: 15 }}>📋 Claim: {claimingBounty.title}</h4>
          <p style={{ margin: '0 0 12px', fontSize: 13, color: '#666' }}>Pick a topic from the list, or find your own for bonus credit.</p>
          <select value={selectedTopic} onChange={e => setSelectedTopic(e.target.value)} style={{ ...st.input, marginBottom: 10 }}>
            <option value="">— Select a topic —</option>
            {(() => {
              const completedTopics = bounties.filter(x => x.category === claimingBounty.category && x.description && x.description.startsWith('Topic:')).map(x => x.description.replace('Topic: ', '').replace(' [OWN DISCOVERY]', ''))
              return (researchTopics[claimingBounty.category] || []).map(t => <option key={t} value={t} disabled={completedTopics.includes(t)}>{t}{completedTopics.includes(t) ? ' ✓' : ''}</option>)
            })()}
            <option value="__custom__">✨ I found my own!</option>
          </select>
          {selectedTopic === '__custom__' && (
            <input placeholder="Enter your discovery..." value={customTopic} onChange={e => setCustomTopic(e.target.value)} style={{ ...st.input, marginBottom: 10 }} autoFocus />
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={confirmClaim} disabled={!selectedTopic || (selectedTopic === '__custom__' && !customTopic.trim())} style={{ ...st.submitBtn, padding: '8px 18px', fontSize: 13, opacity: (!selectedTopic || (selectedTopic === '__custom__' && !customTopic.trim())) ? 0.5 : 1 }}>Claim Bounty</button>
            <button onClick={() => setClaimingBounty(null)} style={{ padding: '8px 18px', fontSize: 13, background: '#eee', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {getVisibleTiers(eligibility?.eligible_tier || 'bronze', isAdmin).filter(tier => bounties.some(b => b.tier === tier)).map(tier => (
        <div key={tier} style={{ marginBottom: 24 }}>
          <h4 style={{ margin: '0 0 8px', color: TIER_COLORS[tier], textTransform: 'capitalize', fontSize: 14 }}>{tier} Tier <span style={{ fontSize: 11, color: '#999', fontWeight: 400 }}>({bounties.filter(b => b.tier === tier).length})</span></h4>
          {/* Column headers */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 10px', fontSize: 10, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5, borderBottom: '1px solid #eee', marginBottom: 4 }}>
            <span style={{ width: 28, textAlign: 'center' }}>Status</span>
            <span style={{ flex: 1, paddingLeft: 4 }}>Task</span>
            <span style={{ width: 40, textAlign: 'center' }}>Age</span>
            <span style={{ width: 70, textAlign: 'right' }}>Reward</span>
            <span style={{ width: 44 }}></span>
          </div>
          {/* Scrollable tier list */}
          <div style={{ maxHeight: 300, overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: 8, padding: '4px 0' }}>
            {bounties.filter(b => b.tier === tier).map(b => (
              <div key={b.id}>
                <div style={st.bountyItem}>
                {editingBounty === b.id ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                      <select value={editBountyForm.status} onChange={e => setEditBountyForm({ ...editBountyForm, status: e.target.value })} style={{ ...st.input, maxWidth: 110, margin: 0 }}>
                        {BOUNTY_STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
                      </select>
                      <select value={editBountyForm.tier} onChange={e => setEditBountyForm({ ...editBountyForm, tier: e.target.value })} style={{ ...st.input, maxWidth: 110, margin: 0 }}>
                        {TIER_ORDER.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                      </select>
                      <select value={editBountyForm.age_band} onChange={e => setEditBountyForm({ ...editBountyForm, age_band: e.target.value })} style={{ ...st.input, maxWidth: 100, margin: 0 }}>
                        <option value="">Age band</option>
                        <option value="0-2">0–2</option>
              <option value="2-3">2–3</option>
              <option value="3-5">3–5</option>
                        <option value="6-12">6–12</option>
                        <option value="13-18">13–18</option>
                        <option value="18-25">18–25</option>
                        <option value="25-35">25–35</option>
                      </select>
                      <input value={editBountyForm.reward_amount} onChange={e => setEditBountyForm({ ...editBountyForm, reward_amount: e.target.value })} type="number" step="0.25" min="0" placeholder="$" style={{ ...st.input, maxWidth: 80, margin: 0 }} />
                    </div>
                    <input value={editBountyForm.title} onChange={e => setEditBountyForm({ ...editBountyForm, title: e.target.value })} style={{ ...st.input, margin: 0 }} />
                    <input value={editBountyForm.description} onChange={e => setEditBountyForm({ ...editBountyForm, description: e.target.value })} placeholder="Description" style={{ ...st.input, margin: 0 }} />
                    {b.category && researchTopics[b.category] && (() => {
                      const completedTopics = bounties.filter(x => x.category === b.category && x.description && x.description.startsWith('Topic:')).map(x => x.description.replace('Topic: ', '').replace(' [OWN DISCOVERY]', ''))
                      const available = researchTopics[b.category].filter(t => !completedTopics.includes(t))
                      return (
                        <div style={{ background: '#f9f9ff', padding: '8px 12px', borderRadius: 8, border: '1px solid #e8e8f0' }}>
                          <label style={{ fontSize: 12, fontWeight: 600, color: '#555' }}>Select topic ({b.category}):</label>
                          <select value="" onChange={e => { if (e.target.value) setEditBountyForm({ ...editBountyForm, description: `Topic: ${e.target.value}` }) }} style={{ ...st.input, margin: '6px 0 0' }}>
                            <option value="">— Pick a topic —</option>
                            {available.map(t => <option key={t} value={t}>{t}</option>)}
                            <option disabled>── Completed ──</option>
                            {completedTopics.map(t => <option key={t} disabled>{t} ✓</option>)}
                          </select>
                        </div>
                      )
                    })()}
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                      <label style={{ fontSize: 14, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <input type="checkbox" checked={editBountyForm.repeatable} onChange={e => setEditBountyForm({ ...editBountyForm, repeatable: e.target.checked })} /> Repeatable
                      </label>
                      {editBountyForm.repeatable && <>
                        <label style={{ fontSize: 14, color: '#333' }}>Divide by <input type="number" min="2" value={editBountyForm.decay_divisor} onChange={e => setEditBountyForm({ ...editBountyForm, decay_divisor: e.target.value })} style={{ ...st.input, width: 55, margin: '0 4px', display: 'inline', fontSize: 14 }} /> each time</label>
                        <label style={{ fontSize: 14, color: '#333' }}>Reset after <input type="number" min="1" placeholder="days" value={editBountyForm.reset_days} onChange={e => setEditBountyForm({ ...editBountyForm, reset_days: e.target.value })} style={{ ...st.input, width: 65, margin: '0 4px', display: 'inline', fontSize: 14 }} /> days</label>
                      </>}
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button onClick={() => saveEditBounty(b)} style={{ ...st.submitBtn, padding: '6px 14px', fontSize: 12 }}>Save</button>
                      {b.repeatable && b.times_completed > 0 && <button onClick={() => resetBountyDecay(b)} style={{ padding: '6px 14px', fontSize: 12, background: '#fff3e0', border: '1px solid #f5a623', borderRadius: 6, cursor: 'pointer', color: '#b37400' }}>Reset Reward</button>}
                      <button onClick={() => setEditingBounty(null)} style={{ padding: '6px 14px', fontSize: 12, background: '#eee', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <button onClick={() => cycleBountyStatus(b)} style={st.statusDot} title={`${b.status} — click to advance`}>
                      <span style={{ color: b.status === 'paid' ? '#2ecc71' : b.status === 'complete' ? '#27ae60' : b.status === 'claimed' ? '#f5a623' : '#ddd', fontSize: 16 }}>
                        {b.status === 'paid' ? '✓' : b.status === 'complete' ? '●' : b.status === 'claimed' ? '◐' : '○'}
                      </span>
                    </button>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ textDecoration: b.status === 'paid' ? 'line-through' : 'none', color: b.status === 'paid' ? '#888' : '#1a1a1a' }}>{b.title}</span>
                      {b.repeatable ? <span style={{ fontSize: 10, marginLeft: 6, color: '#999' }}>🔄×{b.times_completed}{b.streak_count > 0 ? <span style={{ color: b.streak_count >= 52 ? '#ff4500' : b.streak_count >= 12 ? '#ffd700' : b.streak_count >= 4 ? '#2ecc71' : '#999' }}> 🔥{b.streak_count}</span> : ''}{b.reset_days && b.times_completed > 0 && b.last_completed_at ? (() => {
                        const daysElapsed = Math.floor((Date.now() - new Date(b.last_completed_at).getTime()) / 86400000)
                        const daysLeft = Math.max(0, b.reset_days - daysElapsed)
                        return daysLeft > 0 ? ` · resets in ${daysLeft}d` : ' · reset!'
                      })() : ''}</span> : null}
                      {b.description && <MiniMarkdown text={b.description} maxHeight={120} />}
                      {(b.requirements || b.reference || b.criteria) && (
                        <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          {b.requirements && <details style={{ fontSize: 11, width: '100%' }}><summary style={{ cursor: 'pointer', color: '#4a90d9', fontWeight: 600 }}>📋 Requirements</summary><pre style={{ margin: '4px 0', whiteSpace: 'pre-wrap', fontSize: 11, color: '#444', background: '#f8f9ff', padding: 8, borderRadius: 6 }}>{b.requirements}</pre></details>}
                          {b.reference && <details style={{ fontSize: 11, width: '100%' }}><summary style={{ cursor: 'pointer', color: '#27ae60', fontWeight: 600 }}>📖 Reference</summary><pre style={{ margin: '4px 0', whiteSpace: 'pre-wrap', fontSize: 11, color: '#444', background: '#f0fff4', padding: 8, borderRadius: 6 }}>{b.reference}</pre></details>}
                          {b.criteria && <details style={{ fontSize: 11, width: '100%' }}><summary style={{ cursor: 'pointer', color: '#e67e22', fontWeight: 600 }}>✓ Criteria</summary><pre style={{ margin: '4px 0', whiteSpace: 'pre-wrap', fontSize: 11, color: '#444', background: '#fffbf0', padding: 8, borderRadius: 6 }}>{b.criteria}</pre></details>}
                        </div>
                      )}
                    </div>
                    <span style={{ width: 40, textAlign: 'center', fontSize: 10, padding: '2px 4px', borderRadius: 8, background: b.age_band ? '#f0f4ff' : 'transparent', color: '#4a90d9' }}>{b.age_band || ''}</span>
                    <span style={{ width: 70, textAlign: 'right', fontWeight: 600, fontSize: 13, color: '#333' }}>${(b.current_reward / 100).toFixed(2)}{b.repeatable && b.current_reward !== b.reward_amount ? <span style={{ fontSize: 9, color: '#999', textDecoration: 'line-through', marginLeft: 3 }}>${(b.reward_amount / 100).toFixed(2)}</span> : null}</span>
                    <button onClick={() => toggleBountyLog(b)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: expandedLog === b.id ? '#4a90d9' : '#aaa' }} title="Log">📝</button>
                    <button onClick={() => startEditBounty(b)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: '#aaa' }} title="Edit">✎</button>
                    <button onClick={() => handleDeleteBounty(b.id)} style={st.delBtn}>&times;</button>
                  </>
                )}
              </div>
              {expandedLog === b.id && (
                <div style={{ padding: '10px 12px', background: '#f9f9ff', borderTop: '1px solid #eee', borderRadius: '0 0 8px 8px', marginTop: -2 }}>
                  <div style={{ maxHeight: 200, overflowY: 'auto', marginBottom: 10 }}>
                    {bountyLogs.length === 0 && <p style={{ fontSize: 12, color: '#999', margin: 0 }}>No log entries yet.</p>}
                    {bountyLogs.map(log => (
                      <div key={log.id} style={{ display: 'flex', gap: 8, padding: '6px 0', borderBottom: '1px solid #f0f0f0', alignItems: 'flex-start' }}>
                        <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 6, background: log.author === 'child' ? '#e8f8f0' : '#f0f4ff', color: log.author === 'child' ? '#27ae60' : '#4a90d9', whiteSpace: 'nowrap' }}>{log.author}</span>
                        <span style={{ fontSize: 10, padding: '2px 4px', borderRadius: 4, background: '#f5f5f5', color: '#888', whiteSpace: 'nowrap' }}>{log.entry_type}</span>
                        <span style={{ flex: 1, fontSize: 12, color: '#333' }}>{log.content}</span>
                        <span style={{ fontSize: 10, color: '#bbb', whiteSpace: 'nowrap' }}>{log.created_at ? new Date(log.created_at).toLocaleDateString() : ''}</span>
                        <button onClick={() => removeLog(b.id, log.id)} style={{ background: 'none', border: 'none', color: '#ccc', cursor: 'pointer', fontSize: 14 }}>×</button>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <select value={logForm.entry_type} onChange={e => setLogForm({ ...logForm, entry_type: e.target.value })} style={{ ...st.input, maxWidth: 110, margin: 0, fontSize: 12 }}>
                      <option value="note">Note</option>
                      <option value="submission">Submission</option>
                      <option value="feedback">Feedback</option>
                      <option value="evidence">Evidence</option>
                    </select>
                    <select value={logForm.author} onChange={e => setLogForm({ ...logForm, author: e.target.value })} style={{ ...st.input, maxWidth: 90, margin: 0, fontSize: 12 }}>
                      <option value="parent">Parent</option>
                      <option value="child">Child</option>
                    </select>
                    <input value={logForm.content} onChange={e => setLogForm({ ...logForm, content: e.target.value })} placeholder="Add a log entry..." style={{ ...st.input, flex: 1, margin: 0, fontSize: 12 }} onKeyDown={e => { if (e.key === 'Enter') submitLog(b.id) }} />
                    <button onClick={() => submitLog(b.id)} style={{ ...st.submitBtn, padding: '6px 12px', fontSize: 12 }}>Add</button>
                  </div>
                </div>
              )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Fund Tracker */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '32px 0 12px' }}>
        <h3 style={{ margin: 0 }}>💰 Fund Tracker</h3>
        <button onClick={() => setShowFundForm(!showFundForm)} style={{ ...st.btn, background: '#27ae60' }}>{showFundForm ? 'Cancel' : '+ New Fund'}</button>
      </div>
      {showFundForm && (
        <form onSubmit={async (e) => { e.preventDefault(); if (!fundForm.name.trim() || !fundForm.starting_balance) return; await createFund(profileId, { name: fundForm.name.trim(), description: fundForm.description.trim() || null, starting_balance: Math.round(parseFloat(fundForm.starting_balance) * 100) }); setFundForm({ name: '', description: '', starting_balance: '' }); setShowFundForm(false); load() }} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          <input placeholder="Fund name (e.g. Insurance Fund)" value={fundForm.name} onChange={e => setFundForm({ ...fundForm, name: e.target.value })} style={{ ...st.input, flex: 1 }} />
          <input placeholder="Description" value={fundForm.description} onChange={e => setFundForm({ ...fundForm, description: e.target.value })} style={{ ...st.input, flex: 1 }} />
          <input placeholder="Starting balance ($)" type="number" step="0.01" min="0" value={fundForm.starting_balance} onChange={e => setFundForm({ ...fundForm, starting_balance: e.target.value })} style={{ ...st.input, maxWidth: 130 }} />
          <button type="submit" style={{ ...st.btn, background: '#27ae60' }}>Create</button>
        </form>
      )}
      {funds.map(fund => {
        const pct = fund.starting_balance > 0 ? Math.round((fund.current_balance / fund.starting_balance) * 100) : 0
        const isExpanded = expandedFund === fund.id
        return (
          <div key={fund.id} style={{ background: '#f8fff8', border: '1px solid #d4edda', borderRadius: 8, padding: 12, marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{fund.name}</strong>
                {fund.description && <span style={{ fontSize: 12, color: '#666', marginLeft: 8 }}>{fund.description}</span>}
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontWeight: 700, color: fund.current_balance > 0 ? '#27ae60' : '#e74c3c' }}>${(fund.current_balance / 100).toFixed(2)}</span>
                <span style={{ fontSize: 11, color: '#999', marginLeft: 6 }}>of ${(fund.starting_balance / 100).toFixed(2)}</span>
              </div>
            </div>
            <div style={{ background: '#e9ecef', borderRadius: 4, height: 8, marginTop: 8 }}>
              <div style={{ background: '#27ae60', borderRadius: 4, height: 8, width: `${pct}%`, transition: 'width 0.3s' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
              <button onClick={async () => { if (isExpanded) { setExpandedFund(null); return } setExpandedFund(fund.id); const txns = await fetchFundTransactions(profileId, fund.id); setFundTxns(Array.isArray(txns) ? txns : []) }} style={{ ...st.btn, background: '#f0f0f0', color: '#333', fontSize: 11 }}>{isExpanded ? 'Hide' : 'Transactions'} ({fund.transaction_count})</button>
              <button onClick={async () => { if (confirm(`Delete fund "${fund.name}"?`)) { await deleteFund(profileId, fund.id); load() }}} style={{ ...st.btn, background: '#fdecea', color: '#c0392b', fontSize: 11 }}>Delete</button>
            </div>
            {isExpanded && (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #d4edda' }}>
                <form onSubmit={async (e) => { e.preventDefault(); if (!txnForm.amount || !txnForm.description.trim()) return; const res = await createFundTransaction(profileId, fund.id, { amount: Math.round(parseFloat(txnForm.amount) * 100), description: txnForm.description.trim(), date: txnForm.date || null }); if (res && res.id) { setTxnForm({ amount: '', description: '', date: new Date().toISOString().split('T')[0] }); const txns = await fetchFundTransactions(profileId, fund.id); setFundTxns(Array.isArray(txns) ? txns : []); load() } else { alert(res?.detail || 'Error') }}} style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                  <input placeholder="Amount ($)" type="number" step="0.01" min="0" value={txnForm.amount} onChange={e => setTxnForm({ ...txnForm, amount: e.target.value })} style={{ ...st.input, maxWidth: 100 }} />
                  <input placeholder="What was it for?" value={txnForm.description} onChange={e => setTxnForm({ ...txnForm, description: e.target.value })} style={{ ...st.input, flex: 1 }} />
                  <input type="date" value={txnForm.date} onChange={e => setTxnForm({ ...txnForm, date: e.target.value })} style={{ ...st.input, maxWidth: 140 }} />
                  <button type="submit" style={{ ...st.btn, background: '#27ae60', fontSize: 11 }}>+ Disburse</button>
                </form>
                {fundTxns.length === 0 && <p style={{ fontSize: 12, color: '#888', margin: 0 }}>No transactions yet.</p>}
                {fundTxns.map(txn => (
                  <div key={txn.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #eee', fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#c0392b', fontWeight: 600 }}>-${(txn.amount / 100).toFixed(2)}</span>
                      <span style={{ marginLeft: 8, color: '#555' }}>{txn.description}</span>
                      {txn.date && <span style={{ marginLeft: 8, color: '#aaa' }}>{txn.date}</span>}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ color: '#888' }}>bal: ${(txn.balance_after / 100).toFixed(2)}</span>
                      <button onClick={async () => { await deleteFundTransaction(profileId, fund.id, txn.id); const txns = await fetchFundTransactions(profileId, fund.id); setFundTxns(Array.isArray(txns) ? txns : []); load() }} style={{ background: 'none', border: 'none', color: '#c0392b', cursor: 'pointer', fontSize: 11 }}>×</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}

      {/* Wishlist */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '32px 0 12px' }}>
        <h3 style={{ margin: 0 }}>🎁 Wishlist</h3>
        <button onClick={() => setShowWishForm(!showWishForm)} style={{ ...st.btn, background: '#8e44ad' }}>{showWishForm ? 'Cancel' : '+ Add Wish'}</button>
      </div>

      {showWishForm && (
        <form onSubmit={handleWishSubmit} style={st.form}>
          <input placeholder="What do you want?" value={wishForm.title} onChange={e => setWishForm({ ...wishForm, title: e.target.value })} style={st.input} autoFocus />
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <input placeholder="$ cost" type="number" step="0.01" min="0" value={wishForm.cost_cents} onChange={e => setWishForm({ ...wishForm, cost_cents: e.target.value })} style={{ ...st.input, maxWidth: 100 }} />
            <input placeholder="Link/URL (optional)" value={wishForm.url} onChange={e => setWishForm({ ...wishForm, url: e.target.value })} style={{ ...st.input, flex: 1 }} />
            <select value={wishForm.priority} onChange={e => setWishForm({ ...wishForm, priority: parseInt(e.target.value) })} style={{ ...st.input, maxWidth: 120 }}>
              <option value={1}>Low priority</option>
              <option value={2}>Medium</option>
              <option value={3}>High priority</option>
            </select>
          </div>
          <input placeholder="Why do you want it? (optional)" value={wishForm.description} onChange={e => setWishForm({ ...wishForm, description: e.target.value })} style={st.input} />
          <button type="submit" style={{ ...st.submitBtn, background: '#8e44ad' }}>Add to Wishlist</button>
        </form>
      )}

      {wishlist.length === 0 && !showWishForm && (
        <p style={{ color: '#888', textAlign: 'center', padding: 20 }}>No wishes yet. Add something to save toward!</p>
      )}

      {wishlist.map(item => {
        const earned = earnings ? earnings.total_earned_cents : 0
        const pct = item.cost_cents > 0 ? Math.min(100, Math.round((earned / item.cost_cents) * 100)) : 0
        const priorityLabel = { 1: '⭐', 2: '⭐⭐', 3: '⭐⭐⭐' }[item.priority] || ''
        return (
          <div key={item.id} style={{ ...st.bountyItem, borderLeft: `3px solid ${item.status === 'purchased' ? '#2ecc71' : item.status === 'approved' ? '#f5a623' : '#e0e0e0'}` }}>
            <button onClick={() => cycleWishStatus(item)} style={st.statusDot} title={item.status}>
              <span style={{ fontSize: 16 }}>{item.status === 'purchased' ? '✓' : item.status === 'approved' ? '👍' : '💭'}</span>
            </button>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ textDecoration: item.status === 'purchased' ? 'line-through' : 'none' }}>{item.title}</span>
                <span style={{ fontSize: 11 }}>{priorityLabel}</span>
              </div>
              {item.description && <p style={{ margin: '2px 0 0', fontSize: 12, color: '#888' }}>{item.description}</p>}
              {item.cost_cents > 0 && item.status === 'saving' && (
                <div style={{ marginTop: 4 }}>
                  <div style={{ width: '100%', height: 4, background: '#eee', borderRadius: 2 }}>
                    <div style={{ width: `${pct}%`, height: 4, background: pct >= 100 ? '#2ecc71' : '#4a90d9', borderRadius: 2 }} />
                  </div>
                  <span style={{ fontSize: 11, color: '#888' }}>${(earned / 100).toFixed(2)} / ${(item.cost_cents / 100).toFixed(2)} ({pct}%)</span>
                </div>
              )}
              {item.url && <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: '#4a90d9' }}>View item ↗</a>}
            </div>
            <span style={{ fontWeight: 600, fontSize: 14, color: '#333' }}>${(item.cost_cents / 100).toFixed(2)}</span>
            <button onClick={() => handleDeleteWish(item.id)} style={st.delBtn}>&times;</button>
          </div>
        )
      })}
    </div>
  )
}

const st = {
  banner: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 20, background: '#fafafa', borderRadius: 12, border: '2px solid', marginBottom: 20 },
  earningsRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10, marginBottom: 20 },
  earnCard: { display: 'flex', flexDirection: 'column', padding: 14, background: '#fff', border: '1px solid #e8e8e8', borderRadius: 10, textAlign: 'center' },
  earnLabel: { fontSize: 11, color: '#888', textTransform: 'uppercase' },
  earnValue: { fontSize: 20, fontWeight: 700, marginTop: 4 },
  btn: { padding: '8px 16px', background: '#4a90d9', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 },
  form: { display: 'flex', flexDirection: 'column', gap: 10, padding: 16, background: '#f8f9ff', borderRadius: 10, marginBottom: 16 },
  input: { padding: '8px 12px', border: '1px solid #ddd', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
  submitBtn: { padding: '8px 20px', background: '#2ecc71', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600, alignSelf: 'flex-start' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid #eee', fontSize: 11, color: '#888', textTransform: 'uppercase' },
  td: { padding: '6px 8px', borderBottom: '1px solid #f5f5f5' },
  bountyItem: { display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', background: '#fff', borderRadius: 6, marginBottom: 4 },
  statusDot: { background: 'none', border: 'none', cursor: 'pointer', padding: 2 },
  delBtn: { background: 'none', border: 'none', color: '#ccc', fontSize: 18, cursor: 'pointer' },
}
