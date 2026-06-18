import { describe, it, expect, vi, beforeEach } from 'vitest'
import { preprocessFile } from '@/api/preprocess'

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

describe('preprocessFile', () => {
  const file = new File(['Raw text 25%.'], 'book.txt', { type: 'text/plain' })

  it('returns normalized text on 200 and posts multipart with the file', async () => {
    const body = {
      normalized_text: 'Raw text venticinque per cento.',
      language: 'it',
      model_id: 'kokoro',
      original_char_count: 13,
      normalized_char_count: 31,
    }
    globalThis.fetch = mockFetchResponse(200, body)

    const result = await preprocessFile(file)
    expect(result).toEqual(body)

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]!
    expect(call[0]).toBe('/api/v1/preprocess')
    expect(call[1].method).toBe('POST')
    const form = call[1].body as FormData
    expect(form.get('file')).toBe(file)
    expect(form.has('language')).toBe(false)
  })

  it('sends language when provided', async () => {
    globalThis.fetch = mockFetchResponse(200, {
      normalized_text: 'x',
      language: 'it',
      model_id: 'kokoro',
      original_char_count: 1,
      normalized_char_count: 1,
    })

    await preprocessFile(file, 'it')

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]!
    const form = call[1].body as FormData
    expect(form.get('language')).toBe('it')
  })

  it('throws with message on 400 (validation)', async () => {
    globalThis.fetch = mockFetchResponse(400, {
      detail: 'Invalid file type: only .txt files are accepted',
    })
    await expect(preprocessFile(file)).rejects.toThrow(
      'Invalid file type: only .txt files are accepted',
    )
  })

  it('throws on 409 (no model loaded)', async () => {
    globalThis.fetch = mockFetchResponse(409, { detail: 'No model loaded' })
    await expect(preprocessFile(file)).rejects.toThrow('No model loaded')
  })

  it('throws on unexpected error status', async () => {
    globalThis.fetch = mockFetchResponse(500, {})
    await expect(preprocessFile(file)).rejects.toThrow('Failed to preprocess text: 500')
  })
})
