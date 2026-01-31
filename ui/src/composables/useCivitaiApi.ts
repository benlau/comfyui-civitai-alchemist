import type { Metadata, Resource, ResolveResponse } from '../types'

/**
 * Read the Civitai API key from ComfyUI Settings.
 */
export function getApiKey(): string {
  return (window.app.extensionManager.setting.get('civitai-alchemist.api_key') as string) || ''
}

/**
 * Parse a Civitai image ID from a URL or bare number string.
 * Returns the numeric ID string, or throws an error for invalid input.
 */
export function parseImageId(input: string): string {
  const trimmed = input.trim()
  if (/^\d+$/.test(trimmed)) {
    return trimmed
  }
  const match = trimmed.match(/civitai\.com\/images\/(\d+)/)
  if (match) {
    return match[1]
  }
  throw new Error('Invalid format. Enter a numeric image ID or a Civitai image URL.')
}

/**
 * Fetch image metadata from the backend.
 */
export async function fetchMetadata(imageId: string): Promise<Metadata> {
  const response = await window.app.api.fetchApi('/civitai/fetch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_id: imageId, api_key: getApiKey() }),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const message = data.error || `Request failed (${response.status})`
    throw new Error(message)
  }
  return response.json()
}

/**
 * Resolve model resources from metadata via the backend.
 */
export async function resolveModels(metadata: Metadata): Promise<ResolveResponse> {
  const response = await window.app.api.fetchApi('/civitai/resolve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ metadata, api_key: getApiKey() }),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    const message = data.error || `Request failed (${response.status})`
    throw new Error(message)
  }
  return response.json()
}

/**
 * Start a single model download in the background.
 * Returns the task_id for tracking progress via WebSocket.
 */
export async function downloadModel(resource: Resource): Promise<{ task_id: string }> {
  const response = await window.app.api.fetchApi('/civitai/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resource, api_key: getApiKey() }),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.error || `Download request failed (${response.status})`)
  }
  return response.json()
}

/**
 * Start a batch download for multiple missing models.
 * Only sends resolved, not-yet-downloaded resources.
 * Returns the task_id for the batch task.
 */
export async function downloadAllMissing(resources: Resource[]): Promise<{ task_id: string }> {
  const missing = resources.filter(r => r.resolved && !r.already_downloaded)
  const response = await window.app.api.fetchApi('/civitai/download-all', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resources: missing, api_key: getApiKey() }),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.error || `Batch download request failed (${response.status})`)
  }
  return response.json()
}

/**
 * Cancel a specific download task.
 */
export async function cancelDownload(taskId: string): Promise<void> {
  await window.app.api.fetchApi('/civitai/download-cancel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId }),
  })
}

/**
 * Cancel all active download tasks.
 */
export async function cancelAllDownloads(): Promise<void> {
  await window.app.api.fetchApi('/civitai/download-cancel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cancel_all: true }),
  })
}
