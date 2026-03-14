import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from '../App.vue'

const routes = [
  { path: '/', name: 'library', component: { template: '<div>Library</div>' } },
  { path: '/create', name: 'create', component: { template: '<div>Create</div>' } },
  { path: '/models', name: 'models', component: { template: '<div>Models</div>' } },
  { path: '/preview', name: 'preview', component: { template: '<div>Preview</div>' } },
  { path: '/monitoring', name: 'monitoring', component: { template: '<div>Monitoring</div>' } },
]

async function mountApp(initialRoute = '/') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes,
  })
  router.push(initialRoute)
  await router.isReady()
  return mount(App, {
    global: { plugins: [router] },
  })
}

describe('App', () => {
  it('renders navigation links', async () => {
    const wrapper = await mountApp()
    const nav = wrapper.find('nav')
    expect(nav.exists()).toBe(true)

    const links = nav.findAll('a')
    expect(links.length).toBe(5)

    const hrefs = links.map((l) => l.attributes('href'))
    expect(hrefs).toContain('/')
    expect(hrefs).toContain('/create')
    expect(hrefs).toContain('/models')
    expect(hrefs).toContain('/preview')
    expect(hrefs).toContain('/monitoring')
  })

  it('renders router-view content for the default route', async () => {
    const wrapper = await mountApp('/')
    expect(wrapper.find('main').text()).toContain('Library')
  })

  it('renders router-view content when navigating to /create', async () => {
    const wrapper = await mountApp('/create')
    expect(wrapper.find('main').text()).toContain('Create')
  })
})
