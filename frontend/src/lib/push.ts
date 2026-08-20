import { push as pushApi } from '@/lib/api'

export function isPushSupported(): boolean {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window
}

/** Web Push wants the VAPID public key as a raw Uint8Array, but the server
 * hands it over base64url-encoded (see backend/app/services/push_service.py). */
function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const base64Safe = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64Safe)
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

async function registration(): Promise<ServiceWorkerRegistration> {
  return (await navigator.serviceWorker.getRegistration('/sw.js')) || navigator.serviceWorker.register('/sw.js')
}

export async function getExistingSubscription(): Promise<PushSubscription | null> {
  if (!isPushSupported()) return null
  const reg = await registration()
  return reg.pushManager.getSubscription()
}

/** Requests notification permission (browser prompt) and subscribes this
 * device. Throws if the user denies permission or the browser blocks it. */
export async function enablePushOnThisDevice(): Promise<void> {
  if (!isPushSupported()) throw new Error('Push not supported in this browser')

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') throw new Error('Notification permission denied')

  const { public_key } = await pushApi.vapidPublicKey()
  const reg = await registration()
  let sub = await reg.pushManager.getSubscription()
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(public_key) as BufferSource,
    })
  }
  const json = sub.toJSON()
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error('Browser returned an incomplete push subscription')
  }
  await pushApi.subscribe({
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
    user_agent: navigator.userAgent,
  })
}

export async function disablePushOnThisDevice(): Promise<void> {
  const sub = await getExistingSubscription()
  if (!sub) return
  const endpoint = sub.endpoint
  await sub.unsubscribe()
  await pushApi.unsubscribe(endpoint)
}
