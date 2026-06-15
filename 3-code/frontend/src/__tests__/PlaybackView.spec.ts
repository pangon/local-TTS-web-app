import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import PlaybackView from '../views/PlaybackView.vue'
import type { AudiobookDetail } from '../api/audiobooks'
import type { PlaybackPosition } from '../api/playback'

const mockFetchAudiobook = vi.fn()
const mockFetchPosition = vi.fn()
const mockSavePosition = vi.fn()

vi.mock('@/api/audiobooks', () => ({
  fetchAudiobook: (...args: unknown[]) => mockFetchAudiobook(...args),
  chapterAudioUrl: (id: string, n: number) => `/api/v1/audiobooks/${id}/chapters/${n}/audio`,
}))

vi.mock('@/api/playback', () => ({
  fetchPlaybackPosition: (...args: unknown[]) => mockFetchPosition(...args),
  savePlaybackPosition: (...args: unknown[]) => mockSavePosition(...args),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'ab-1' } }),
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
}))

function makeDetail(chapterCount: number): AudiobookDetail {
  return {
    id: 'ab-1',
    title: 'My Book',
    source_filename: 'my-book.txt',
    model_id: 'hexgrad/Kokoro-82M',
    voice: 'if_sara',
    language: 'it',
    created_at: '2026-03-11T14:30:00Z',
    chapters: Array.from({ length: chapterCount }, (_, i) => ({
      chapter_number: i + 1,
      title: `Chapter ${i + 1}`,
      duration_seconds: 100,
      file_size_bytes: 2 * 1024 * 1024, // 2.0 MB
    })),
  }
}

function makePosition(overrides: Partial<PlaybackPosition> = {}): PlaybackPosition {
  return { last_chapter_number: 1, chapters: {}, ...overrides }
}

/** Replaces the element's currentTime with a writable tracked property. */
function trackCurrentTime(el: HTMLMediaElement, initial = 0) {
  let t = initial
  Object.defineProperty(el, 'currentTime', {
    configurable: true,
    get: () => t,
    set: (v: number) => {
      t = v
    },
  })
}

async function mountView() {
  const wrapper = mount(PlaybackView)
  await flushPromises()
  return wrapper
}

// Each PlaybackView registers global pagehide/visibilitychange listeners and
// may start a periodic-save interval; auto-unmount keeps tests isolated by
// running its onUnmounted cleanup (removing listeners and clearing the timer).
enableAutoUnmount(afterEach)

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchAudiobook.mockResolvedValue(makeDetail(3))
  mockFetchPosition.mockResolvedValue(makePosition())
  mockSavePosition.mockResolvedValue(undefined)
})

