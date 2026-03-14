import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import type { SSEEventMap } from '../composables/useSSE'

/**
 * Minimal EventSource mock that captures addEventListener calls
 * and provides helpers to simulate server events.
 */
class MockEventSource {
  static instances: MockEventSource[] = []

  url: string
  onopen: ((event: Event) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  readyState = 0 // CONNECTING

  private _listeners: Map<string, Array<(e: MessageEvent) => void>> = new Map()
  closed = false

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
    // Simulate async open
    queueMicrotask(() => {
      if (!this.closed) {
        this.readyState = 1 // OPEN
        this.onopen?.(new Event('open'))
      }
    })
  }

  addEventListener(type: string, handler: EventListener): void {
    if (!this._listeners.has(type)) {
      this._listeners.set(type, [])
    }
    this._listeners.get(type)!.push(handler as (e: MessageEvent) => void)
  }

  removeEventListener(type: string, handler: EventListener): void {
    const handlers = this._listeners.get(type)
    if (handlers) {
      const idx = handlers.indexOf(handler as (e: MessageEvent) => void)
      if (idx !== -1) handlers.splice(idx, 1)
    }
  }

  close(): void {
    this.closed = true
    this.readyState = 2 // CLOSED
  }

  /** Test helper: simulate the server sending a typed event. */
  simulateEvent(eventType: string, data: unknown): void {
    const handlers = this._listeners.get(eventType) ?? []
    const messageEvent = new MessageEvent(eventType, {
      data: JSON.stringify(data),
    })
    for (const handler of handlers) {
      handler(messageEvent)
    }
  }

  /** Test helper: simulate an error (triggers reconnection in real EventSource). */
  simulateError(): void {
    this.readyState = 0
    this.onerror?.(new Event('error'))
  }

  static reset(): void {
    MockEventSource.instances = []
  }
}

// Install mock before each test
beforeEach(() => {
  MockEventSource.reset()
  vi.stubGlobal('EventSource', MockEventSource)
})

afterEach(() => {
  // Reset module state between tests so the singleton connection doesn't leak
  vi.resetModules()
  vi.unstubAllGlobals()
})

/** Helper to dynamically import useSSE with fresh module state. */
async function freshUseSSE() {
  const mod = await import('../composables/useSSE')
  return mod.useSSE
}

/** Helper to create a test component that uses the composable. */
function createTestComponent(setupFn: () => ReturnType<Awaited<ReturnType<typeof freshUseSSE>>>) {
  return defineComponent({
    setup() {
      const result = setupFn()
      return { sseResult: result }
    },
    template: '<div></div>',
  })
}

