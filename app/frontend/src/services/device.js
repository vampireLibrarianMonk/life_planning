/**
 * Device-mode detection ("mobile" vs "desktop").
 *
 * The layout breakpoint is the single source of truth and MUST match the
 * `@media (max-width: 767px)` rules in index.html, so the JS-visible mode and
 * the CSS-applied layout can never disagree.
 *
 * Mode is decided by viewport width (what actually drives layout). Touch and
 * UA-mobile are reported separately because they are different questions:
 * a narrow desktop window is "mobile layout, not touch"; an iPad is "touch,
 * desktop layout".
 */
export const MOBILE_MAX_WIDTH = 767

const NARROW_QUERY = `(max-width: ${MOBILE_MAX_WIDTH}px)`
const COARSE_QUERY = '(pointer: coarse)'

function uaSaysMobile() {
  // userAgentData is the modern signal (Chromium); fall back to the UA string.
  const uad = navigator.userAgentData
  if (uad && typeof uad.mobile === 'boolean') return uad.mobile
  return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '')
}

/** Snapshot of the current device characteristics. */
export function detectDevice() {
  const narrow = window.matchMedia(NARROW_QUERY).matches
  const touch = window.matchMedia(COARSE_QUERY).matches || navigator.maxTouchPoints > 0
  return {
    mode: narrow ? 'mobile' : 'desktop',
    touch,
    uaMobile: uaSaysMobile(),
    width: window.innerWidth,
  }
}

function apply(root) {
  const d = detectDevice()
  root.setAttribute('data-device', d.mode)
  root.setAttribute('data-touch', String(d.touch))
  window.__lpDevice = d // read by automated evaluation + handy in devtools
  return d
}

/**
 * Apply the detected mode to <html> and keep it current on resize/rotation.
 * Returns an unsubscribe function.
 */
export function installDeviceMode(root = document.documentElement) {
  apply(root)
  const mq = window.matchMedia(NARROW_QUERY)
  const onChange = () => apply(root)
  mq.addEventListener('change', onChange)
  window.addEventListener('orientationchange', onChange)
  return () => {
    mq.removeEventListener('change', onChange)
    window.removeEventListener('orientationchange', onChange)
  }
}
