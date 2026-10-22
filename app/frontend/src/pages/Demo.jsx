import { useEffect, useState } from 'react'

const PILLAR_META = {
  spiritual: { icon: '✝️', label: 'Spiritual' },
  financial: { icon: '💰', label: 'Financial' },
  education: { icon: '🎓', label: 'Education & Career' },
  character: { icon: '🛡️', label: 'Character' },
  life_skills: { icon: '🧰', label: 'Life Skills' },
  heritage: { icon: '🌳', label: 'Heritage & Language' },
}

const STATUS_LABEL = {
  not_started: '○ Not Started',
  introduced: '◔ Introduced',
  in_progress: '◑ In Progress',
  practicing: '◕ Practicing',
  complete: '● Complete',
  mastered: '★ Mastered',
}

const TIER_COLOR = {
  bronze: '#8a5420',
  silver: '#595959',
  gold: '#8a6f00',
  platinum: '#2563b0',
  diamond: '#00707f',
}

/**
 * Public, no-login app demonstrator. Renders an entirely anonymized FAKE
 * profile ("Alex Example") from the /api/demo/* endpoints. No real family data
 * is ever reachable here, and nothing is editable.
 */
export default function Demo() {
  const [profile, setProfile] = useState(null)
  const [entries, setEntries] = useState([])
  const [bounties, setBounties] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/demo/profile').then(r => r.json()),
      fetch('/api/demo/entries').then(r => r.json()),
      fetch('/api/demo/bounties').then(r => r.json()),
    ])
      .then(([p, e, b]) => {
        setProfile(p)
        setEntries(Array.isArray(e) ? e : [])
        setBounties(Array.isArray(b) ? b : [])
      })
      .catch(() => setError('Could not load the demo.'))
  }, [])

  if (error) return <div style={s.container}><p>{error}</p></div>
  if (!profile) return <div style={s.container}><p style={{ color: '#888' }}>Loading demo…</p></div>

  const byPillar = {}
  entries.forEach(e => {
    if (!byPillar[e.pillar]) byPillar[e.pillar] = []
    byPillar[e.pillar].push(e)
  })

  return (
    <div style={s.container}>
      <div style={s.demoBanner} role="status">
        👋 <strong>Demo mode</strong> — this is a sample profile with made-up data to show how Life
        Plan Tracker works. Nothing here is real and nothing can be changed.{' '}
        <a href="/" style={{ color: '#5c4a00', fontWeight: 600 }}>Go to the app →</a>
      </div>

      <header style={s.header}>
        <div style={s.avatar}>{profile.name.charAt(0)}</div>
        <div>
          <h1 style={{ margin: 0 }}>{profile.name}</h1>
          <p style={{ margin: '4px 0 0', color: '#666', fontSize: 14 }}>Sample lifetime-development dashboard</p>
        </div>
      </header>

      <h2 style={s.sectionTitle}>Development Pillars</h2>
      {Object.keys(byPillar).map(pk => {
        const meta = PILLAR_META[pk] || { icon: '•', label: pk }
        return (
          <div key={pk} style={s.card}>
            <h3 style={{ margin: '0 0 8px' }}>{meta.icon} {meta.label}</h3>
            {byPillar[pk].map(m => (
              <div key={m.id} style={s.row}>
                <span style={{ fontSize: 12, color: '#666', minWidth: 110 }}>{STATUS_LABEL[m.status] || m.status}</span>
                <span style={{ flex: 1 }}>{m.title}</span>
                {m.age_band && <span style={s.ageBadge}>{m.age_band}</span>}
              </div>
            ))}
          </div>
        )
      })}

      <h2 style={s.sectionTitle}>Sample Bounties</h2>
      <div style={s.card}>
        {bounties.map(b => (
          <div key={b.id} style={s.row}>
            <span style={{ ...s.tier, color: TIER_COLOR[b.tier] || '#555' }}>{b.tier}</span>
            <span style={{ flex: 1 }}>{b.title}</span>
            {b.age_band && <span style={s.ageBadge}>{b.age_band}</span>}
            <span style={{ fontWeight: 600 }}>${(b.current_reward / 100).toFixed(2)}</span>
          </div>
        ))}
      </div>

      <p style={{ textAlign: 'center', color: '#888', fontSize: 12, margin: '32px 0' }}>
        Behavior logs, private journals, and financial totals are never shown in the demo.
      </p>
    </div>
  )
}

const s = {
  container: { maxWidth: 860, margin: '0 auto', padding: '16px 20px 48px', fontFamily: 'system-ui, sans-serif' },
  demoBanner: { background: '#fff3cd', border: '1px solid #e0c97a', color: '#5c4a00', padding: '10px 16px', borderRadius: 8, fontSize: 14, marginBottom: 20 },
  header: { display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 },
  avatar: { width: 64, height: 64, borderRadius: '50%', background: '#2563b0', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, fontWeight: 700 },
  sectionTitle: { fontSize: 18, margin: '28px 0 12px' },
  card: { background: '#f9f9fb', border: '1px solid #eee', borderRadius: 10, padding: 14, marginBottom: 12 },
  row: { display: 'flex', alignItems: 'center', gap: 10, padding: '6px 4px', borderBottom: '1px solid #f0f0f0' },
  ageBadge: { fontSize: 10, padding: '2px 6px', borderRadius: 8, background: '#f0f4ff', color: '#2563b0' },
  tier: { fontSize: 11, textTransform: 'capitalize', fontWeight: 700, minWidth: 64 },
}
