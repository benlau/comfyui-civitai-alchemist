<template>
  <div class="comfy-vue-side-bar-container flex h-full flex-col">
    <!-- Header: title row -->
    <div class="comfy-vue-side-bar-header flex flex-col gap-2">
      <div class="flex min-h-8 items-center px-2 2xl:px-4 pt-3 pb-1">
        <span class="truncate font-bold">Civitai Alchemist</span>
      </div>
      <!-- Input area -->
      <div class="px-2 2xl:px-4 pb-2">
        <ApiKeyWarning v-if="!apiKeySet" />
        <ImageInput
          :disabled="!apiKeySet"
          :loading="loading"
          @submit="handleSubmit"
        />
      </div>
    </div>

    <!-- Body: scrollable content area -->
    <div class="comfy-vue-side-bar-body flex-1 overflow-y-auto overflow-x-hidden px-2 2xl:px-4">
      <!-- Loading state -->
      <div v-if="loading" class="status-box loading-box">
        <div class="spinner"></div>
        <span>{{ loadingStep }}</span>
      </div>

      <!-- Error state -->
      <div v-if="error" class="status-box error-box">
        <span>{{ error }}</span>
      </div>

      <!-- Results: image preview + generation info + model list -->
      <template v-if="!loading && !error && metadata">
        <!-- Image preview -->
        <div v-if="metadata.image_url" class="image-preview">
          <img :src="metadata.image_url" alt="Civitai image preview" />
        </div>

        <GenerationInfo :metadata="metadata" />
        <ModelList
          v-if="resources.length > 0"
          :resources="resources"
          :batch-downloading="batchDownloading"
          :batch-progress="batchProgress"
          :batch-total="batchTotal"
          :generating-workflow="generatingWorkflow"
          :workflow-result="workflowResult"
          @download="handleDownload"
          @cancel="handleCancel"
          @retry="handleDownload"
          @download-all="handleDownloadAll"
          @cancel-all="handleCancelAll"
          @generate-workflow="handleGenerateWorkflow"
        />

        <!-- Missing models warning dialog -->
        <div v-if="showMissingWarning" class="warning-dialog">
          <div class="warning-header">Missing models:</div>
          <ul class="warning-list">
            <li v-for="m in missingModels" :key="m.name">{{ m.name }} ({{ m.type }})</li>
          </ul>
          <p class="warning-note">
            Workflow will be generated with original filenames. You can replace them on canvas.
          </p>
          <div class="warning-actions">
            <button class="warning-btn warning-cancel-btn" @click="handleWarningCancel">Cancel</button>
            <button class="warning-btn warning-continue-btn" @click="handleWarningContinue">Continue</button>
          </div>
        </div>
      </template>

      <!-- Empty state hint -->
      <p v-if="!loading && !error && !metadata && apiKeySet" class="hint-text">
        Paste a Civitai image ID or URL to get started.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import type { Metadata, Resource } from './types'
import {
  getApiKey, parseImageId, fetchMetadata, resolveModels,
  downloadModel, downloadAllMissing, cancelDownload, cancelAllDownloads,
  generateWorkflow,
} from './composables/useCivitaiApi'
import ApiKeyWarning from './components/ApiKeyWarning.vue'
import ImageInput from './components/ImageInput.vue'
import GenerationInfo from './components/GenerationInfo.vue'
import ModelList from './components/ModelList.vue'

const apiKeySet = ref(false)
const loading = ref(false)
const loadingStep = ref('')
const error = ref('')
const metadata = ref<Metadata | null>(null)
const resources = ref<Resource[]>([])

// Download state tracking
const batchDownloading = ref(false)
const batchTaskId = ref<string | null>(null)
const batchProgress = ref(0) // current index (1-based) in batch
const batchTotal = ref(0)    // total count of resources in batch

// Workflow generation state
const generatingWorkflow = ref(false)
const workflowResult = ref<{ type: string; nodeCount: number } | null>(null)
const showMissingWarning = ref(false)
const missingModels = ref<{ name: string; type: string }[]>([])

/**
 * Find a resource by filename match.
 * The backend sends filename in progress events; match against resource list.
 */
