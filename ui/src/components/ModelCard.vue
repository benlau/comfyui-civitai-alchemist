<template>
  <div class="model-card" :class="cardClass">
    <div class="card-header">
      <span class="model-status">{{ statusIcon }}</span>
      <span class="model-name" :title="displayName">{{ displayName }}</span>
      <span class="model-meta">
        <span class="model-type-tag">{{ resource.type }}</span>
        <template v-if="formattedSize">
          <span class="meta-sep">&middot;</span>
          <span class="model-size">{{ formattedSize }}</span>
        </template>
      </span>
    </div>

    <!-- State: already downloaded — show path -->
    <div v-if="resource.already_downloaded && resource.target_path" class="card-path" :title="resource.target_path">
      {{ shortenedPath }}
    </div>

    <!-- State: missing + unresolved — show error / cannot resolve -->
    <div v-if="!resource.already_downloaded && !resource.resolved && !isDownloading" class="card-detail">
      <span class="card-error">{{ resource.error || 'Cannot resolve' }}</span>
    </div>

    <!-- State: missing + resolved + idle — show Download button -->
    <div v-if="showDownloadButton" class="card-detail">
      <button class="action-btn download-btn" @click="$emit('download', resource)">Download</button>
    </div>

    <!-- State: waiting (batch queue) -->
    <div v-if="resource.downloadStatus === 'waiting'" class="card-detail">
      <span class="card-status-text">Waiting...</span>
    </div>

    <!-- State: downloading — show progress bar + cancel -->
    <div v-if="resource.downloadStatus === 'downloading'" class="card-detail">
      <ProgressBar :value="resource.downloadProgress ?? 0" :showValue="false" class="download-progress" />
      <span class="progress-text">{{ formattedDownloaded }} / {{ formattedTotal }}</span>
      <button class="action-btn cancel-btn" @click="$emit('cancel', resource)">Cancel</button>
    </div>

    <!-- State: verifying SHA256 -->
    <div v-if="resource.downloadStatus === 'verifying'" class="card-detail">
      <span class="card-status-text">Verifying SHA256...</span>
    </div>

    <!-- State: failed — show error + retry -->
    <div v-if="resource.downloadStatus === 'failed'" class="card-detail">
      <span class="card-error">{{ resource.downloadError || 'Download failed' }}</span>
      <button class="action-btn retry-btn" @click="$emit('retry', resource)">Retry</button>
    </div>

    <!-- State: cancelled — show cancelled + download again -->
    <div v-if="resource.downloadStatus === 'cancelled'" class="card-detail">
      <span class="card-status-text">Cancelled</span>
      <button class="action-btn download-btn" @click="$emit('download', resource)">Download</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ProgressBar from 'primevue/progressbar'
import type { Resource } from '../types'

const props = defineProps<{
  resource: Resource
}>()

defineEmits<{
  download: [resource: Resource]
  cancel: [resource: Resource]
  retry: [resource: Resource]
}>()

const isDownloading = computed(() => {
  const s = props.resource.downloadStatus
  return s === 'downloading' || s === 'verifying' || s === 'waiting'
})

const showDownloadButton = computed(() => {
  const r = props.resource
  return !r.already_downloaded
    && r.resolved
    && (!r.downloadStatus || r.downloadStatus === 'idle')
})

const statusIcon = computed(() => {
  const r = props.resource
  if (r.downloadStatus === 'downloading' || r.downloadStatus === 'verifying' || r.downloadStatus === 'waiting') return '\u23F3'
  if (r.already_downloaded) return '\u2705'
  return '\u274C'
})

const cardClass = computed(() => {
  const r = props.resource
  if (r.downloadStatus === 'downloading' || r.downloadStatus === 'verifying' || r.downloadStatus === 'waiting') return 'model-downloading'
  if (!r.already_downloaded) return 'model-missing'
  return ''
})

const displayName = computed(() => {
  const name = props.resource.name
  if (name && name !== 'unknown') return name
  const fn = props.resource.filename
  if (fn) return fn.replace(/\.[^.]+$/, '')
  return 'unknown'
})

const formattedSize = computed(() => {
  const kb = props.resource.size_kb
  if (kb == null) return ''
  if (kb >= 1024 * 1024) return `${(kb / (1024 * 1024)).toFixed(1)} GB`
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`
  return `${kb.toFixed(1)} KB`
})

const shortenedPath = computed(() => {
  const p = props.resource.target_path
  if (!p) return ''
  const modelsIdx = p.replace(/\\/g, '/').indexOf('/models/')
  if (modelsIdx !== -1) {
    return p.replace(/\\/g, '/').slice(modelsIdx + 1)
  }
  return p.replace(/\\/g, '/').split('/').pop() || p
})

function formatBytes(bytes: number | undefined): string {
  if (bytes == null) return '?'
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${bytes} B`
}

const formattedDownloaded = computed(() => formatBytes(props.resource.downloadedBytes))
const formattedTotal = computed(() => formatBytes(props.resource.totalBytes))
</script>

<style scoped>
.model-card {
  padding: 8px 10px;
  background: var(--comfy-input-bg);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.model-missing {
  border-color: var(--p-red-500);
  border-style: dashed;
}

.model-downloading {
  border-color: var(--p-primary-500);
  border-style: solid;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.model-status {
  flex-shrink: 0;
  font-size: 12px;
}

.model-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.model-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  margin-left: auto;
}

.model-type-tag {
  display: inline-block;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--p-primary-500);
  background: rgba(var(--p-primary-500-rgb, 59, 130, 246), 0.15);
  border-radius: 3px;
  white-space: nowrap;
}

.meta-sep {
  color: var(--descrip-text);
  font-size: 11px;
}

.model-size {
  font-size: 11px;
  color: var(--descrip-text);
  white-space: nowrap;
}

.card-path {
  font-size: 10px;
  color: var(--descrip-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 4px;
}

.card-detail {
  margin-top: 6px;
}

.card-error {
  font-size: 10px;
  color: var(--error-text);
  display: block;
}

.card-status-text {
  font-size: 10px;
  color: var(--descrip-text);
}

.download-progress {
  height: 6px;
  margin-bottom: 4px;
}

.progress-text {
  font-size: 10px;
  color: var(--descrip-text);
  display: block;
  margin-bottom: 4px;
}

.action-btn {
  display: inline-block;
  padding: 3px 12px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  background: var(--comfy-input-bg);
  color: var(--fg-color);
  margin-top: 4px;
  transition: background 0.15s, border-color 0.15s;
}

.action-btn:hover {
  background: var(--border-color);
}

.download-btn {
  color: var(--p-primary-500);
  border-color: var(--p-primary-500);
}

.download-btn:hover {
  background: rgba(var(--p-primary-500-rgb, 59, 130, 246), 0.15);
}

.cancel-btn {
  color: var(--error-text);
  border-color: var(--error-text);
}

.cancel-btn:hover {
  background: rgba(220, 38, 38, 0.1);
}

.retry-btn {
  color: var(--p-primary-500);
  border-color: var(--p-primary-500);
  margin-top: 4px;
}

.retry-btn:hover {
  background: rgba(var(--p-primary-500-rgb, 59, 130, 246), 0.15);
}
</style>
