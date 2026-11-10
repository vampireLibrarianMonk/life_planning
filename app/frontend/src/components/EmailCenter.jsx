import { useEffect, useState } from 'react'
import {
  fetchEmailFacts,
  fetchEmailRecipients,
  createEmailDraft,
  aiEmailDraft,
  fetchEmailDrafts,
  previewEmailDraft,
  sendEmailDraft,
  fetchEmailMessages,
} from '../services/api'

/**
 * Email Center (v6 Pass 5) - compose a child update from explicitly selected
 * facts + media, preview the EXACT final email, then send with explicit
 * confirmation. Local/dev sends go through the console backend (honest
 * "logged" status, no real email). Bedrock AI drafting appears when enabled.
 * Readonly/child roles never reach this view (admin-only backend + gating).
 */
/**
 * SearchSelect — a lightweight searchable multi-select (type-to-filter
 * dropdown + removable selected chips). Used for recipients, highlights,
 * and media so the composer scales past a handful of items.
 */
function SearchSelect({ options, selected, onToggle, placeholder, emptyText }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const q = query.trim().toLowerCase()
  const matches = q
    ? options.filter((o) =>
        `${o.label} ${o.sub || ''} ${o.keywords || ''}`.toLowerCase().includes(q),
      )
    : options
  const selectedSet = new Set(selected)
  return (
    <div style={ss.wrap}>
      <div style={ss.selectedRow}>
        {selected.length === 0 && (
          <span style={ss.none}>Nothing selected yet — search below.</span>
        )}
        {options
          .filter((o) => selectedSet.has(o.id))
          .map((o) => (
            <span
              key={o.id}
              style={{ ...ss.selChip, ...(o.color ? { borderColor: o.color } : {}) }}
            >
              {o.icon ? `${o.icon} ` : ''}
              {o.label}
              <button
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => onToggle(o.id)}
                style={ss.x}
                title="Remove"
              >
                ×
              </button>
            </span>
          ))}
      </div>
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            setQuery('')
            setOpen(false)
          }
          if (e.key === 'Enter' && matches.length) {
            onToggle(matches[0].id)
            setQuery('')
          }
        }}
        placeholder={placeholder}
        style={ss.input}
      />
      {open && (
        <div style={ss.list}>
          {matches.length === 0 && (
            <div style={ss.noMatch}>No matches{emptyText ? ` — ${emptyText}` : ''}.</div>
          )}
          {matches.map((o) => (
            <button
              key={o.id}
              // preventDefault keeps focus in the input so onBlur doesn't close
              // the list before the click registers.
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onToggle(o.id)
                setQuery('')
              }}
              style={{ ...ss.option, ...(selectedSet.has(o.id) ? ss.optionOn : {}) }}
            >
              <span>
                {o.icon ? `${o.icon} ` : ''}
                {o.label}
                {o.sub ? <span style={ss.sub}> · {o.sub}</span> : null}
              </span>
              <span style={ss.check}>{selectedSet.has(o.id) ? '✓' : '+'}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function EmailCenter({ profileId, profileName, onBack, canWrite }) {
  const [facts, setFacts] = useState(null)
  const [recipients, setRecipients] = useState([])
  const [drafts, setDrafts] = useState([])
  const [messages, setMessages] = useState([])
  const [selRecipients, setSelRecipients] = useState([]) // method ids
  const [selFacts, setSelFacts] = useState([]) // fact ids
  const [selMedia, setSelMedia] = useState([]) // media ids
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(null)
  const [activeDraft, setActiveDraft] = useState(null)

  const load = () => {
    fetchEmailFacts(profileId).then((f) => setFacts(f))
    fetchEmailRecipients(profileId).then((r) => setRecipients(Array.isArray(r) ? r : []))
    fetchEmailDrafts(profileId).then((d) => setDrafts(Array.isArray(d) ? d : []))
    fetchEmailMessages(profileId).then((m) => setMessages(Array.isArray(m) ? m : []))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId])

  const toggle = (list, setList, id) =>
    setList(list.includes(id) ? list.filter((x) => x !== id) : [...list, id])

  const selectedRecipients = recipients.filter((r) => selRecipients.includes(r.method_id))
  const audiences = [...new Set(selectedRecipients.map((r) => r.audience))]
  const mixed = audiences.length > 1
  const audience = audiences[0] || null

  async function compose(useAI) {
    setError('')
    setPreview(null)
    if (!selRecipients.length) return setError('Select at least one recipient.')
    if (mixed) return setError('Mixed audiences must be sent as SEPARATE drafts.')
    setBusy(true)
    try {
      const payload = {
        recipient_method_ids: selRecipients,
        fact_ids: selFacts,
        media_ids: selMedia,
        note: note.trim() || null,
      }
      const draft = useAI
        ? await aiEmailDraft(profileId, payload)
        : await createEmailDraft(profileId, payload)
      setActiveDraft(draft)
      setDrafts(await fetchEmailDrafts(profileId))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function doPreview(draft) {
    setError('')
    setBusy(true)
    try {
      const p = await previewEmailDraft(profileId, draft.id)
      setPreview(p)
      setActiveDraft(draft)
    } catch (e) {
      setError(e.message)
      setPreview(null)
    } finally {
      setBusy(false)
    }
  }

  async function doSend(draft) {
    if (!confirm(`Send this email to ${draft.audience} recipient(s)? This cannot be undone.`)) return
    setError('')
    setBusy(true)
    try {
      await sendEmailDraft(profileId, draft.id)
      setPreview(null)
      setActiveDraft(null)
      setDrafts(await fetchEmailDrafts(profileId))
      setMessages(await fetchEmailMessages(profileId))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (!canWrite) {
    return (
      <div style={s.container}>
        <button className="back-btn" onClick={onBack} style={s.back}>&larr; Back to Dashboard</button>
        <p style={{ color: '#595959' }}>The Email Center is available to parent accounts only.</p>
      </div>
    )
  }

  return (
    <div style={s.container}>
      <button className="back-btn" onClick={onBack} style={s.back}>&larr; Back to Dashboard</button>
      <div style={s.header}>
        <span style={{ fontSize: 30 }} aria-hidden="true">✉️</span>
        <div>
          <h2 style={{ margin: 0 }}>Email Center</h2>
          <p style={{ margin: '2px 0 0', fontSize: 13, color: '#595959' }}>
            {profileName} · compose from selected facts + media ·{' '}
            {facts?.email_backend === 'ses' ? 'SES live' : 'console mode (no real email sent)'}
          </p>
        </div>
      </div>

      {error && <p style={s.error}>{error}</p>}

      {/* Recipients */}
      <h3 style={s.h3}>1 · Recipients</h3>
      {recipients.length === 0 && (
        <p style={s.hint}>No linked contacts with email yet — add them in Contacts.</p>
      )}
      <SearchSelect
        options={recipients.map((r) => ({
          id: r.method_id,
          label: r.display_name,
          sub: `${r.audience}${r.verified ? '' : ' · NOT verified'}`,
          keywords: r.address,
          color: AUDIENCE_COLOR[r.audience],
        }))}
        selected={selRecipients}
        onToggle={(id) => toggle(selRecipients, setSelRecipients, id)}
        placeholder="Search recipients by name, role, or email…"
        emptyText="try a different name or role"
      />
      {mixed && <p style={s.warn}>⚠️ Mixed audiences selected — the server will require separate drafts.</p>}

      {/* Facts */}
      <h3 style={s.h3}>2 · Highlights (child development & events)</h3>
      {facts && facts.highlights.length === 0 && facts.recent_events.length === 0 && (
        <p style={s.hint}>No child-development objectives or events yet.</p>
      )}
      <SearchSelect
        options={[
          ...(facts?.highlights || []).map((h) => ({
            id: h.id,
            label: h.title,
            sub: (h.status || '').replace('_', ' '),
            keywords: `${h.content || ''} ${h.category || ''}`,
          })),
          ...(facts?.recent_events || []).map((h) => ({
            id: h.id,
            label: h.title,
            sub: 'recent event',
            icon: '📎',
            keywords: h.content || '',
          })),
        ]}
        selected={selFacts}
        onToggle={(id) => toggle(selFacts, setSelFacts, id)}
        placeholder="Search highlights and events…"
        emptyText="try a different word"
      />

      {/* Media */}
      <h3 style={s.h3}>3 · Photos & videos</h3>
      <p style={s.hint}>Photos attach (within the 10 MiB email budget); videos always become private share links.</p>
      <SearchSelect
        options={(facts?.media || []).map((m) => ({
          id: m.id,
          label: m.name,
          sub: m.media_type,
          icon: m.media_type === 'video' ? '🎬' : m.media_type === 'photo' ? '🖼️' : '📄',
          keywords: `${m.observation || ''} ${m.mime_type || ''}`,
        }))}
        selected={selMedia}
        onToggle={(id) => toggle(selMedia, setSelMedia, id)}
        placeholder="Search photos and videos…"
        emptyText="no media matches that search"
      />

      {/* Note + compose */}
      <h3 style={s.h3}>4 · Note & compose</h3>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Optional personal note to weave in…"
        style={{ ...s.input, minHeight: 70, resize: 'vertical' }}
      />
      <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
        <button onClick={() => compose(false)} disabled={busy} style={s.primaryBtn}>
          {busy ? 'Working…' : '✉️ Compose draft'}
        </button>
        {facts?.bedrock_enabled && (
          <button onClick={() => compose(true)} disabled={busy} style={s.aiBtn}>
            ✨ Draft with Bedrock
          </button>
        )}
      </div>

      {/* Drafts */}
      <h3 style={s.h3}>Drafts</h3>
      {drafts.length === 0 && <p style={s.hint}>No drafts yet.</p>}
      {drafts.map((d) => (
        <div key={d.id} style={s.row}>
          <div style={{ flex: 1 }}>
            <strong style={{ fontSize: 13 }}>{d.subject || '(no subject)'}</strong>
            <span style={s.chipSub}> · {d.audience} · {d.status}
              {d.template_key === 'bedrock_assisted' ? ' · ✨ AI-assisted' : ''}</span>
          </div>
          <button onClick={() => doPreview(d)} disabled={busy} style={s.smallBtn}>Preview</button>
          {d.status === 'draft' && (
            <button onClick={() => doSend(d)} disabled={busy} style={{ ...s.smallBtn, background: '#c0392b' }}>Send…</button>
          )}
        </div>
      ))}

      {/* Exact preview */}
      {preview && (
        <div style={s.previewBox}>
          <h3 style={{ ...s.h3, marginTop: 0 }}>Exact preview — {preview.audience} draft</h3>
          <p style={s.hint}>
            To: {preview.recipients.map((r) => `${r.display_name} <${r.address}>`).join(', ')}
            {' '}· attachments {preview.attachments.length} · share links {preview.share_links.length} ·
            encoded {(preview.total_encoded_bytes / 1048576).toFixed(2)} MiB of {(preview.mime_cap_bytes / 1048576)} MiB cap
          </p>
          <pre style={s.pre}>{preview.text_body}</pre>
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            <button onClick={() => doSend(activeDraft)} disabled={busy} style={{ ...s.primaryBtn, background: '#c0392b' }}>
              ✅ Confirm & Send
            </button>
            <button onClick={() => setPreview(null)} style={s.smallGray}>Close preview</button>
          </div>
        </div>
      )}

      {/* Sent history */}
      <h3 style={s.h3}>Sent (outbound only — no inbox)</h3>
      {messages.length === 0 && <p style={s.hint}>Nothing sent yet.</p>}
      {messages.map((m) => (
        <div key={m.id} style={s.row}>
          <div style={{ flex: 1 }}>
            <strong style={{ fontSize: 13 }}>{m.subject}</strong>
            <span style={s.chipSub}> · to {m.to} · {m.transport}/{m.status}
              {m.sent_at ? ` · ${new Date(m.sent_at).toLocaleString()}` : ''}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

const AUDIENCE_COLOR = { family: '#15803d', clinician: '#2563b0', educator: '#7a4ed4' }

const s = {
  container: { maxWidth: 820, margin: '0 auto', padding: '8px 16px 48px' },
  back: { background: 'none', border: 'none', color: '#2563b0', cursor: 'pointer', fontSize: 14, padding: '6px 0' },
  header: { display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0 10px' },
  h3: { margin: '20px 0 8px', fontSize: 15 },
  hint: { margin: '4px 0 8px', fontSize: 12, color: '#595959' },
  chipWrap: { display: 'flex', gap: 6, flexWrap: 'wrap' },
  chip: { fontSize: 12, padding: '6px 10px', borderRadius: 14, border: '1px solid #cdd4dc', background: '#fff', color: '#333', cursor: 'pointer' },
  chipOn: { background: '#eaf2fd', borderColor: '#2563b0', fontWeight: 600 },
  chipSub: { fontSize: 10, color: '#595959' },
  warn: { color: '#b37400', background: '#fff7e0', padding: 8, borderRadius: 8, fontSize: 12 },
  error: { color: '#c0392b', background: '#fdf0ef', padding: 12, borderRadius: 8, margin: '10px 0' },
  input: { padding: '8px 10px', border: '1px solid #ccc', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
  primaryBtn: { fontSize: 14, fontWeight: 600, padding: '8px 16px', background: '#15803d', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' },
  aiBtn: { fontSize: 14, fontWeight: 600, padding: '8px 16px', background: '#7a4ed4', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' },
  smallBtn: { padding: '6px 12px', background: '#2563b0', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  smallGray: { padding: '6px 12px', background: '#eee', color: '#333', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  row: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', background: '#fff', border: '1px solid #e8e8e8', borderRadius: 8, marginBottom: 6 },
  previewBox: { marginTop: 16, background: '#fbfbf7', border: '2px solid #d9e7ff', borderRadius: 12, padding: 14 },
  pre: { whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6, background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 12, overflow: 'auto' },
}

// SearchSelect styles (scoped to the combobox so they don't leak into `s`).
const ss = {
  wrap: { position: 'relative', marginBottom: 6 },
  selectedRow: { display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6, minHeight: 24 },
  none: { fontSize: 12, color: '#8a8a8a', alignSelf: 'center' },
  selChip: { display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12, padding: '4px 8px', borderRadius: 14, border: '1px solid #2563b0', background: '#eaf2fd', fontWeight: 600 },
  x: { background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, color: '#595959', padding: '0 2px', lineHeight: 1 },
  input: { padding: '8px 10px', border: '1px solid #ccc', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
  list: { position: 'absolute', zIndex: 30, left: 0, right: 0, top: '100%', marginTop: 2, background: '#fff', border: '1px solid #cdd4dc', borderRadius: 8, boxShadow: '0 6px 18px rgba(0,0,0,0.12)', maxHeight: 240, overflowY: 'auto' },
  option: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left', padding: '8px 10px', background: 'none', border: 'none', borderBottom: '1px solid #f0f0f0', cursor: 'pointer', fontSize: 13, color: '#1a1a1a' },
  optionOn: { background: '#eaf2fd', fontWeight: 600 },
  sub: { fontSize: 11, color: '#595959', fontWeight: 400 },
  check: { color: '#2563b0', fontWeight: 700 },
  noMatch: { padding: 10, fontSize: 12, color: '#8a8a8a' },
}
