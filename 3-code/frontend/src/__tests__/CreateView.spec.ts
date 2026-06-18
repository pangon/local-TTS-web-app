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

const mockPreprocessFile = vi.fn()
const mockCreateSynthesisJob = vi.fn()

vi.mock('@/api/preprocess', () => ({
  preprocessFile: (...args: unknown[]) => mockPreprocessFile(...args),
}))

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
  Object.defineProperty(input.element, 'files', {
    value: [file],
    writable: false,
    configurable: true,
  })
  await input.trigger('change')
  await flushPromises()
}

function findButton(wrapper: ReturnType<typeof mount>, text: string) {
  return wrapper.findAll('button').find((b) => b.text() === text)
}

/** Select a valid file and run the preprocess step, landing in the review state. */
async function reachReview(wrapper: ReturnType<typeof mount>, file = makeFile('book.txt', 100)) {
  await selectFile(wrapper, file)
  await findButton(wrapper, 'Preprocess & Review')!.trigger('click')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  for (const key of Object.keys(sseHandlers)) delete sseHandlers[key]
  mockPreprocessFile.mockResolvedValue({
    normalized_text: 'Normalized text venticinque per cento.',
    language: 'it',
    model_id: 'kokoro',
    original_char_count: 20,
    normalized_char_count: 38,
  })
  mockCreateSynthesisJob.mockResolvedValue({
    id: 'job-1',
    type: 'synthesis',
    status: 'queued',
    progress: 0,
    created_at: '2026-04-12T10:00:00Z',
  })
})

describe('CreateView — file selection', () => {
  it('renders the heading and file input', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('h1').text()).toBe('Create Audiobook')
    expect(wrapper.find('input[type="file"]').exists()).toBe(true)
  })

  it('disables Preprocess button when no file is selected', async () => {
    const wrapper = await mountView()
    expect(findButton(wrapper, 'Preprocess & Review')!.attributes('disabled')).toBeDefined()
  })

  it('enables Preprocess button when a valid .txt file is selected', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('book.txt', 100))
    expect(findButton(wrapper, 'Preprocess & Review')!.attributes('disabled')).toBeUndefined()
  })

  it('shows error when non-.txt file is selected', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, new File(['data'], 'image.png', { type: 'image/png' }))
    expect(wrapper.text()).toContain('Only .txt files are accepted')
    expect(findButton(wrapper, 'Preprocess & Review')!.attributes('disabled')).toBeDefined()
  })

  it('shows error when file exceeds 2 MB', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('big.txt', 3 * 1024 * 1024))
    expect(wrapper.text()).toContain('File exceeds the 2 MB size limit')
    expect(findButton(wrapper, 'Preprocess & Review')!.attributes('disabled')).toBeDefined()
  })

  it('shows file info when a valid file is selected', async () => {
    const wrapper = await mountView()
    await selectFile(wrapper, makeFile('mybook.txt', 1024))
    expect(wrapper.find('.file-name').text()).toBe('mybook.txt')
    expect(wrapper.find('.file-size').exists()).toBe(true)
  })
})

describe('CreateView — preprocess & review step', () => {
  it('calls preprocessFile with the selected file (and language) on click', async () => {
    const wrapper = await mountView()
    const file = makeFile('book.txt', 100)
    await reachReview(wrapper, file)
    expect(mockPreprocessFile).toHaveBeenCalledWith(file, undefined)
  })

  it('shows the normalized text in an editable textarea after preprocessing (AC1, AC2)', async () => {
    const wrapper = await mountView()
    await reachReview(wrapper)

    const textarea = wrapper.find('textarea.review-textarea')
    expect(textarea.exists()).toBe(true)
    expect((textarea.element as HTMLTextAreaElement).value).toBe(
      'Normalized text venticinque per cento.',
    )
    // Before/after counts are shown so the user can tell what changed.
    expect(wrapper.find('.char-counts').text()).toContain('20')
    expect(wrapper.find('.char-counts').text()).toContain('38')
  })

  it('does not call createSynthesisJob until the user confirms (no auto-start)', async () => {
    const wrapper = await mountView()
    await reachReview(wrapper)
    expect(mockCreateSynthesisJob).not.toHaveBeenCalled()
  })

  it('shows a preprocess error when preprocessing fails', async () => {
    mockPreprocessFile.mockRejectedValueOnce(new Error('No model loaded'))
    const wrapper = await mountView()
    await reachReview(wrapper)
    expect(wrapper.text()).toContain('No model loaded')
    // Stays on the selection step (no review textarea).
    expect(wrapper.find('textarea.review-textarea').exists()).toBe(false)
  })

  it('Start Over returns to the file-selection step', async () => {
    const wrapper = await mountView()
    await reachReview(wrapper)
    await findButton(wrapper, 'Start Over')!.trigger('click')
    await flushPromises()
    expect(wrapper.find('textarea.review-textarea').exists()).toBe(false)
    expect(wrapper.find('.file-name').exists()).toBe(false)
    expect(findButton(wrapper, 'Preprocess & Review')).toBeDefined()
  })
})

