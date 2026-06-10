import { useEffect, useState } from 'react'
import { fetchBehavior, createBehavior, updateBehavior, fetchEligibility, fetchBounties, createBounty, updateBounty, deleteBounty, fetchEarnings, fetchWishlist, createWishlistItem, updateWishlistItem, deleteWishlistItem, fetchIncidents, createIncident, deleteIncident } from '../services/api'

const TRAITS = ['integrity', 'honesty', 'responsibility', 'respect', 'school_effort', 'citizenship']
const TRAIT_LABELS = { integrity: 'Integrity', honesty: 'Honesty', responsibility: 'Responsibility', respect: 'Respect', school_effort: 'School Effort', citizenship: 'Citizenship' }
const TIER_COLORS = { bronze: '#cd7f32', silver: '#a0a0a0', gold: '#ffd700', platinum: '#4a90d9' }
const TIER_ORDER = ['bronze', 'silver', 'gold', 'platinum']
const BOUNTY_STATUS_CYCLE = { available: 'claimed', claimed: 'complete', complete: 'paid' }

export default function Economy({ profileId }) {
  const [eligibility, setEligibility] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [bounties, setBounties] = useState([])
  const [earnings, setEarnings] = useState(null)
  const [showIncidentForm, setShowIncidentForm] = useState(false)
  const [incForm, setIncForm] = useState({ trait: 'integrity', positive: 1, description: '', date: new Date().toISOString().split('T')[0] })
  const [showBountyForm, setShowBountyForm] = useState(false)
  const [bountyForm, setBountyForm] = useState({ tier: 'bronze', title: '', description: '', reward_amount: '' })
  const [wishlist, setWishlist] = useState([])
  const [showWishForm, setShowWishForm] = useState(false)
  const [wishForm, setWishForm] = useState({ title: '', description: '', cost_cents: '', url: '', priority: 2 })

  const load = () => {
    fetchEligibility(profileId).then(setEligibility)
    fetchIncidents(profileId).then(d => Array.isArray(d) && setIncidents(d))
    fetchBounties(profileId).then(d => Array.isArray(d) && setBounties(d))
    fetchEarnings(profileId).then(setEarnings)
    fetchWishlist(profileId).then(d => Array.isArray(d) && setWishlist(d))
  }

  useEffect(() => { load() }, [profileId])

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
          Record positive (✓) and negative (✗) incidents for each trait. Your tier is determined by the ratio of positives to total incidents over the last 30 days:
        </p>
        <table style={{ ...st.table, marginBottom: 12 }}>
          <tbody>
            <tr><td style={st.td}>💎 Platinum (90%+)</td><td style={st.td}>Can propose projects, negotiate rates</td></tr>
            <tr><td style={st.td}>🥇 Gold (70–89%)</td><td style={st.td}>Larger projects requiring skill</td></tr>
            <tr><td style={st.td}>🥈 Silver (50–69%)</td><td style={st.td}>Property and organization tasks</td></tr>
            <tr><td style={st.td}>🥉 Bronze (&lt;50%)</td><td style={st.td}>Household help at entry level</td></tr>
          </tbody>
        </table>
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
