import { useEffect, useState } from 'react'
import {
  fetchContacts,
  createContact,
  unlinkContact,
  fetchRelationshipSubtypes,
  CONTACT_ROLE_OPTIONS,
} from '../services/api'

// Human labels for the relationship sub-type keys the backend returns.
const SUBTYPE_LABELS = {
  mother: 'Mother', father: 'Father', grandmother: 'Grandmother', grandfather: 'Grandfather',
  aunt: 'Aunt', uncle: 'Uncle', sibling: 'Sibling', cousin: 'Cousin', godparent: 'Godparent',
  stepmother: 'Stepmother', stepfather: 'Stepfather', stepsibling: 'Stepsibling',
  legal_guardian: 'Legal guardian', foster_parent: 'Foster parent',
  therapist: 'Therapist', psychologist: 'Psychologist', psychiatrist: 'Psychiatrist',
  dentist: 'Dentist', optometrist: 'Optometrist', dietitian: 'Nutritionist / Dietitian',
  specialist: 'Specialist', classroom_teacher: 'Classroom teacher',
  special_education_teacher: 'Special-education teacher', aide: 'Aide', tutor: 'Tutor',
  administrator: 'Principal / Administrator', counselor: 'Counselor', coach: 'Coach',
  daycare_provider: 'Daycare provider', babysitter: 'Babysitter', nanny: 'Nanny',
  after_school_program: 'After-school program', primary: 'Primary', secondary: 'Secondary',
  other: 'Other',
}

/**
 * Contacts — the per-child recipient directory (v6 Pass 4). A role label is a
 * selection aid, NOT a permission. A contact may carry both an email and a
 * phone; roles that have relationship sub-types show a dependent 2nd dropdown.
 * Read-only users view but cannot add/remove.
 */
