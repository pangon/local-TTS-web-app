// @vitest-environment node
import { describe, it, expect } from 'vitest'
import config from '../../vite.config'

describe('Vite dev server proxy', () => {
  const serverConfig = (config as Record<string, unknown>).server as Record<string, unknown>
  const proxy = serverConfig?.proxy as Record<string, unknown>

  it('proxies /api requests to the FastAPI backend', () => {
    expect(proxy).toBeDefined()
    expect(proxy['/api']).toBeDefined()
  })

  it('targets 127.0.0.1:8000', () => {
    const apiProxy = proxy['/api'] as Record<string, unknown>
    expect(apiProxy.target).toBe('http://127.0.0.1:8000')
  })

  it('enables changeOrigin', () => {
    const apiProxy = proxy['/api'] as Record<string, unknown>
    expect(apiProxy.changeOrigin).toBe(true)
  })
})