function findResourceByFilename(filename: string): Resource | undefined {
  return resources.value.find(r => r.filename === filename)
}

/**
 * Handle WebSocket progress events from the backend.
 */
function onDownloadProgress(event: CustomEvent) {
  const { task_id, filename, status, progress, downloaded_bytes, total_bytes, error: errorMsg } = event.detail

  const resource = findResourceByFilename(filename)
  if (!resource) return

  resource.taskId = task_id

  switch (status) {
    case 'downloading':
      resource.downloadStatus = 'downloading'
      resource.downloadProgress = progress ?? 0
      resource.downloadedBytes = downloaded_bytes
      resource.totalBytes = total_bytes
      resource.downloadError = undefined
      break
    case 'verifying':
      resource.downloadStatus = 'verifying'
      resource.downloadedBytes = downloaded_bytes
      resource.totalBytes = total_bytes
      break
    case 'completed':
      resource.downloadStatus = undefined
      resource.downloadProgress = undefined
      resource.downloadedBytes = undefined
      resource.totalBytes = undefined
      resource.downloadError = undefined
      resource.taskId = undefined
      resource.already_downloaded = true
      // Update batch progress counter
      if (batchDownloading.value && task_id === batchTaskId.value) {
        batchProgress.value++
      }
      break
    case 'failed':
      resource.downloadStatus = 'failed'
      resource.downloadError = errorMsg || 'Download failed'
      resource.downloadProgress = undefined
      resource.downloadedBytes = undefined
      resource.totalBytes = undefined
      // For batch: advance counter and let next resource start
      if (batchDownloading.value && task_id === batchTaskId.value) {
        batchProgress.value++
      }
      break
    case 'cancelled':
      resource.downloadStatus = 'cancelled'
      resource.downloadProgress = undefined
      resource.downloadedBytes = undefined
      resource.totalBytes = undefined
      resource.downloadError = undefined
      break
  }

  // Check if batch is done (all resources processed)
  if (batchDownloading.value && task_id === batchTaskId.value) {
    const batchResources = resources.value.filter(r =>
      r.downloadStatus === 'downloading' || r.downloadStatus === 'verifying' || r.downloadStatus === 'waiting'
    )
    if (batchResources.length === 0) {
      batchDownloading.value = false
      batchTaskId.value = null
    }
  }
}

function checkApiKey() {
  apiKeySet.value = !!getApiKey()
}

onMounted(() => {
  checkApiKey()
  // Re-check API key periodically in case user sets it via Settings
  setInterval(checkApiKey, 2000)
  // Listen for download progress events
  window.app.api.addEventListener('civitai.download.progress', onDownloadProgress)
})

onUnmounted(() => {
  window.app.api.removeEventListener('civitai.download.progress', onDownloadProgress)
})

async function handleSubmit(input: string) {
  error.value = ''
  metadata.value = null
  resources.value = []
  workflowResult.value = null
  showMissingWarning.value = false

  // Validate input format on the client side first
  let imageId: string
  try {
    imageId = parseImageId(input)
  } catch (e: unknown) {
    error.value = (e as Error).message
    return
  }

  loading.value = true

  try {
    // Step 1: Fetch metadata
    loadingStep.value = 'Fetching metadata...'
    const meta = await fetchMetadata(imageId)
    metadata.value = meta

    // Step 2: Resolve models
    loadingStep.value = 'Resolving models...'
    const resolved = await resolveModels(meta)
    resources.value = resolved.resources
  } catch (e: unknown) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
    loadingStep.value = ''
  }
}

async function handleDownload(resource: Resource) {
  resource.downloadStatus = 'downloading'
  resource.downloadProgress = 0
  resource.downloadError = undefined
  try {
    const { task_id } = await downloadModel(resource)
    resource.taskId = task_id
  } catch (e: unknown) {
    resource.downloadStatus = 'failed'
    resource.downloadError = (e as Error).message
  }
}

