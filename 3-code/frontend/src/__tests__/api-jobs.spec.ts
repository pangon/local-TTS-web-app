import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createSynthesisJob } from '@/api/jobs'

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

describe('createSynthesisJob', () => {
  const file = new File(['Hello world'], 'test.txt', { type: 'text/plain' })

  it('returns job response on 201', async () => {
    const body = {
      id: 'abc-123',
      type: 'synthesis',
      status: 'queued',
      progress: 0,
      created_at: '2026-04-12T10:00:00Z',
    }
    globalThis.fetch = mockFetchResponse(201, body)

    const result = await createSynthesisJob(file)
    expect(result).toEqual(body)

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]!
    expect(call[0]).toBe('/api/v1/jobs/synthesis')
    expect(call[1].method).toBe('POST')
    expect(call[1].body).toBeInstanceOf(FormData)
  })

  it('sends voice and language when provided', async () => {
    globalThis.fetch = mockFetchResponse(201, { id: 'x', type: 'synthesis', status: 'queued', progress: 0, created_at: '' })

    await createSynthesisJob(file, 'if_sara', 'it')

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]!
    const form = call[1].body as FormData
    expect(form.get('voice')).toBe('if_sara')
    expect(form.get('language')).toBe('it')
  })

  it('does not send voice/language when omitted', async () => {
    globalThis.fetch = mockFetchResponse(201, { id: 'x', type: 'synthesis', status: 'queued', progress: 0, created_at: '' })

    await createSynthesisJob(file)

    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]!
    const form = call[1].body as FormData
    expect(form.has('voice')).toBe(false)
    expect(form.has('language')).toBe(false)
  })

  it('throws with message on 400 (string detail)', async () => {
    globalThis.fetch = mockFetchResponse(400, { detail: 'Invalid file type: only .txt files are accepted' })
    await expect(createSynthesisJob(file)).rejects.toThrow('Invalid file type: only .txt files are accepted')
  })

  it('throws on 409 with string detail (no model loaded)', async () => {
    globalThis.fetch = mockFetchResponse(409, { detail: 'No model loaded' })
    await expect(createSynthesisJob(file)).rejects.toThrow('No model loaded')
  })

  it('throws with disk space details on 409 with object detail', async () => {
    globalThis.fetch = mockFetchResponse(409, {
      detail: { detail: 'Insufficient disk space', estimated_mb: 20.5, available_mb: 1.0 },
    })
    try {
      await createSynthesisJob(file)
      expect.fail('should have thrown')
    } catch (e) {
      const err = e as Error & { estimated_mb?: number; available_mb?: number }
      expect(err.message).toBe('Insufficient disk space')
      expect(err.estimated_mb).toBe(20.5)
      expect(err.available_mb).toBe(1.0)
    }
  })

  it('throws on unexpected error status', async () => {
    globalThis.fetch = mockFetchResponse(500, {})
    await expect(createSynthesisJob(file)).rejects.toThrow('Failed to create synthesis job: 500')
  })
})
