import { useEffect, useRef, useState } from 'react'

/**
 * Region-failover monitor (phase-2 dormant until a standby region exists).
 *
 * Polls /api/health. While healthy it remembers the serving region. If health
 * checks start failing (primary region down, Route 53 failing over to the
 * standby), it surfaces a plain-language overlay: which region appears down,
 * which is being brought up, and "give it a few minutes". No countdown timer —
 * it simply auto-dismisses when the backend answers again.
 *
 * In single-region (phase 1) this effectively never fires, because a brief
 * blip clears on the next poll and there is no second region name to report.
 */

const HEALTHY_POLL_MS = 15000   // poll cadence while healthy (snappy enough to
                                // catch a brief real failover without being chatty)
const FAILING_POLL_MS = 3000    // poll faster once we suspect an outage
const FAILS_BEFORE_OVERLAY = 2  // consecutive failures before showing the overlay

function prettyRegion(region) {
  if (!region) return 'the primary region'
  const names = {
    'us-east-1': 'US East (N. Virginia)',
    'us-west-2': 'US West (Oregon)',
  }
  return names[region] || region
}

async function probeHealth() {
  try {
    const res = await fetch('/api/health', { cache: 'no-store' })
    if (!res.ok) return { ok: false }
    const data = await res.json()
    return { ok: true, region: data?.config?.region || null }
  } catch {
    return { ok: false }
  }
}

export function useRegionFailoverMonitor() {
  const [state, setState] = useState({ failing: false, lastRegion: null, currentRegion: null })
  const failCount = useRef(0)
  const lastGoodRegion = useRef(null)

  useEffect(() => {
    let timer
    let cancelled = false

    async function tick() {
      const result = await probeHealth()
      if (cancelled) return

      if (result.ok) {
        failCount.current = 0
        if (result.region) lastGoodRegion.current = result.region
        setState((s) =>
          s.failing || s.currentRegion !== result.region
            ? { failing: false, lastRegion: lastGoodRegion.current, currentRegion: result.region }
            : s
        )
        timer = setTimeout(tick, HEALTHY_POLL_MS)
      } else {
        failCount.current += 1
        if (failCount.current >= FAILS_BEFORE_OVERLAY) {
          setState({
            failing: true,
            lastRegion: lastGoodRegion.current,
            currentRegion: null,
          })
        }
        timer = setTimeout(tick, FAILING_POLL_MS)
      }
    }

    tick()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [])

  return state
}

export default function RegionFailoverBanner() {
  const { failing, lastRegion } = useRegionFailoverMonitor()
  if (!failing) return null

  const downRegion = prettyRegion(lastRegion)
  // The standby is whichever region is not the one that just went down.
  const standby =
    lastRegion === 'us-east-1'
      ? prettyRegion('us-west-2')
      : lastRegion === 'us-west-2'
        ? prettyRegion('us-east-1')
        : 'the backup region'

  return (
    <div role="alert" aria-live="assertive" style={styles.overlay}>
      <div style={styles.card}>
        <div style={styles.icon} aria-hidden="true">🔄</div>
        <h2 style={styles.title}>Switching to the backup region</h2>
        <p style={styles.body}>
          The app is temporarily unavailable. It looks like <strong>{downRegion}</strong> is
          having trouble, so we are bringing the service back up in <strong>{standby}</strong>.
        </p>
        <p style={styles.body}>
          Please give it a few minutes — this page will reconnect automatically as soon as the
          backup region is ready. You do not need to do anything.
        </p>
        <p style={styles.hint}>Your data is safe; nothing is lost during the switch.</p>
      </div>
    </div>
  )
}

const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(38, 50, 56, 0.72)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
    padding: 16,
  },
  card: {
    background: '#fff',
    borderRadius: 16,
    padding: '28px 32px',
    maxWidth: 460,
    textAlign: 'center',
    boxShadow: '0 10px 40px rgba(0,0,0,0.25)',
  },
  icon: { fontSize: 40, marginBottom: 8 },
  title: { margin: '0 0 12px', fontSize: 22, color: '#263238' },
  body: { margin: '0 0 12px', fontSize: 15, lineHeight: 1.6, color: '#37474f' },
  hint: { margin: 0, fontSize: 13, color: '#595959' },
}