async function handleDownloadAll() {
  const missing = resources.value.filter(r => r.resolved && !r.already_downloaded)
  if (missing.length === 0) return

  // Mark all missing as waiting
  for (const r of missing) {
    r.downloadStatus = 'waiting'
    r.downloadError = undefined
  }

  batchDownloading.value = true
  batchProgress.value = 0
  batchTotal.value = missing.length

  try {
    const { task_id } = await downloadAllMissing(resources.value)
    batchTaskId.value = task_id
    // Set taskId on all batch resources for tracking
    for (const r of missing) {
      r.taskId = task_id
    }
  } catch (e: unknown) {
    // Reset all waiting resources on API error
    for (const r of missing) {
      r.downloadStatus = undefined
      r.downloadError = undefined
    }
    batchDownloading.value = false
    batchTaskId.value = null
    error.value = (e as Error).message
  }
}

async function handleCancel(resource: Resource) {
  if (resource.taskId) {
    try {
      await cancelDownload(resource.taskId)
    } catch {
      // Cancel is best-effort; the WebSocket event will update status
    }
  }
}

async function handleCancelAll() {
  try {
    await cancelAllDownloads()
  } catch {
    // Cancel is best-effort
  }
}

function handleGenerateWorkflow() {
  // Check for missing models
  const missing = resources.value.filter(r => !r.already_downloaded)
  if (missing.length > 0) {
    missingModels.value = missing.map(r => ({ name: r.name, type: r.type }))
    showMissingWarning.value = true
    return
  }
  doGenerateWorkflow()
}

function handleWarningCancel() {
  showMissingWarning.value = false
  missingModels.value = []
}

function handleWarningContinue() {
  showMissingWarning.value = false
  missingModels.value = []
  doGenerateWorkflow()
}

async function doGenerateWorkflow() {
  if (!metadata.value) return
  generatingWorkflow.value = true
  workflowResult.value = null
  error.value = ''

  try {
    const result = await generateWorkflow(metadata.value, resources.value)
    const filename = `civitai_${metadata.value.image_id || 'workflow'}.json`
    await window.app.loadApiJson(result.workflow, filename)

    // Fix: loadApiJson's arrange() uses default sizes. Recompute and re-arrange.
    for (const node of window.app.graph._nodes) {
      const size = node.computeSize()
      node.setSize(size)
    }
    window.app.graph.arrange()

    workflowResult.value = {
      type: result.workflow_type,
      nodeCount: result.node_count,
    }
  } catch (e: unknown) {
    error.value = (e as Error).message
  } finally {
    generatingWorkflow.value = false
  }
}
</script>

<style scoped>
.image-preview {
  margin-bottom: 12px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  max-height: 180px;
  background: var(--comfy-input-bg);
}

.image-preview img {
  display: block;
  width: 100%;
  height: 100%;
  max-height: 180px;
  object-fit: contain;
}

.hint-text {
  color: var(--descrip-text);
  font-size: 12px;
  margin: 0;
  line-height: 1.4;
}

.status-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 12px;
}

.loading-box {
  background: var(--comfy-input-bg);
  border: 1px solid var(--border-color);
  color: var(--descrip-text);
}

.error-box {
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid var(--error-text);
  color: var(--error-text);
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-color);
  border-top-color: var(--p-primary-500);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.warning-dialog {
  margin-top: 12px;
  padding: 12px;
  border-radius: 6px;
  background: var(--comfy-input-bg);
  border: 1px solid var(--border-color);
  font-size: 12px;
}

.warning-header {
  font-weight: 600;
  color: var(--fg-color);
  margin-bottom: 6px;
}

.warning-list {
  margin: 0 0 8px 0;
  padding-left: 18px;
  color: var(--error-text);
}

.warning-list li {
  margin-bottom: 2px;
}

.warning-note {
  color: var(--descrip-text);
  margin: 0 0 10px 0;
  line-height: 1.4;
}

.warning-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.warning-btn {
  padding: 4px 14px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--comfy-input-bg);
  color: var(--fg-color);
  transition: background 0.15s;
}

.warning-btn:hover {
  background: var(--border-color);
}

.warning-continue-btn {
  color: var(--p-primary-500);
  border-color: var(--p-primary-500);
}

.warning-continue-btn:hover {
  background: rgba(var(--p-primary-500-rgb, 59, 130, 246), 0.15);
}
</style>
