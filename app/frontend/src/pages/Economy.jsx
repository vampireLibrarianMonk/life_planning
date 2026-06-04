import { useEffect, useState } from 'react'
import { fetchBehavior, createBehavior, updateBehavior, fetchEligibility, fetchBounties, createBounty, updateBounty, deleteBounty, fetchEarnings, fetchWishlist, createWishlistItem, updateWishlistItem, deleteWishlistItem } from '../services/api'

const TRAITS = ['integrity', 'honesty', 'responsibility', 'respect', 'school_effort', 'citizenship']
const TRAIT_LABELS = { integrity: 'Integrity', honesty: 'Honesty', responsibility: 'Responsibility', respect: 'Respect', school_effort: 'School Effort', citizenship: 'Citizenship' }
const TIER_COLORS = { bronze: '#cd7f32', silver: '#a0a0a0', gold: '#ffd700', platinum: '#4a90d9' }
const TIER_ORDER = ['bronze', 'silver', 'gold', 'platinum']
const BOUNTY_STATUS_CYCLE = { available: 'claimed', claimed: 'complete', complete: 'paid' }

export default function Economy({ profileId }) {
  const [behavior, setBehavior] = useState([])
  const [eligibility, setEligibility] = useState(null)
  const [bounties, setBounties] = useState([])
  const [earnings, setEarnings] = useState(null)
  const [showBehaviorForm, setShowBehaviorForm] = useState(false)
  const [showBountyForm, setShowBountyForm] = useState(false)
  const [bForm, setBForm] = useState({ integrity: 3, honesty: 3, responsibility: 3, respect: 3, school_effort: 3, citizenship: 3, notes: '' })
  const [bountyForm, setBountyForm] = useState({ tier: 'bronze', title: '', description: '', reward_amount: '' })
  const [wishlist, setWishlist] = useState([])
  const [showWishForm, setShowWishForm] = useState(false)
  const [wishForm, setWishForm] = useState({ title: '', description: '', cost_cents: '', url: '', priority: 2 })

  const load = () => {
    fetchBehavior(profileId).then(d => Array.isArray(d) && setBehavior(d))
    fetchEligibility(profileId).then(setEligibility)
    fetchBounties(profileId).then(d => Array.isArray(d) && setBounties(d))
    fetchEarnings(profileId).then(setEarnings)
    fetchWishlist(profileId).then(d => Array.isArray(d) && setWishlist(d))
  }

  useEffect(() => { load() }, [profileId])

  const getMonday = () => {
    const d = new Date(); d.setDate(d.getDate() - d.getDay() + 1)
    return d.toISOString().split('T')[0]
  }

  const handleBehaviorSubmit = async (e) => {
    e.preventDefault()
    await createBehavior(profileId, { ...bForm, week_of: getMonday(), notes: bForm.notes || null })
    setShowBehaviorForm(false)
    setBForm({ integrity: 3, honesty: 3, responsibility: 3, respect: 3, school_effort: 3, citizenship: 3, notes: '' })
    load()
  }

  const handleBountySubmit = async (e) => {
    e.preventDefault()
    if (!bountyForm.title.trim()) return
    await createBounty(profileId, { ...bountyForm, title: bountyForm.title.trim(), description: bountyForm.description.trim() || null, reward_amount: Math.round((parseFloat(bountyForm.reward_amount) || 0) * 100) })
    setShowBountyForm(false)
    setBountyForm({ tier: 'bronze', title: '', description: '', reward_amount: '' })
    load()
  }

  const cycleBountyStatus = async (b) => {
    const next = BOUNTY_STATUS_CYCLE[b.status]
    if (!next) return
    await updateBounty(profileId, b.id, { status: next })
    load()
  }

  const handleDeleteBounty = async (id) => {
    if (!confirm('Delete this bounty?')) return
    await deleteBounty(profileId, id); load()
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
            <span style={{ fontSize: 12, color: '#888' }}>Avg Score</span>
            <h3 style={{ margin: '4px 0 0' }}>{eligibility.average}/5</h3>
          </div>
        </div>
      )}

      {/* Earnings Summary */}
      {earnings && (
        <div style={st.earningsRow}>
          <div style={st.earnCard}><span style={st.earnLabel}>Total Earned</span><span style={st.earnValue}>{earnings.total_earned}</span></div>
          <div style={st.earnCard}><span style={st.earnLabel}>Paid Out</span><span style={st.earnValue}>{earnings.paid_out}</span></div>
          <div style={st.earnCard}><span style={st.earnLabel}>Pending</span><span style={st.earnValue}>{earnings.pending_payout}</span></div>
          <div style={st.earnCard}><span style={st.earnLabel}>Completed</span><span style={st.earnValue}>{earnings.bounties_completed}</span></div>
        </div>
      )}

      {/* Behavior Matrix */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '24px 0 12px' }}>
        <h3 style={{ margin: 0 }}>Behavior Matrix</h3>
        <button onClick={() => setShowBehaviorForm(!showBehaviorForm)} style={st.btn}>{showBehaviorForm ? 'Cancel' : '+ Score Week'}</button>
      </div>

      {showBehaviorForm && (
        <form onSubmit={handleBehaviorSubmit} style={st.form}>
          <p style={{ margin: '0 0 8px', fontSize: 13, color: '#666' }}>Rate each trait 1–5 for this week:</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 8 }}>
            {TRAITS.map(t => (
              <label key={t} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                {TRAIT_LABELS[t]}
                <input type="number" min="1" max="5" value={bForm[t]} onChange={e => setBForm({ ...bForm, [t]: parseInt(e.target.value) || 3 })} style={{ width: 40, padding: 4, borderRadius: 4, border: '1px solid #ddd', textAlign: 'center' }} />
              </label>
            ))}
          </div>
          <input placeholder="Notes (optional)" value={bForm.notes} onChange={e => setBForm({ ...bForm, notes: e.target.value })} style={st.input} />
          <button type="submit" style={st.submitBtn}>Save Week</button>
        </form>
      )}

      {behavior.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={st.table}>
            <thead>
              <tr>
                <th style={st.th}>Week</th>
                {TRAITS.map(t => <th key={t} style={st.th}>{TRAIT_LABELS[t].slice(0, 6)}</th>)}
                <th style={st.th}>Avg</th>
              </tr>
            </thead>
            <tbody>
              {behavior.slice(0, 8).map(s => {
                const avg = (TRAITS.reduce((sum, t) => sum + s[t], 0) / 6).toFixed(1)
                return (
                  <tr key={s.id}>
                    <td style={st.td}>{s.week_of}</td>
                    {TRAITS.map(t => <td key={t} style={{ ...st.td, color: s[t] >= 4 ? '#27ae60' : s[t] <= 2 ? '#c0392b' : '#333' }}>{s[t]}</td>)}
                    <td style={{ ...st.td, fontWeight: 600 }}>{avg}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
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
            <input placeholder="Task title" value={bountyForm.title} onChange={e => setBountyForm({ ...bountyForm, title: e.target.value })} style={{ ...st.input, flex: 1 }} />
            <input placeholder="$ amount" type="number" step="0.25" min="0" value={bountyForm.reward_amount} onChange={e => setBountyForm({ ...bountyForm, reward_amount: e.target.value })} style={{ ...st.input, maxWidth: 100 }} />
          </div>
          <input placeholder="Description (optional)" value={bountyForm.description} onChange={e => setBountyForm({ ...bountyForm, description: e.target.value })} style={st.input} />
          <button type="submit" style={st.submitBtn}>Create Bounty</button>
        </form>
      )}

      {bounties.length === 0 && !showBountyForm && (
        <p style={{ color: '#888', textAlign: 'center', padding: 20 }}>No bounties yet. Create one above.</p>
      )}

      {TIER_ORDER.filter(tier => bounties.some(b => b.tier === tier)).map(tier => (
        <div key={tier} style={{ marginBottom: 20 }}>
          <h4 style={{ margin: '0 0 8px', color: TIER_COLORS[tier], textTransform: 'capitalize', fontSize: 14 }}>{tier} Tier</h4>
          {bounties.filter(b => b.tier === tier).map(b => (
            <div key={b.id} style={st.bountyItem}>
              <button onClick={() => cycleBountyStatus(b)} style={st.statusDot} title={b.status}>
                <span style={{ color: b.status === 'paid' ? '#2ecc71' : b.status === 'complete' ? '#27ae60' : b.status === 'claimed' ? '#f5a623' : '#ddd', fontSize: 16 }}>
                  {b.status === 'paid' ? '✓' : b.status === 'complete' ? '●' : b.status === 'claimed' ? '◐' : '○'}
                </span>
              </button>
              <div style={{ flex: 1 }}>
                <span style={{ textDecoration: b.status === 'paid' ? 'line-through' : 'none', color: b.status === 'paid' ? '#888' : '#1a1a1a' }}>{b.title}</span>
                {b.description && <p style={{ margin: '2px 0 0', fontSize: 12, color: '#888' }}>{b.description}</p>}
              </div>
              <span style={{ fontWeight: 600, fontSize: 14, color: '#333' }}>${(b.reward_amount / 100).toFixed(2)}</span>
              <button onClick={() => handleDeleteBounty(b.id)} style={st.delBtn}>&times;</button>
            </div>
          ))}
        </div>
      ))}

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
