import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ModelsView from '../views/ModelsView.vue'
import type { Model } from '@/api/models'

const sseHandlers: Record<string, ((...args: any[]) => void)[]> = {}

vi.mock('@/composables/useSSE', () => ({
  useSSE: () => ({
    on: (event: string, handler: (...args: any[]) => void) => {
      if (!sseHandlers[event]) sseHandlers[event] = []
      sseHandlers[event].push(handler)
    },
    off: (event: string, handler: (...args: any[]) => void) => {
      const list = sseHandlers[event]
      if (list) {
        const idx = list.indexOf(handler)
        if (idx !== -1) list.splice(idx, 1)
      }
    },
    isConnected: { value: true },
  }),
}))

const mockFetchModels = vi.fn<() => Promise<Model[]>>()
const mockDownloadModel = vi.fn()
const mockLoadModel = vi.fn()

vi.mock('@/api/models', () => ({
  fetchModels: (...args: unknown[]) => mockFetchModels(...(args as [])),
  downloadModel: (...args: unknown[]) => mockDownloadModel(...args),
  loadModel: (...args: unknown[]) => mockLoadModel(...args),
}))

/** Default FOSS license metadata shared by fixtures that don't exercise the disclosure. */
const FOSS = { license: 'Apache-2.0', license_is_foss: true, license_notice: null }

function sampleModels(): Model[] {
  return [
    { model_id: 'facebook/mms-tts-eng', name: 'MMS TTS English', is_cached: false, is_loaded: false, loader_available: true, ...FOSS },
    { model_id: 'facebook/mms-tts-ita', name: 'MMS TTS Italian', is_cached: true, is_loaded: false, loader_available: true, ...FOSS },
    { model_id: 'facebook/mms-tts-fra', name: 'MMS TTS French', is_cached: true, is_loaded: true, loader_available: true, ...FOSS },
  ]
}

/** Mixed set: two models with an adapter, two without (distinct names to avoid substring clashes). */
function mixedModels(): Model[] {
  return [
    { model_id: 'with/sigma-cached', name: 'Sigma Cached', is_cached: true, is_loaded: false, loader_available: true, ...FOSS },
    { model_id: 'with/sigma-remote', name: 'Sigma Remote', is_cached: false, is_loaded: false, loader_available: true, ...FOSS },
    { model_id: 'no/omega-cached', name: 'Omega Cached', is_cached: true, is_loaded: false, loader_available: false, ...FOSS },
    { model_id: 'no/omega-remote', name: 'Omega Remote', is_cached: false, is_loaded: false, loader_available: false, ...FOSS },
  ]
}

async function mountView() {
  const wrapper = mount(ModelsView)
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  for (const key of Object.keys(sseHandlers)) delete sseHandlers[key]
  mockFetchModels.mockResolvedValue(sampleModels())
  mockDownloadModel.mockResolvedValue({ model_id: 'test', status: 'downloading' })
  mockLoadModel.mockResolvedValue({ model_id: 'test', status: 'loaded' })
})