export default function Contacts({ profileId, profileName, onBack, canWrite }) {
  const [contacts, setContacts] = useState(null)
  const [subtypeMap, setSubtypeMap] = useState({})
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    display_name: '', email: '', phone: '', role: 'family', subtype: '',
  })

  const load = () => fetchContacts(profileId).then((d) => setContacts(Array.isArray(d) ? d : []))
  useEffect(() => {
    load()
    fetchRelationshipSubtypes(profileId).then((m) => setSubtypeMap(m || {}))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId])

  // Sub-types available for the currently selected role (empty => no 2nd dropdown).
  const subtypeOptions = subtypeMap[form.role] || []

  function setRole(role) {
    // Changing the first dropdown resets the dependent second dropdown.
    setForm((f) => ({ ...f, role, subtype: '' }))
  }

  async function add(e) {
    e.preventDefault()
    setError('')
    if (!form.display_name.trim()) {
      setError('A name is required.')
      return
    }
    if (!form.email.trim() && !form.phone.trim()) {
      setError('Enter an email, a phone number, or both.')
      return
    }
    const methods = []
    if (form.email.trim()) methods.push({ channel: 'email', address: form.email.trim() })
    if (form.phone.trim()) methods.push({ channel: 'sms', address: form.phone.trim() })
    try {
      await createContact(profileId, {
        display_name: form.display_name.trim(),
        methods,
        roles: form.role,
        relationship_subtype: form.subtype || null,
      })
      setForm({ display_name: '', email: '', phone: '', role: 'family', subtype: '' })
      setShowForm(false)
      await load()
    } catch (err) {
      setError(err.message || 'Could not save contact')
    }
  }

  async function remove(id) {
    if (!confirm('Remove this contact from this child? (The contact itself is kept.)')) return
    await unlinkContact(profileId, id)
    await load()
  }

  return (
    <div style={s.container}>
      <button className="back-btn" onClick={onBack} style={s.back}>
        &larr; Back to Dashboard
      </button>
      <div style={s.header}>
        <span style={{ fontSize: 30 }} aria-hidden="true">📇</span>
        <div>
          <h2 style={{ margin: 0 }}>Contacts</h2>
          <p style={{ margin: '2px 0 0', fontSize: 13, color: '#595959' }}>
            {profileName} · people you may share updates with
          </p>
        </div>
      </div>

      <p style={s.note}>
        A role label is just a label to help you organize — it does <strong>not</strong> give
        anyone access to {profileName}&rsquo;s information. You choose exactly what to send, each time.
      </p>

      {canWrite && !showForm && (
        <button className="write-action" onClick={() => setShowForm(true)} style={s.addBtn}>
          + Add contact
        </button>
      )}

      {canWrite && showForm && (
        <form onSubmit={add} style={s.form}>
          <input
            placeholder="Name (e.g. Dr. Sample)"
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            style={s.input}
          />
          <label style={s.fieldLabel}>Email</label>
          <input
            type="email"
            placeholder="name@example.com"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            style={s.input}
          />
          <label style={s.fieldLabel}>Phone (SMS)</label>
          <input
            type="tel"
            placeholder="+1 555 555 0123"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            style={s.input}
          />
          <label style={s.fieldLabel}>Role</label>
          <select value={form.role} onChange={(e) => setRole(e.target.value)} style={s.input}>
            {CONTACT_ROLE_OPTIONS.map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          {subtypeOptions.length > 0 && (
            <>
              <label style={s.fieldLabel}>Relationship</label>
              <select
                value={form.subtype}
                onChange={(e) => setForm({ ...form, subtype: e.target.value })}
                style={s.input}
              >
                <option value="">— Select —</option>
                {subtypeOptions.map((k) => (
                  <option key={k} value={k}>{SUBTYPE_LABELS[k] || k}</option>
                ))}
              </select>
            </>
          )}
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button type="submit" style={s.smallBtn}>Save</button>
            <button type="button" onClick={() => { setShowForm(false); setError('') }} style={s.smallGray}>Cancel</button>
          </div>
        </form>
      )}

      {error && <p style={s.error}>{error}</p>}
      {contacts === null && <p style={{ color: '#595959' }}>Loading…</p>}
      {contacts !== null && contacts.length === 0 && !showForm && (
        <p style={{ color: '#595959' }}>No contacts yet.</p>
      )}

      {contacts && contacts.length > 0 && (
        <div style={s.list}>
          {contacts.map((c) => (
            <div key={c.id} style={s.row}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <span style={{ fontWeight: 600 }}>{c.display_name}</span>
                {(c.methods || []).map((m) => (
                  <div key={m.id} style={{ fontSize: 12, color: '#595959' }}>
                    {m.channel === 'email' ? '✉️' : '📱'} {m.address}
                    {m.verified_at ? ' · verified' : ' · unverified'}
                  </div>
                ))}
              </div>
              {canWrite && (
                <button className="tap-target" title="Remove from this child" onClick={() => remove(c.id)} style={s.del}>
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const s = {
  container: { maxWidth: 820, margin: '0 auto', padding: '8px 16px 48px' },
  back: { background: 'none', border: 'none', color: '#2563b0', cursor: 'pointer', fontSize: 14, padding: '6px 0' },
  header: { display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0 10px' },
  note: { fontSize: 12, color: '#566370', background: '#f4f7fb', border: '1px solid #dce6f2', borderRadius: 8, padding: '8px 12px' },
  addBtn: { fontSize: 14, fontWeight: 600, padding: '8px 16px', background: '#15803d', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', marginBottom: 12 },
  form: { display: 'flex', flexDirection: 'column', gap: 6, background: '#f8f9ff', border: '1px solid #e2e8f5', borderRadius: 10, padding: 14, marginBottom: 14 },
  fieldLabel: { fontSize: 11, fontWeight: 600, color: '#566370', marginTop: 4 },
  input: { padding: '8px 10px', border: '1px solid #ccc', borderRadius: 6, fontSize: 13 },
  smallBtn: { padding: '7px 16px', background: '#15803d', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  smallGray: { padding: '7px 16px', background: '#eee', color: '#333', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  list: { display: 'flex', flexDirection: 'column', gap: 8 },
  row: { display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 12px', background: '#fff', border: '1px solid #e8e8e8', borderRadius: 8 },
  del: { background: 'none', border: 'none', color: '#c0392b', fontSize: 18, cursor: 'pointer' },
  error: { color: '#c0392b', background: '#fdf0ef', padding: 10, borderRadius: 8, margin: '10px 0' },
}
