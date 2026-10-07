import { useEffect } from 'react'

/**
 * Fade/slide `.reveal` elements in once they reach the viewport. Re-scans when `key` changes (e.g. route).
 * Anything at or above the bottom of the screen is revealed, so fast scrolls and jumps (End key, anchor
 * links, full-page screenshots) never leave a section hidden.
 */
export function useReveal(key: unknown) {
  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let frame = 0
    const check = () => {
      frame = 0
      const limit = window.innerHeight * 0.94
      document.querySelectorAll<HTMLElement>('.reveal:not(.in)').forEach((el) => {
        if (reduce || el.getBoundingClientRect().top < limit) el.classList.add('in')
      })
    }
    const schedule = () => { if (!frame) frame = requestAnimationFrame(check) }
    check()
    // Content renders after data loads, so check again shortly after mount.
    const timers = [150, 500, 1200].map((ms) => window.setTimeout(check, ms))
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      timers.forEach(clearTimeout)
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [key])
}