describe('ModelsView', () => {
  it('displays a list of models on mount', async () => {
    const wrapper = await mountView()
    const items = wrapper.findAll('.model-item')
    expect(items).toHaveLength(3)
    expect(items[0]!.text()).toContain('MMS TTS English')
    expect(items[1]!.text()).toContain('MMS TTS Italian')
    expect(items[2]!.text()).toContain('MMS TTS French')
  })

  it('shows cache status badges correctly', async () => {
    const wrapper = await mountView()
    const badges = wrapper.findAll('.badge')
    expect(badges[0]!.text()).toBe('Not cached')
    expect(badges[0]!.classes()).toContain('badge-remote')
    expect(badges[1]!.text()).toBe('Cached')
    expect(badges[1]!.classes()).toContain('badge-cached')
    expect(badges[2]!.text()).toBe('Loaded')
    expect(badges[2]!.classes()).toContain('badge-loaded')
  })

  it('shows the currently loaded model in a banner', async () => {
    const wrapper = await mountView()
    const banner = wrapper.find('.loaded-banner')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('MMS TTS French')
  })

  it('shows Download button only for non-cached models', async () => {
    const wrapper = await mountView()
    const buttons = wrapper.findAll('button')
    const downloadButtons = buttons.filter((b) => b.text() === 'Download')
    expect(downloadButtons).toHaveLength(1)
  })

  it('shows Load button only for cached but not loaded models', async () => {
    const wrapper = await mountView()
    const buttons = wrapper.findAll('button')
    const loadButtons = buttons.filter((b) => b.text() === 'Load')
    expect(loadButtons).toHaveLength(1)
  })

  it('calls downloadModel when Download button is clicked', async () => {
    const wrapper = await mountView()
    const downloadBtn = wrapper.findAll('button').find((b) => b.text() === 'Download')!
    await downloadBtn.trigger('click')
    await flushPromises()
    expect(mockDownloadModel).toHaveBeenCalledWith('facebook/mms-tts-eng')
  })

  it('shows download progress from SSE events', async () => {
    const wrapper = await mountView()
    await wrapper.findAll('button').find((b) => b.text() === 'Download')!.trigger('click')
    await flushPromises()

    // Simulate SSE download-progress event
    for (const handler of sseHandlers['download-progress'] ?? []) {
      handler({ model_id: 'facebook/mms-tts-eng', progress: 42 })
    }
    await flushPromises()

    const progress = wrapper.find('progress')
    expect(progress.exists()).toBe(true)
    expect(progress.attributes('value')).toBe('42')
    expect(wrapper.find('.progress-text').text()).toBe('42%')
  })

  it('refreshes model list on download-completed SSE event', async () => {
    const wrapper = await mountView()
    expect(mockFetchModels).toHaveBeenCalledTimes(1)

    for (const handler of sseHandlers['download-completed'] ?? []) {
      handler({ model_id: 'facebook/mms-tts-eng' })
    }
    await flushPromises()

    expect(mockFetchModels).toHaveBeenCalledTimes(2)
  })

  it('shows download error from SSE download-failed event', async () => {
    const wrapper = await mountView()
    await wrapper.findAll('button').find((b) => b.text() === 'Download')!.trigger('click')
    await flushPromises()

    for (const handler of sseHandlers['download-failed'] ?? []) {
      handler({ model_id: 'facebook/mms-tts-eng', error_message: 'Network error' })
    }
    await flushPromises()

    expect(wrapper.text()).toContain('Network error')
  })

  it('shows insufficient disk space error on download', async () => {
    const diskErr = new Error('Insufficient disk space') as Error & {
      estimated_mb?: number
      available_mb?: number
    }
    diskErr.estimated_mb = 2048
    diskErr.available_mb = 500
    mockDownloadModel.mockRejectedValueOnce(diskErr)

    const wrapper = await mountView()
    await wrapper.findAll('button').find((b) => b.text() === 'Download')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('need 2048 MB')
    expect(wrapper.text()).toContain('have 500 MB')
  })

  it('calls loadModel and refreshes on Load button click', async () => {
    const wrapper = await mountView()
    const loadBtn = wrapper.findAll('button').find((b) => b.text() === 'Load')!
    await loadBtn.trigger('click')
    await flushPromises()

    expect(mockLoadModel).toHaveBeenCalledWith('facebook/mms-tts-ita')
    // refresh is called after successful load
    expect(mockFetchModels).toHaveBeenCalledTimes(2)
  })

  it('shows insufficient VRAM error on load', async () => {
    const vramErr = new Error('Insufficient VRAM') as Error & {
      required_mb?: number
      available_mb?: number
    }
    vramErr.required_mb = 4096
    vramErr.available_mb = 2048
    mockLoadModel.mockRejectedValueOnce(vramErr)

    const wrapper = await mountView()
    const loadBtn = wrapper.findAll('button').find((b) => b.text() === 'Load')!
    await loadBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('need 4096 MB')
    expect(wrapper.text()).toContain('have 2048 MB')
  })

  it('shows error message when fetchModels fails', async () => {
    mockFetchModels.mockRejectedValueOnce(new Error('Server error'))
    const wrapper = await mountView()
    expect(wrapper.text()).toContain('Server error')
  })

  it('shows empty state when no models are available', async () => {
    mockFetchModels.mockResolvedValueOnce([])
    const wrapper = await mountView()
    expect(wrapper.text()).toContain('No models available')
  })

  it('disables Load buttons while a model is loading', async () => {
    // Make loadModel hang
    mockLoadModel.mockReturnValueOnce(new Promise(() => {}))

    const wrapper = await mountView()
    const loadBtn = wrapper.findAll('button').find((b) => b.text() === 'Load')!
    await loadBtn.trigger('click')
    await flushPromises()

    // Button should now show "Loading..." and be disabled
    const loadingBtn = wrapper.findAll('button').find((b) => b.text() === 'Loading...')
    expect(loadingBtn).toBeDefined()
    expect(loadingBtn!.attributes('disabled')).toBeDefined()
  })
})