describe('CreateView — confirm & synthesize', () => {
  it('synthesizes exactly the reviewed text with filename and resolved language (AC3)', async () => {
    const wrapper = await mountView()
    await reachReview(wrapper, makeFile('mybook.txt', 100))

    await findButton(wrapper, 'Confirm & Start Synthesis')!.trigger('click')
    await flushPromises()

    expect(mockCreateSynthesisJob).toHaveBeenCalledWith({
      text: 'Normalized text venticinque per cento.',
      source_filename: 'mybook.txt',
      language: 'it',
    })
  })

  it('synthesizes the edited text when the user edits before confirming (AC3)', async () => {
    const wrapper = await mountView()
    await reachReview(wrapper)

    await wrapper.find('textarea.review-textarea').setValue('User-edited reviewed text.')
    await findButton(wrapper, 'Confirm & Start Synthesis')!.trigger('click')
    await flushPromises()

    expect(mockCreateSynthesisJob).toHaveBeenCalledWith(
      expect.objectContaining({ text: 'User-edited reviewed text.' }),
    )
  })

  it('disables confirm when the reviewed text is emptied', async () => {
    const wrapper = await mountView()
    await reachReview(wrapper)
    await wrapper.find('textarea.review-textarea').setValue('   ')
    expect(findButton(wrapper, 'Confirm & Start Synthesis')!.attributes('disabled')).toBeDefined()
  })

  it('displays job status after successful submission', async () => {
    const wrapper = await mountView()
    await reachReview(wrapper)
    await findButton(wrapper, 'Confirm & Start Synthesis')!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.progress-section').exists()).toBe(true)
    expect(wrapper.text()).toContain('queued')
  })

  it('shows submit error on synthesis API failure', async () => {
    mockCreateSynthesisJob.mockRejectedValueOnce(new Error('No model loaded'))
    const wrapper = await mountView()
    await reachReview(wrapper)
    await findButton(wrapper, 'Confirm & Start Synthesis')!.trigger('click')
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
    await reachReview(wrapper)
    await findButton(wrapper, 'Confirm & Start Synthesis')!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('need 20.5 MB')
    expect(wrapper.text()).toContain('have 1 MB')
  })
})

describe('CreateView — job progress via SSE', () => {
  async function startJob(wrapper: ReturnType<typeof mount>) {
    await reachReview(wrapper)
    await findButton(wrapper, 'Confirm & Start Synthesis')!.trigger('click')
    await flushPromises()
  }

  it('updates progress from SSE job-progress events', async () => {
    const wrapper = await mountView()
    await startJob(wrapper)

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
    await startJob(wrapper)

    for (const handler of sseHandlers['job-progress'] ?? []) {
      handler({ job_id: 'other-job', type: 'synthesis', status: 'processing', progress: 99 })
    }
    await flushPromises()

    expect(wrapper.text()).toContain('queued')
  })

  it('shows success message on job-completed SSE event', async () => {
    const wrapper = await mountView()
    await startJob(wrapper)

    for (const handler of sseHandlers['job-completed'] ?? []) {
      handler({ job_id: 'job-1', type: 'synthesis', audiobook_id: 'ab-1' })
    }
    await flushPromises()

    expect(wrapper.text()).toContain('completed')
    expect(wrapper.text()).toContain('Audiobook created successfully')
  })

  it('shows error message on job-failed SSE event', async () => {
    const wrapper = await mountView()
    await startJob(wrapper)

    for (const handler of sseHandlers['job-failed'] ?? []) {
      handler({ job_id: 'job-1', type: 'synthesis', error_message: 'Out of VRAM' })
    }
    await flushPromises()

    expect(wrapper.text()).toContain('failed')
    expect(wrapper.text()).toContain('Out of VRAM')
  })

  it('shows New Audiobook button after completion and resets the form', async () => {
    const wrapper = await mountView()
    await startJob(wrapper)

    expect(findButton(wrapper, 'New Audiobook')).toBeUndefined()

    for (const handler of sseHandlers['job-completed'] ?? []) {
      handler({ job_id: 'job-1', type: 'synthesis', audiobook_id: 'ab-1' })
    }
    await flushPromises()

    const newBtn = findButton(wrapper, 'New Audiobook')
    expect(newBtn).toBeDefined()

    await newBtn!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.progress-section').exists()).toBe(false)
    expect(wrapper.find('textarea.review-textarea').exists()).toBe(false)
    expect(wrapper.find('.file-name').exists()).toBe(false)
  })

  it('hides the confirm/start-over actions once a job is active', async () => {
    const wrapper = await mountView()
    await startJob(wrapper)
    expect(findButton(wrapper, 'Confirm & Start Synthesis')).toBeUndefined()
    expect(findButton(wrapper, 'Start Over')).toBeUndefined()
  })

  it('disables the file input while in review', async () => {
    const wrapper = await mountView()
    await reachReview(wrapper)
    expect(wrapper.find('input[type="file"]').attributes('disabled')).toBeDefined()
  })
})