describe('useSSE', () => {
  it('connects to the SSE endpoint on first use', async () => {
    const useSSE = await freshUseSSE()
    const Component = createTestComponent(() => useSSE())
    mount(Component)

    expect(MockEventSource.instances).toHaveLength(1)
    expect(MockEventSource.instances[0]!.url).toBe('/api/v1/events')
  })

  it('sets isConnected to true when EventSource opens', async () => {
    const useSSE = await freshUseSSE()
    let sseReturn: ReturnType<typeof useSSE> | undefined
    const Component = defineComponent({
      setup() {
        sseReturn = useSSE()
        return {}
      },
      template: '<div></div>',
    })

    mount(Component)
    expect(sseReturn!.isConnected.value).toBe(false)

    // Let the microtask (onopen) run
    await flushPromises()
    expect(sseReturn!.isConnected.value).toBe(true)
  })

  it('sets isConnected to false on EventSource error', async () => {
    const useSSE = await freshUseSSE()
    let sseReturn: ReturnType<typeof useSSE> | undefined
    const Component = defineComponent({
      setup() {
        sseReturn = useSSE()
        return {}
      },
      template: '<div></div>',
    })

    mount(Component)
    await flushPromises()
    expect(sseReturn!.isConnected.value).toBe(true)

    MockEventSource.instances[0]!.simulateError()
    expect(sseReturn!.isConnected.value).toBe(false)
  })

  it('delivers typed events to subscribed callbacks', async () => {
    const useSSE = await freshUseSSE()
    const handler = vi.fn()

    const Component = defineComponent({
      setup() {
        const sse = useSSE()
        sse.on('download-progress', handler)
        return {}
      },
      template: '<div></div>',
    })

    mount(Component)
    await flushPromises()

    const payload: SSEEventMap['download-progress'] = {
      model_id: 'facebook/mms-tts-eng',
      progress: 42,
    }
    MockEventSource.instances[0]!.simulateEvent('download-progress', payload)

    expect(handler).toHaveBeenCalledOnce()
    expect(handler).toHaveBeenCalledWith(payload)
  })

  it('does not deliver events to unsubscribed callbacks', async () => {
    const useSSE = await freshUseSSE()
    const handler = vi.fn()

    const Component = defineComponent({
      setup() {
        const sse = useSSE()
        sse.on('download-progress', handler)
        sse.off('download-progress', handler)
        return {}
      },
      template: '<div></div>',
    })

    mount(Component)
    await flushPromises()

    MockEventSource.instances[0]!.simulateEvent('download-progress', {
      model_id: 'test',
      progress: 50,
    })

    expect(handler).not.toHaveBeenCalled()
  })

  it('does not deliver events of a different type to a callback', async () => {
    const useSSE = await freshUseSSE()
    const handler = vi.fn()

    const Component = defineComponent({
      setup() {
        const sse = useSSE()
        sse.on('job-progress', handler)
        return {}
      },
      template: '<div></div>',
    })

    mount(Component)
    await flushPromises()

    MockEventSource.instances[0]!.simulateEvent('download-progress', {
      model_id: 'test',
      progress: 10,
    })

    expect(handler).not.toHaveBeenCalled()
  })

  it('shares a single EventSource across multiple composable instances', async () => {
    const useSSE = await freshUseSSE()

    const Component = defineComponent({
      setup() {
        useSSE()
        useSSE()
        return {}
      },
      template: '<div></div>',
    })

    mount(Component)
    expect(MockEventSource.instances).toHaveLength(1)
  })

  it('cleans up listeners when the component unmounts', async () => {
    const useSSE = await freshUseSSE()
    const handler = vi.fn()

    const Component = defineComponent({
      setup() {
        const sse = useSSE()
        sse.on('job-completed', handler)
        return {}
      },
      template: '<div></div>',
    })

    const wrapper = mount(Component)
    await flushPromises()

    wrapper.unmount()

    // The EventSource was closed (only consumer disconnected)
    expect(MockEventSource.instances[0]!.closed).toBe(true)
  })

  it('closes EventSource when last consumer unmounts', async () => {
    const useSSE = await freshUseSSE()

    const Component1 = defineComponent({
      setup() {
        useSSE()
        return {}
      },
      template: '<div></div>',
    })
    const Component2 = defineComponent({
      setup() {
        useSSE()
        return {}
      },
      template: '<div></div>',
    })

    const w1 = mount(Component1)
    const w2 = mount(Component2)
    expect(MockEventSource.instances).toHaveLength(1)

    w1.unmount()
    // Still one consumer — connection stays open
    expect(MockEventSource.instances[0]!.closed).toBe(false)

    w2.unmount()
    // Last consumer gone — connection closed
    expect(MockEventSource.instances[0]!.closed).toBe(true)
  })

  it('ignores malformed JSON in event data', async () => {
    const useSSE = await freshUseSSE()
    const handler = vi.fn()

    const Component = defineComponent({
      setup() {
        const sse = useSSE()
        sse.on('download-progress', handler)
        return {}
      },
      template: '<div></div>',
    })

    mount(Component)
    await flushPromises()

    // Simulate a raw event with invalid JSON
    const es = MockEventSource.instances[0]!
    const listeners = (es as any)._listeners.get('download-progress') ?? []
    const badEvent = new MessageEvent('download-progress', { data: 'not-json' })
    for (const l of listeners) l(badEvent)

    expect(handler).not.toHaveBeenCalled()
  })

  it('supports multiple handlers for the same event type', async () => {
    const useSSE = await freshUseSSE()
    const handler1 = vi.fn()
    const handler2 = vi.fn()

    const Component = defineComponent({
      setup() {
        const sse = useSSE()
        sse.on('job-failed', handler1)
        sse.on('job-failed', handler2)
        return {}
      },
      template: '<div></div>',
    })

    mount(Component)
    await flushPromises()

    const payload: SSEEventMap['job-failed'] = {
      job_id: '123',
      type: 'synthesis',
      error_message: 'Out of VRAM',
    }
    MockEventSource.instances[0]!.simulateEvent('job-failed', payload)

    expect(handler1).toHaveBeenCalledWith(payload)
    expect(handler2).toHaveBeenCalledWith(payload)
  })
})