describe('ModelsView adapter-availability grouping', () => {
  it('splits models into an available list and an adapter-not-yet-available list', async () => {
    mockFetchModels.mockResolvedValueOnce(mixedModels())
    const wrapper = await mountView()

    const available = wrapper.find('.model-list-available')
    const unavailable = wrapper.find('.model-list-unavailable')
    expect(available.exists()).toBe(true)
    expect(unavailable.exists()).toBe(true)

    const availableItems = available.findAll('.model-item')
    const unavailableItems = unavailable.findAll('.model-item')
    expect(availableItems).toHaveLength(2)
    expect(unavailableItems).toHaveLength(2)

    expect(available.text()).toContain('Sigma Cached')
    expect(available.text()).toContain('Sigma Remote')
    expect(available.text()).not.toContain('Omega')

    expect(unavailable.text()).toContain('Omega Cached')
    expect(unavailable.text()).toContain('Omega Remote')
    expect(unavailable.text()).not.toContain('Sigma')
  })

  it('renders the available list before the adapter-not-yet-available list', async () => {
    mockFetchModels.mockResolvedValueOnce(mixedModels())
    const wrapper = await mountView()

    const sections = wrapper.findAll('.model-section')
    expect(sections).toHaveLength(2)
    expect(sections[0]!.classes()).toContain('model-section-available')
    expect(sections[1]!.classes()).toContain('model-section-unavailable')
  })

  it('does not show Download or Load buttons for models without an adapter', async () => {
    mockFetchModels.mockResolvedValueOnce(mixedModels())
    const wrapper = await mountView()

    const unavailable = wrapper.find('.model-list-unavailable')
    expect(unavailable.findAll('button')).toHaveLength(0)
    // Only the adapter-backed cached model offers a Load button (the adapterless one does not)
    const loadButtons = wrapper.findAll('button').filter((b) => b.text() === 'Load')
    expect(loadButtons).toHaveLength(1)
    // Only the adapter-backed remote model offers a Download button (the adapterless one does not)
    const downloadButtons = wrapper.findAll('button').filter((b) => b.text() === 'Download')
    expect(downloadButtons).toHaveLength(1)
  })

  it('marks adapterless models with a No adapter badge and keeps their cache status', async () => {
    mockFetchModels.mockResolvedValueOnce(mixedModels())
    const wrapper = await mountView()

    const unavailable = wrapper.find('.model-list-unavailable')
    const noAdapterBadges = unavailable.findAll('.badge-no-adapter')
    expect(noAdapterBadges).toHaveLength(2)
    expect(unavailable.find('.badge-cached').exists()).toBe(true)
    expect(unavailable.find('.badge-remote').exists()).toBe(true)
  })

  it('hides the adapter-not-yet-available section when every model has an adapter', async () => {
    // sampleModels() are all loader_available: true
    const wrapper = await mountView()
    expect(wrapper.find('.model-section-available').exists()).toBe(true)
    expect(wrapper.find('.model-section-unavailable').exists()).toBe(false)
  })

  it('hides the available section when no model has an adapter', async () => {
    mockFetchModels.mockResolvedValueOnce([
      { model_id: 'no/adapter', name: 'No Adapter', is_cached: false, is_loaded: false, loader_available: false, ...FOSS },
    ])
    const wrapper = await mountView()
    expect(wrapper.find('.model-section-available').exists()).toBe(false)
    expect(wrapper.find('.model-section-unavailable').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('No models available')
  })
})

describe('ModelsView license disclosure', () => {
  /**
   * Two non-FOSS models — one with an adapter (available list), one without
   * (adapter-not-yet-available list) — plus one FOSS model, to prove the notice
   * is rendered for every non-FOSS model regardless of which list it falls in.
   */
  function licenseModels(): Model[] {
    return [
      {
        model_id: 'foss/apache',
        name: 'Apache Model',
        is_cached: false,
        is_loaded: false,
        loader_available: true,
        license: 'Apache-2.0',
        license_is_foss: true,
        license_notice: null,
      },
      {
        model_id: 'nonfoss/with-adapter',
        name: 'Research Adapter Model',
        is_cached: false,
        is_loaded: false,
        loader_available: true,
        license: 'Fish Audio Research License',
        license_is_foss: false,
        license_notice: 'Free for personal use; commercial use requires a separate license.',
      },
      {
        model_id: 'nonfoss/no-adapter',
        name: 'Research No-Adapter Model',
        is_cached: false,
        is_loaded: false,
        loader_available: false,
        license: 'Boson Research & Non-Commercial License',
        license_is_foss: false,
        license_notice: 'Non-commercial use only; commercial use requires a paid license.',
      },
    ]
  }

  it('renders a license notice only for non-FOSS models', async () => {
    mockFetchModels.mockResolvedValueOnce(licenseModels())
    const wrapper = await mountView()

    // Two non-FOSS models → two notices; the FOSS model has none.
    const notices = wrapper.findAll('.license-notice')
    expect(notices).toHaveLength(2)
  })

  it('shows the license notice text and license name for a non-FOSS model', async () => {
    mockFetchModels.mockResolvedValueOnce(licenseModels())
    const wrapper = await mountView()

    expect(wrapper.text()).toContain('Free for personal use; commercial use requires a separate license.')
    expect(wrapper.text()).toContain('Fish Audio Research License')
  })

  it('renders the notice for non-FOSS models in both the available and unavailable lists', async () => {
    mockFetchModels.mockResolvedValueOnce(licenseModels())
    const wrapper = await mountView()

    const available = wrapper.find('.model-list-available')
    const unavailable = wrapper.find('.model-list-unavailable')
    expect(available.find('.license-notice').exists()).toBe(true)
    expect(unavailable.find('.license-notice').exists()).toBe(true)
  })

  it('does not render any license notice when every model is FOSS', async () => {
    // sampleModels() are all FOSS
    const wrapper = await mountView()
    expect(wrapper.findAll('.license-notice')).toHaveLength(0)
  })

  it('falls back to a generic notice when a non-FOSS model lacks an explicit notice', async () => {
    mockFetchModels.mockResolvedValueOnce([
      {
        model_id: 'nonfoss/no-notice',
        name: 'No Notice Model',
        is_cached: false,
        is_loaded: false,
        loader_available: true,
        license: 'Custom Research License',
        license_is_foss: false,
        license_notice: null,
      },
    ])
    const wrapper = await mountView()

    const notice = wrapper.find('.license-notice')
    expect(notice.exists()).toBe(true)
    expect(notice.text()).toContain('Custom Research License')
    expect(notice.text()).toContain('free for personal use')
  })
})
