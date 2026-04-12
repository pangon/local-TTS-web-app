import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CreateView from '../views/CreateView.vue'

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

const mockCreateSynthesisJob = vi.fn()

vi.mock('@/api/jobs', () => ({
  createSynthesisJob: (...args: unknown[]) => mockCreateSynthesisJob(...args),
}))

function makeFile(name: string, sizeBytes: number, content = 'Hello world'): File {
  const data = content.padEnd(sizeBytes, ' ')
  return new File([data], name, { type: 'text/plain' })
}

async function mountView() {
  const wrapper = mount(CreateView)
  await flushPromises()
  return wrapper
}

async function selectFile(wrapper: ReturnType<typeof mount>, file: File) {
  const input = wrapper.find('input[type="file"]')
  // Create a mock FileList-like structure on the input element
  Object.defineProperty(input.element, 'files', {
    value: [file],
    writable: false,
    configurable: true,
  })
  await input.trigger('change')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  for (const key of Object.keys(sseHandlers)) delete sseHandlers[key]
  mockCreateSynthesisJob.mockResolvedValue({
    id: 'job-1',
    type: 'synthesis',
    status: 'queued',
    progress: 0,
    created_at: '2026-04-12T10:00:00Z',
  })
})

describe('CreateView', () => {
  it('renders the heading and file input', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('h1').text()).toBe('Create Audiobook')
    expect(wrapper.find('input[type="file"]').exists()).toBe(true)
  })

  it('disables Start Synthesis button when no file is selected', async () => {
    const wrapper = await mountView()
    const btn = wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('enables Start Synthesis button when a valid .txt file is selected', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    const btn = wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('shows error when non-.txt file is selected', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, new File(['data'], 'image.png', { type: 'image/png' }))
    expect(wrapper.text()).toContain('Only .txt files are accepted')
    const btn = wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('shows error when file exceeds 2 MB', async () => {
    const wrapper = await mountView()
    const bigFile = makeFile('big.txt', 3 * 1024 * 1024)
    await selectFile(wrapper, bigFile)
    expect(wrapper.text()).toContain('File exceeds the 2 MB size limit')
    const btn = wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('shows file info when a valid file is selected', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('mybook.txt', 1024))
    expect(wrapper.find('.file-name').text()).toBe('mybook.txt')
    expect(wrapper.find('.file-size').exists()).toBe(true)
  })

  it('calls createSynthesisJob with selected file on submit', async () => {
    const wrapper = await mountView()
    const file = makeFile('book.txt', 100)
    await selectFile(wrapper, file)

    const btn = wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!
    await btn.trigger('click')
    await flushPromises()

    expect(mockCreateSynthesisJob).toHaveBeenCalledWith(file)
  })

  it('displays job status after successful submission', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))

    const btn = wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!
    await btn.trigger('click')
    await flushPromises()

    expect(wrapper.find('.progress-section').exists()).toBe(true)
    expect(wrapper.text()).toContain('queued')
  })

  it('shows submit error on API failure', async () => {
    mockCreateSynthesisJob.mockRejectedValueOnce(new Error('No model loaded'))

    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('No model loaded')
  })

  it('shows disk space error with details', async () => {
    const err = new Error('Insufficient disk space') as Error & {
      estimated_mb?: number
      available_mb?: number
    }
    err.estimated_mb = 20.5
    err.available_mb = 1.0
    mockCreateSynthesisJob.mockRejectedValueOnce(err)

    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('need 20.5 MB')
    expect(wrapper.text()).toContain('have 1 MB')
  })

  it('updates progress from SSE job-progress events', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    // Simulate job-progress SSE event
    for (const handler of sseHandlers['job-progress'] ?? []) {
      handler({ job_id: 'job-1', type: 'synthesis', status: 'processing', progress: 42 })
    }
    await flushPromises()

    expect(wrapper.text()).toContain('processing')
    const progress = wrapper.find('progress')
    expect(progress.exists()).toBe(true)
    expect(progress.attributes('value')).toBe('42')
    expect(wrapper.find('.progress-text').text()).toBe('42%')
  })

  it('ignores SSE events for other jobs', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    for (const handler of sseHandlers['job-progress'] ?? []) {
      handler({ job_id: 'other-job', type: 'synthesis', status: 'processing', progress: 99 })
    }
    await flushPromises()

    // Should still show the original queued status, not the event for the other job
    expect(wrapper.text()).toContain('queued')
  })

  it('shows success message on job-completed SSE event', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    for (const handler of sseHandlers['job-completed'] ?? []) {
      handler({ job_id: 'job-1', type: 'synthesis', audiobook_id: 'ab-1' })
    }
    await flushPromises()

    expect(wrapper.text()).toContain('completed')
    expect(wrapper.text()).toContain('Audiobook created successfully')
  })

  it('shows error message on job-failed SSE event', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    for (const handler of sseHandlers['job-failed'] ?? []) {
      handler({ job_id: 'job-1', type: 'synthesis', error_message: 'Out of VRAM' })
    }
    await flushPromises()

    expect(wrapper.text()).toContain('failed')
    expect(wrapper.text()).toContain('Out of VRAM')
  })

  it('shows New Audiobook button after completion', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    // No "New Audiobook" button yet
    expect(wrapper.findAll('button').find((b) => b.text() === 'New Audiobook')).toBeUndefined()

    for (const handler of sseHandlers['job-completed'] ?? []) {
      handler({ job_id: 'job-1', type: 'synthesis', audiobook_id: 'ab-1' })
    }
    await flushPromises()

    const newBtn = wrapper.findAll('button').find((b) => b.text() === 'New Audiobook')
    expect(newBtn).toBeDefined()
  })

  it('resets form when New Audiobook is clicked', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    for (const handler of sseHandlers['job-completed'] ?? []) {
      handler({ job_id: 'job-1', type: 'synthesis', audiobook_id: 'ab-1' })
    }
    await flushPromises()

    await wrapper.findAll('button').find((b) => b.text() === 'New Audiobook')!.trigger('click')
    await flushPromises()

    // Progress section should be gone
    expect(wrapper.find('.progress-section').exists()).toBe(false)
    // File info should be gone
    expect(wrapper.find('.file-name').exists()).toBe(false)
  })

  it('disables submit button while a job is active', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    const btn = wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('disables file input while a job is active', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    await wrapper.findAll('button').find((b) => b.text() === 'Start Synthesis')!.trigger('click')
    await flushPromises()

    const input = wrapper.find('input[type="file"]')
    expect(input.attributes('disabled')).toBeDefined()
  })
})
