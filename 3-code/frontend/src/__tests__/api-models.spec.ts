import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchModels, downloadModel, loadModel } from '@/api/models'

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

describe('fetchModels', () => {
  it('returns model list on success', async () => {
    const models = [{ model_id: 'a', name: 'A', is_cached: true, is_loaded: false }]
    globalThis.fetch = mockFetchResponse(200, models)
    const result = await fetchModels()
    expect(result).toEqual(models)
    expect(fetch).toHaveBeenCalledWith('/api/v1/models')
  })

  it('throws on non-OK response', async () => {
    globalThis.fetch = mockFetchResponse(500, {})
    await expect(fetchModels()).rejects.toThrow('Failed to fetch models: 500')
  })
})

describe('downloadModel', () => {
  it('returns download response on 202', async () => {
    const body = { model_id: 'a', status: 'downloading' }
    globalThis.fetch = mockFetchResponse(202, body)
    const result = await downloadModel('a')
    expect(result).toEqual(body)
  })

  it('throws with disk space details on 409 with object detail', async () => {
    globalThis.fetch = mockFetchResponse(409, {
      detail: { detail: 'Insufficient disk space', estimated_mb: 2048, available_mb: 500 },
    })
    try {
      await downloadModel('a')
      expect.fail('should have thrown')
    } catch (e) {
      const err = e as Error & { estimated_mb?: number; available_mb?: number }
      expect(err.message).toBe('Insufficient disk space')
      expect(err.estimated_mb).toBe(2048)
      expect(err.available_mb).toBe(500)
    }
  })

  it('throws with string detail on 409 with string detail', async () => {
    globalThis.fetch = mockFetchResponse(409, { detail: 'Model already cached' })
    await expect(downloadModel('a')).rejects.toThrow('Model already cached')
  })
})

describe('loadModel', () => {
  it('returns load response on 200', async () => {
    const body = { model_id: 'a', status: 'loaded' }
    globalThis.fetch = mockFetchResponse(200, body)
    const result = await loadModel('a')
    expect(result).toEqual(body)
  })

  it('throws on 404', async () => {
    globalThis.fetch = mockFetchResponse(404, {})
    await expect(loadModel('a')).rejects.toThrow('Model not cached')
  })

  it('throws with VRAM details on 409 with object detail', async () => {
    globalThis.fetch = mockFetchResponse(409, {
      detail: { detail: 'Insufficient VRAM', required_mb: 4096, available_mb: 2048 },
    })
    try {
      await loadModel('a')
      expect.fail('should have thrown')
    } catch (e) {
      const err = e as Error & { required_mb?: number; available_mb?: number }
      expect(err.message).toBe('Insufficient VRAM')
      expect(err.required_mb).toBe(4096)
      expect(err.available_mb).toBe(2048)
    }
  })
})
