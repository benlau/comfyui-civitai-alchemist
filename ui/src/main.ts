import { createApp, type App as VueApp } from 'vue'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import App from './App.vue'

let vueApp: VueApp | null = null

async function init() {
  // Wait for ComfyUI app to be available
  while (!window.app?.extensionManager) {
    await new Promise(r => setTimeout(r, 50))
  }

  // Register Settings (API Key field)
  window.app.registerExtension({
    name: 'civitai-alchemist',
    settings: [{
      id: 'civitai-alchemist.api_key',
      name: 'Civitai API Key',
      type: 'text',
      defaultValue: '',
      tooltip: 'Generate at https://civitai.com/user/account',
      attrs: {
        type: 'password',
        placeholder: 'sk_...'
      }
    }]
  })

  // Register Sidebar Tab
  window.app.extensionManager.registerSidebarTab({
    id: 'civitai-alchemist',
    icon: 'pi pi-bolt',
    title: 'Civitai Alchemist',
    tooltip: 'Reproduce Civitai images',
    type: 'custom',
    render: (el: HTMLElement) => {
      // Prevent duplicate Vue app instances when render is called multiple times
      if (vueApp) {
        vueApp.unmount()
        vueApp = null
      }
      el.innerHTML = ''

      const container = document.createElement('div')
      el.appendChild(container)
      vueApp = createApp(App)
      vueApp.use(PrimeVue, {
        theme: {
          preset: Aura,
          options: {
            darkModeSelector: '.dark-theme, :root.dark-theme'
          }
        }
      })
      vueApp.mount(container)
    }
  })
}

void init()
