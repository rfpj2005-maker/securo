import { useSyncExternalStore, useCallback } from 'react'

const STORAGE_KEY = 'updateCheckEnabled'

const listeners = new Set<() => void>()

function getSnapshot(): boolean {
  const raw = localStorage.getItem(STORAGE_KEY)
  // Defaults to off on this instance — Claude tracks upstream releases and
  // tells the owner directly when one is actually worth adopting, instead
  // of the app nagging everyone about every tag. Still a real per-browser
  // toggle if someone wants it back on for themselves.
  return raw === null ? false : raw === 'true'
}

function subscribe(cb: () => void) {
  listeners.add(cb)
  return () => listeners.delete(cb)
}

function notify() {
  listeners.forEach((cb) => cb())
}

export function useAutoUpdateCheck() {
  const enabled = useSyncExternalStore(subscribe, getSnapshot, () => true)

  const setEnabled = useCallback((next: boolean) => {
    localStorage.setItem(STORAGE_KEY, String(next))
    notify()
  }, [])

  return { enabled, setEnabled } as const
}
