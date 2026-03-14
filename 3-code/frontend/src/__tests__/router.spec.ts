import { describe, it, expect } from 'vitest'
import router from '../router'

describe('Router', () => {
  it('defines all expected routes', () => {
    const routeNames = router.getRoutes().map((r) => r.name)
    expect(routeNames).toContain('library')
    expect(routeNames).toContain('create')
    expect(routeNames).toContain('playback')
    expect(routeNames).toContain('models')
    expect(routeNames).toContain('preview')
    expect(routeNames).toContain('monitoring')
  })

  it('maps library route to /', () => {
    const route = router.getRoutes().find((r) => r.name === 'library')
    expect(route?.path).toBe('/')
  })

  it('maps playback route with id parameter', () => {
    const route = router.getRoutes().find((r) => r.name === 'playback')
    expect(route?.path).toBe('/playback/:id')
  })

  it('has 6 routes total', () => {
    expect(router.getRoutes()).toHaveLength(6)
  })
})
