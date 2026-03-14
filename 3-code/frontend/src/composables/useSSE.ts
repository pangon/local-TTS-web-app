/**
 * Vue composable for consuming Server-Sent Events from the backend.
 *
 * Connects to /api/v1/events via the browser EventSource API (DEC-sse-progress).
 * Views subscribe to specific event types with typed callbacks.
 * Reconnection is handled automatically by EventSource.
 */

import { ref, readonly, onUnmounted, type Ref } from 'vue'

/** All SSE event types emitted by the backend. */
export type SSEEventType =
  | 'job-progress'
  | 'job-completed'
  | 'job-failed'
  | 'download-progress'
  | 'download-completed'
  | 'download-failed'

/** Payloads for each event type, matching the API design. */
export interface JobProgressEvent {
  job_id: string
  type: 'synthesis' | 'preview'
  status: string
  progress: number
}

export interface JobCompletedEvent {
  job_id: string
  type: 'synthesis' | 'preview'
  audiobook_id: string | null
}

export interface JobFailedEvent {
  job_id: string
  type: 'synthesis' | 'preview'
  error_message: string
}

export interface DownloadProgressEvent {
  model_id: string
  progress: number
}

export interface DownloadCompletedEvent {
  model_id: string
}

export interface DownloadFailedEvent {
  model_id: string
  error_message: string
}

/** Maps event type names to their payload types. */
export interface SSEEventMap {
  'job-progress': JobProgressEvent
  'job-completed': JobCompletedEvent
  'job-failed': JobFailedEvent
  'download-progress': DownloadProgressEvent
  'download-completed': DownloadCompletedEvent
  'download-failed': DownloadFailedEvent
}

export type SSECallback<T extends SSEEventType> = (data: SSEEventMap[T]) => void

const SSE_URL = '/api/v1/events'

type Listener = { eventType: SSEEventType; callback: SSECallback<any> }

/**
 * Singleton SSE connection state shared across all composable instances.
 * A single EventSource is reused so multiple views don't open parallel connections.
 */
let eventSource: EventSource | null = null
const listeners: Listener[] = []
const connected = ref(false)
let refCount = 0

function ensureConnection(): void {
  if (eventSource !== null) return

  eventSource = new EventSource(SSE_URL)

  eventSource.onopen = () => {
    connected.value = true
  }

  eventSource.onerror = () => {
    // EventSource reconnects automatically; just update the status flag.
    connected.value = false
  }

  // Register a handler for each known event type.
  const eventTypes: SSEEventType[] = [
    'job-progress',
    'job-completed',
    'job-failed',
    'download-progress',
    'download-completed',
    'download-failed',
  ]

  for (const eventType of eventTypes) {
    eventSource.addEventListener(eventType, ((event: MessageEvent) => {
      let data: unknown
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }
      for (const listener of listeners) {
        if (listener.eventType === eventType) {
          listener.callback(data)
        }
      }
    }) as EventListener)
  }
}

function closeConnectionIfUnused(): void {
  if (refCount <= 0 && eventSource !== null) {
    eventSource.close()
    eventSource = null
    connected.value = false
  }
}

/**
 * Composable that provides typed SSE event subscriptions.
 *
 * Usage:
 * ```ts
 * const { on, off, isConnected } = useSSE()
 *
 * const handler = (data: DownloadProgressEvent) => {
 *   console.log(data.model_id, data.progress)
 * }
 * on('download-progress', handler)
 * // later: off('download-progress', handler)
 * ```
 *
 * The connection is opened when the first composable instance mounts
 * and closed when the last one unmounts.
 */
export function useSSE(): {
  on: <T extends SSEEventType>(eventType: T, callback: SSECallback<T>) => void
  off: <T extends SSEEventType>(eventType: T, callback: SSECallback<T>) => void
  isConnected: Readonly<Ref<boolean>>
} {
  const localListeners: Listener[] = []

  refCount++
  ensureConnection()

  function on<T extends SSEEventType>(eventType: T, callback: SSECallback<T>): void {
    const listener: Listener = { eventType, callback }
    listeners.push(listener)
    localListeners.push(listener)
  }

  function off<T extends SSEEventType>(eventType: T, callback: SSECallback<T>): void {
    // Remove from global listeners
    for (let i = listeners.length - 1; i >= 0; i--) {
      if (listeners[i].eventType === eventType && listeners[i].callback === callback) {
        listeners.splice(i, 1)
        break
      }
    }
    // Remove from local tracking
    for (let i = localListeners.length - 1; i >= 0; i--) {
      if (localListeners[i].eventType === eventType && localListeners[i].callback === callback) {
        localListeners.splice(i, 1)
        break
      }
    }
  }

  onUnmounted(() => {
    // Clean up all listeners registered by this composable instance
    for (const local of localListeners) {
      const idx = listeners.indexOf(local)
      if (idx !== -1) listeners.splice(idx, 1)
    }
    localListeners.length = 0

    refCount--
    closeConnectionIfUnused()
  })

  return {
    on,
    off,
    isConnected: readonly(connected),
  }
}
