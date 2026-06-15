import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchPlaybackPosition, savePlaybackPosition } from '@/api/playback'

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

describe('fetchPlaybackPosition', () => {
  it('returns the two-level bookmark on success', async () => {
    const position = {
      last_chapter_number: 3,
      chapters: { '1': 120.5, '2': 300.0, '3': 45.2 },
    }
    globalThis.fetch = mockFetchResponse(200, position)
    const result = await fetchPlaybackPosition('ab-1')
    expect(result).toEqual(position)
    expect(fetch).toHaveBeenCalledWith('/api/v1/audiobooks/ab-1/position')
  })

  it('throws "Audiobook not found" on 404', async () => {
    globalThis.fetch = mockFetchResponse(404, {})
    await expect(fetchPlaybackPosition('missing')).rejects.toThrow('Audiobook not found')
  })

  it('throws a generic error on other failures', async () => {
    globalThis.fetch = mockFetchResponse(500, {})
    await expect(fetchPlaybackPosition('ab-1')).rejects.toThrow(
      'Failed to fetch playback position: 500',
    )
  })
})

describe('savePlaybackPosition', () => {
  it('PUTs the chapter number and position on success', async () => {
    globalThis.fetch = mockFetchResponse(200, { chapter_number: 2, position_seconds: 42 })
    await expect(savePlaybackPosition('ab-1', 2, 42)).resolves.toBeUndefined()
    expect(fetch).toHaveBeenCalledWith('/api/v1/audiobooks/ab-1/position', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chapter_number: 2, position_seconds: 42 }),
    })
  })

  it('throws on non-OK response', async () => {
    globalThis.fetch = mockFetchResponse(404, {})
    await expect(savePlaybackPosition('ab-1', 1, 0)).rejects.toThrow(
      'Failed to save playback position: 404',
    )
  })
})
