/**
 * Persistent banner shown when the logged-in user has the readonly role.
 * The backend enforces readonly (writes return 403); this makes the state
 * clear to the user so write buttons that fail are not confusing.
 */
export default function ReadOnlyBanner() {
  return (
    <div
      role="status"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 500,
        background: '#fff3cd',
        borderBottom: '1px solid #e0c97a',
        color: '#5c4a00',
        padding: '8px 16px',
        fontSize: 14,
        textAlign: 'center',
      }}
    >
      👁️ <strong>Read-only mode</strong> — you can view everything but cannot make
      changes. Editing, adding, and claiming actions are disabled for this account.
    </div>
  )
}