describe('PlaybackView', () => {
  it('renders the audiobook title and an audio player', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('h1').text()).toBe('My Book')
    expect(wrapper.find('audio.audio-player').exists()).toBe(true)
  })

  it('shows the TTS model used to generate the audiobook', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('.book-model').text()).toContain('hexgrad/Kokoro-82M')
  })

  it('shows each chapter file size on disk in the chapter list', async () => {
    const wrapper = await mountView()
    const sizes = wrapper.findAll('.chapter-list .chapter-size')
    expect(sizes).toHaveLength(3)
    expect(sizes[0]!.text()).toContain('2.0 MB')
  })

  it('shows an error message when loading fails', async () => {
    mockFetchAudiobook.mockRejectedValue(new Error('Audiobook not found'))
    const wrapper = await mountView()
    expect(wrapper.find('.error').text()).toContain('Audiobook not found')
    expect(wrapper.find('audio').exists()).toBe(false)
  })

  it('shows chapter navigation controls for multi-chapter audiobooks', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('.chapter-nav').exists()).toBe(true)
    expect(wrapper.find('.chapter-list').exists()).toBe(true)
  })

  it('hides chapter navigation controls for single-chapter audiobooks', async () => {
    mockFetchAudiobook.mockResolvedValue(makeDetail(1))
    const wrapper = await mountView()
    expect(wrapper.find('.chapter-nav').exists()).toBe(false)
    expect(wrapper.find('.chapter-list').exists()).toBe(false)
    // playback still works
    expect(wrapper.find('audio.audio-player').exists()).toBe(true)
  })

  it('starts from the first chapter when the audiobook has never been played', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('audio').attributes('src')).toBe(
      '/api/v1/audiobooks/ab-1/chapters/1/audio',
    )
  })

  it('resumes from the last active chapter at its saved position', async () => {
    mockFetchPosition.mockResolvedValue(
      makePosition({ last_chapter_number: 2, chapters: { '2': 50 } }),
    )
    const wrapper = await mountView()

    // Loads the last active chapter
    expect(wrapper.find('audio').attributes('src')).toBe(
      '/api/v1/audiobooks/ab-1/chapters/2/audio',
    )

    // Seeks to the saved position once metadata is available
    const audio = wrapper.find('audio').element as HTMLMediaElement
    trackCurrentTime(audio)
    await wrapper.find('audio').trigger('loadedmetadata')
    expect(audio.currentTime).toBe(50)
  })

  it('records the current chapter and timestamp when playback is paused', async () => {
    const wrapper = await mountView()
    const audio = wrapper.find('audio').element as HTMLMediaElement
    trackCurrentTime(audio)
    audio.currentTime = 33

    await wrapper.find('audio').trigger('pause')
    await flushPromises()

    expect(mockSavePosition).toHaveBeenCalledWith('ab-1', 1, 33, { keepalive: false })
  })

  it('resumes from the saved position when navigating to a previously listened chapter', async () => {
    mockFetchPosition.mockResolvedValue(
      makePosition({ last_chapter_number: 1, chapters: { '1': 10, '3': 77 } }),
    )
    const wrapper = await mountView()
    const audio = wrapper.find('audio').element as HTMLMediaElement
    trackCurrentTime(audio)
    audio.currentTime = 10

    // Navigate to chapter 3 (previously listened)
    const chapterButtons = wrapper.findAll('.chapter-link')
    await chapterButtons[2]!.trigger('click')
    await flushPromises()

    // Leaving chapter 1 is saved, and chapter 3 becomes the active bookmark
    expect(mockSavePosition).toHaveBeenCalledWith('ab-1', 1, 10, { keepalive: false })
    expect(mockSavePosition).toHaveBeenCalledWith('ab-1', 3, 77, { keepalive: false })

    // Audio switches to chapter 3 and seeks to its saved position
    expect(wrapper.find('audio').attributes('src')).toBe(
      '/api/v1/audiobooks/ab-1/chapters/3/audio',
    )
    await wrapper.find('audio').trigger('loadedmetadata')
    expect(audio.currentTime).toBe(77)
  })

  it('starts from the beginning when navigating to a never-listened chapter', async () => {
    mockFetchPosition.mockResolvedValue(
      makePosition({ last_chapter_number: 1, chapters: { '1': 10 } }),
    )
    const wrapper = await mountView()
    const audio = wrapper.find('audio').element as HTMLMediaElement
    trackCurrentTime(audio, 10)

    // Navigate to chapter 2 (never listened)
    await wrapper.findAll('.chapter-link')[1]!.trigger('click')
    await flushPromises()

    expect(mockSavePosition).toHaveBeenCalledWith('ab-1', 2, 0, { keepalive: false })

    // No seek beyond start when metadata loads
    audio.currentTime = 0
    await wrapper.find('audio').trigger('loadedmetadata')
    expect(audio.currentTime).toBe(0)
  })

  it('disables previous on the first chapter and next on the last chapter', async () => {
    const wrapper = await mountView()
    const navButtons = wrapper.find('.chapter-nav').findAll('button')
    const [prev, next] = navButtons

    // On chapter 1: previous disabled, next enabled
    expect(prev!.attributes('disabled')).toBeDefined()
    expect(next!.attributes('disabled')).toBeUndefined()

    // Move to last chapter
    await wrapper.findAll('.chapter-link')[2]!.trigger('click')
    await flushPromises()

    const navButtonsAfter = wrapper.find('.chapter-nav').findAll('button')
    expect(navButtonsAfter[0]!.attributes('disabled')).toBeUndefined()
    expect(navButtonsAfter[1]!.attributes('disabled')).toBeDefined()
  })

  it('saves the position every 20 seconds while playing', async () => {
    vi.useFakeTimers()
    try {
      const wrapper = mount(PlaybackView)
      await flushPromises()
      const audio = wrapper.find('audio').element as HTMLMediaElement
      trackCurrentTime(audio)

      await wrapper.find('audio').trigger('play')
      mockSavePosition.mockClear()

      audio.currentTime = 20
      vi.advanceTimersByTime(20000)
      await flushPromises()
      expect(mockSavePosition).toHaveBeenCalledWith('ab-1', 1, 20, { keepalive: false })

      audio.currentTime = 35
      vi.advanceTimersByTime(20000)
      await flushPromises()
      expect(mockSavePosition).toHaveBeenCalledWith('ab-1', 1, 35, { keepalive: false })
      expect(mockSavePosition).toHaveBeenCalledTimes(2)
    } finally {
      vi.useRealTimers()
    }
  })

  it('stops periodic saving once playback is paused', async () => {
    vi.useFakeTimers()
    try {
      const wrapper = mount(PlaybackView)
      await flushPromises()
      const audio = wrapper.find('audio').element as HTMLMediaElement
      trackCurrentTime(audio)

      await wrapper.find('audio').trigger('play')
      await wrapper.find('audio').trigger('pause')
      mockSavePosition.mockClear()

      // Well past one 20s interval: no save should fire once stopped.
      vi.advanceTimersByTime(60000)
      await flushPromises()
      expect(mockSavePosition).not.toHaveBeenCalled()
    } finally {
      vi.useRealTimers()
    }
  })

  it('saves the position with keepalive on page navigation/reload/close', async () => {
    const wrapper = await mountView()
    const audio = wrapper.find('audio').element as HTMLMediaElement
    trackCurrentTime(audio)
    audio.currentTime = 42
    mockSavePosition.mockClear()

    window.dispatchEvent(new Event('pagehide'))
    await flushPromises()

    expect(mockSavePosition).toHaveBeenCalledWith('ab-1', 1, 42, { keepalive: true })
  })

  it('saves the position with keepalive when the tab becomes hidden', async () => {
    const original = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState')
    const wrapper = await mountView()
    const audio = wrapper.find('audio').element as HTMLMediaElement
    trackCurrentTime(audio)
    audio.currentTime = 7
    mockSavePosition.mockClear()

    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => 'hidden',
    })
    try {
      document.dispatchEvent(new Event('visibilitychange'))
      await flushPromises()
      expect(mockSavePosition).toHaveBeenCalledWith('ab-1', 1, 7, { keepalive: true })
    } finally {
      if (original) Object.defineProperty(document, 'visibilityState', original)
    }
  })
})
