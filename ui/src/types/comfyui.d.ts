/** ComfyUI global type declarations */

interface ComfySettingManager {
  get(id: string): unknown
  set(id: string, value: unknown): void
}

interface ComfySidebarTab {
  id: string
  icon: string
  title: string
  tooltip: string
  type: 'custom'
  render: (el: HTMLElement) => void
}

interface ComfyExtensionManager {
  setting: ComfySettingManager
  registerSidebarTab(tab: ComfySidebarTab): void
}

interface ComfySettingDefinition {
  id: string
  name: string
  type: string
  defaultValue: unknown
  tooltip?: string
  attrs?: Record<string, unknown>
}

interface ComfyExtensionDefinition {
  name: string
  settings?: ComfySettingDefinition[]
}

interface ComfyApi {
  fetchApi(route: string, options?: RequestInit): Promise<Response>
}

interface ComfyApp {
  extensionManager: ComfyExtensionManager
  api: ComfyApi
  registerExtension(extension: ComfyExtensionDefinition): void
}

declare global {
  interface Window {
    app: ComfyApp
  }
}

export {}
