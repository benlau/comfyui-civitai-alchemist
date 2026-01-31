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
  addEventListener(type: string, callback: (event: CustomEvent) => void): void
  removeEventListener(type: string, callback: (event: CustomEvent) => void): void
}

interface LGraphNode {
  computeSize(): [number, number]
  setSize(size: [number, number]): void
  size: [number, number]
}

interface LGraph {
  _nodes: LGraphNode[]
  arrange(margin?: number): void
}

interface ComfyApp {
  extensionManager: ComfyExtensionManager
  api: ComfyApi
  graph: LGraph
  registerExtension(extension: ComfyExtensionDefinition): void
  loadApiJson(apiData: Record<string, unknown>, fileName?: string): Promise<void>
}

declare global {
  interface Window {
    app: ComfyApp
  }
}

export {}
