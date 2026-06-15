import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchAudiobooks, deleteAudiobook } from '@/api/audiobooks'

function mockFetchResponse(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('fetchAudiobooks', () => {
  it('returns the audiobook list on success', async () => {
    const books = [
      {
        id: 'ab-1',
        title: 'My Book',
        source_filename: 'my-book.txt',
        model_id: 'hexgrad/Kokoro-82M',
        voice: 'if_sara',
        language: 'it',
        created_at: '2026-03-11T14:30:00Z',
        chapter_count: 5,
      },
    ]
    globalThis.fetch = mockFetchResponse(200, books)
    const result = await fetchAudiobooks()
    expect(result).toEqual(books)
    expect(fetch).toHaveBeenCalledWith('/api/v1/audiobooks')
  })

  it('throws on non-OK response', async () => {
    globalThis.fetch = mockFetchResponse(500, {})
    await expect(fetchAudiobooks()).rejects.toThrow('Failed to fetch audiobooks: 500')
  })
})

describe('deleteAudiobook', () => {
  it('resolves on 204', async () => {
    globalThis.fetch = mockFetchResponse(204, null)
    await expect(deleteAudiobook('ab-1')).resolves.toBeUndefined()
    expect(fetch).toHaveBeenCalledWith('/api/v1/audiobooks/ab-1', { method: 'DELETE' })
  })

  it('throws "Audiobook not found" on 404', async () => {
    globalThis.fetch = mockFetchResponse(404, {})
    await expect(deleteAudiobook('missing')).rejects.toThrow('Audiobook not found')
  })

  it('throws a generic error on other failures', async () => {
    globalThis.fetch = mockFetchResponse(500, {})
    await expect(deleteAudiobook('ab-1')).rejects.toThrow('Failed to delete audiobook: 500')
  })
})
