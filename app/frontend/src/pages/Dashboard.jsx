import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProfiles, createProfile } from '../services/api'
import { clearToken } from '../services/auth'

export default function Dashboard() {
  const [profiles, setProfiles] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDob, setNewDob] = useState('')

  const loadProfiles = () => {
    fetchProfiles()
      .then(data => {
        if (data.detail) setError(data.detail)
        else setProfiles(data)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadProfiles() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!newName.trim()) return
    const result = await createProfile(newName.trim(), newDob)
    if (result.detail) { setError(result.detail); return }
    setShowForm(false)
    setNewName('')
    setNewDob('')
    loadProfiles()
  }

  const getAge = (dob) => {
    if (!dob) return null
    const born = new Date(dob)
    const now = new Date()
    let age = now.getFullYear() - born.getFullYear()
    if (now.getMonth() < born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() < born.getDate())) age--
    return age
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>Life Plan Tracker</h1>
          <p style={styles.subtitle}>Lifetime Development Dashboard</p>
        </div>
        <button onClick={() => { clearToken(); window.location.reload() }} style={styles.logoutBtn}>Logout</button>
      </header>

      {error && <p style={styles.error}>Error: {error}</p>}
      {loading && <p style={styles.loading}>Loading...</p>}

      {!loading && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ margin: 0, fontSize: 20 }}>Profiles</h2>
            <button onClick={() => setShowForm(!showForm)} style={styles.addBtn}>
              {showForm ? 'Cancel' : '+ New Profile'}
            </button>
          </div>

          {showForm && (
            <form onSubmit={handleCreate} style={styles.form}>
              <input
                type="text"
                placeholder="Child's full name"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                style={styles.input}
                autoFocus
              />
              <input
                type="date"
                placeholder="Date of birth"
                value={newDob}
                onChange={e => setNewDob(e.target.value)}
                style={styles.input}
              />
              <button type="submit" style={styles.submitBtn}>Create Profile</button>
            </form>
          )}

          <div style={styles.grid}>
            {profiles.map(p => (
              <Link to={`/profile/${p.id}`} key={p.id} style={styles.card}>
                <div style={styles.avatar}>{p.name.charAt(0)}</div>
                <div style={styles.cardBody}>
                  <h3 style={styles.cardName}>{p.name}</h3>
                  {p.date_of_birth && (
                    <p style={styles.cardMeta}>Age {getAge(p.date_of_birth)} &middot; Born {p.date_of_birth}</p>
                  )}
                </div>
                <div style={styles.cardArrow}>&rarr;</div>
              </Link>
            ))}
          </div>

          {profiles.length === 0 && !showForm && (
            <div style={styles.empty}>
              <p style={{ fontSize: 48, margin: 0 }}>👶</p>
              <p style={{ fontSize: 18, margin: '12px 0 4px' }}>No profiles yet</p>
              <p style={{ color: '#888', margin: 0 }}>Click "+ New Profile" above to create one</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}

const styles = {
  container: { maxWidth: 900, margin: '0 auto', padding: '32px 24px', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', color: '#1a1a1a' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 },
  title: { margin: 0, fontSize: 28, fontWeight: 700 },
  subtitle: { margin: '4px 0 0', color: '#666', fontSize: 14 },
  logoutBtn: { padding: '8px 20px', background: 'none', border: '1px solid #ddd', borderRadius: 6, cursor: 'pointer', fontSize: 14, color: '#666' },
  loading: { textAlign: 'center', color: '#888', padding: 40 },
  error: { color: '#c0392b', background: '#fdf0ef', padding: 16, borderRadius: 8, marginBottom: 16 },
  addBtn: { padding: '10px 20px', background: '#4a90d9', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 },
  form: { display: 'flex', gap: 12, marginBottom: 24, padding: 20, background: '#f8f9ff', borderRadius: 12, flexWrap: 'wrap' },
  input: { flex: 1, minWidth: 180, padding: '10px 14px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 },
  submitBtn: { padding: '10px 24px', background: '#2ecc71', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 },
  card: { display: 'flex', alignItems: 'center', padding: 20, background: '#fff', border: '1px solid #e8e8e8', borderRadius: 12, textDecoration: 'none', color: 'inherit', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' },
  avatar: { width: 52, height: 52, borderRadius: '50%', background: 'linear-gradient(135deg, #667eea, #764ba2)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, fontWeight: 600, flexShrink: 0 },
  cardBody: { flex: 1, marginLeft: 16 },
  cardName: { margin: 0, fontSize: 18, fontWeight: 600 },
  cardMeta: { margin: '4px 0 0', color: '#888', fontSize: 13 },
  cardArrow: { fontSize: 20, color: '#ccc', marginLeft: 12 },
  empty: { textAlign: 'center', padding: 60, background: '#fafafa', borderRadius: 12, border: '1px dashed #ddd', marginTop: 16 },
}
