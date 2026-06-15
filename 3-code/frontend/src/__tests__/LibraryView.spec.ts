import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LibraryView from '../views/LibraryView.vue'
import type { AudiobookSummary } from '../api/audiobooks'

const mockFetchAudiobooks = vi.fn()
const mockDeleteAudiobook = vi.fn()

vi.mock('@/api/audiobooks', () => ({
  fetchAudiobooks: (...args: unknown[]) => mockFetchAudiobooks(...args),
  deleteAudiobook: (...args: unknown[]) => mockDeleteAudiobook(...args),
}))

const RouterLinkStub = {
  props: ['to'],
  template: '<a><slot /></a>',
}

function makeBook(overrides: Partial<AudiobookSummary> = {}): AudiobookSummary {
  return {
    id: 'ab-1',
    title: 'My Book',
    source_filename: 'my-book.txt',
    model_id: 'hexgrad/Kokoro-82M',
    voice: 'if_sara',
    language: 'it',
    created_at: '2026-03-11T14:30:00Z',
    chapter_count: 5,
    ...overrides,
  }
}

async function mountView() {
  const wrapper = mount(LibraryView, {
    global: { stubs: { RouterLink: RouterLinkStub } },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  mockFetchAudiobooks.mockResolvedValue([])
  mockDeleteAudiobook.mockResolvedValue(undefined)
})

describe('LibraryView', () => {
  it('renders the heading', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('h1').text()).toBe('Library')
  })

  it('shows an empty state message when no audiobooks exist', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.find('.audiobook-list').exists()).toBe(false)
  })

  it('lists all audiobooks with title, date, and chapter count', async () => {
    mockFetchAudiobooks.mockResolvedValue([
      makeBook({ id: 'ab-1', title: 'Book One', chapter_count: 3 }),
      makeBook({ id: 'ab-2', title: 'Book Two', chapter_count: 1 }),
    ])
    const wrapper = await mountView()

    const items = wrapper.findAll('.audiobook-item')
    expect(items).toHaveLength(2)
    expect(wrapper.text()).toContain('Book One')
    expect(wrapper.text()).toContain('Book Two')
    // chapter count, with singular/plural handling
    expect(wrapper.text()).toContain('3 chapters')
    expect(wrapper.text()).toContain('1 chapter')
    // creation date is rendered (formatted)
    expect(items[0]!.find('.book-meta').text()).not.toBe('')
  })

  it('links each audiobook to its playback view', async () => {
    mockFetchAudiobooks.mockResolvedValue([makeBook({ id: 'ab-42' })])
    const wrapper = await mountView()

    const link = wrapper.findComponent(RouterLinkStub)
    expect(link.props('to')).toEqual({ name: 'playback', params: { id: 'ab-42' } })
  })

  it('shows an error message when loading fails', async () => {
    mockFetchAudiobooks.mockRejectedValue(new Error('Network down'))
    const wrapper = await mountView()
    expect(wrapper.find('.error').text()).toContain('Network down')
  })

  it('does not delete immediately; shows a confirmation prompt first', async () => {
    mockFetchAudiobooks.mockResolvedValue([makeBook()])
    const wrapper = await mountView()

    await wrapper.find('.btn-secondary').trigger('click')
    await flushPromises()

    expect(wrapper.find('.confirm-text').exists()).toBe(true)
    expect(mockDeleteAudiobook).not.toHaveBeenCalled()
    // audiobook still present
    expect(wrapper.findAll('.audiobook-item')).toHaveLength(1)
  })

  it('removes the audiobook when deletion is confirmed', async () => {
    mockFetchAudiobooks.mockResolvedValue([makeBook({ id: 'ab-1' })])
    const wrapper = await mountView()

    await wrapper.find('.btn-secondary').trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((b) => b.text() === 'Confirm')!.trigger('click')
    await flushPromises()

    expect(mockDeleteAudiobook).toHaveBeenCalledWith('ab-1')
    expect(wrapper.findAll('.audiobook-item')).toHaveLength(0)
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })

  it('leaves the audiobook unchanged when deletion is cancelled', async () => {
    mockFetchAudiobooks.mockResolvedValue([makeBook({ id: 'ab-1' })])
    const wrapper = await mountView()

    await wrapper.find('.btn-secondary').trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((b) => b.text() === 'Cancel')!.trigger('click')
    await flushPromises()

    expect(mockDeleteAudiobook).not.toHaveBeenCalled()
    expect(wrapper.findAll('.audiobook-item')).toHaveLength(1)
    expect(wrapper.find('.confirm-text').exists()).toBe(false)
  })

  it('shows an error when deletion fails and keeps the audiobook', async () => {
    mockFetchAudiobooks.mockResolvedValue([makeBook({ id: 'ab-1' })])
    mockDeleteAudiobook.mockRejectedValue(new Error('Audiobook not found'))
    const wrapper = await mountView()

    await wrapper.find('.btn-secondary').trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((b) => b.text() === 'Confirm')!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.error').text()).toContain('Audiobook not found')
    expect(wrapper.findAll('.audiobook-item')).toHaveLength(1)
  })
})
