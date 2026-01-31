<template>
  <div class="model-card" :class="{ 'model-missing': !resource.already_downloaded }">
    <div class="card-header">
      <span class="model-status">{{ resource.already_downloaded ? '✅' : '❌' }}</span>
      <span class="model-name" :title="displayName">{{ displayName }}</span>
      <span class="model-meta">
        <span class="model-type-tag">{{ resource.type }}</span>
        <template v-if="formattedSize">
          <span class="meta-sep">·</span>
          <span class="model-size">{{ formattedSize }}</span>
        </template>
      </span>
    </div>
    <div v-if="resource.already_downloaded && resource.target_path" class="card-path" :title="resource.target_path">
      {{ shortenedPath }}
    </div>
    <div v-if="!resource.resolved && resource.error" class="card-error">
      {{ resource.error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Resource } from '../types'

const props = defineProps<{
  resource: Resource
}>()

const displayName = computed(() => {
  const name = props.resource.name
  if (name && name !== 'unknown') return name
  // Fallback: use filename without extension
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
  // Show path relative to models/ directory
  const modelsIdx = p.replace(/\\/g, '/').indexOf('/models/')
  if (modelsIdx !== -1) {
    return p.replace(/\\/g, '/').slice(modelsIdx + 1)
  }
  // Fallback: show just the filename
  return p.replace(/\\/g, '/').split('/').pop() || p
})
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

.card-error {
  font-size: 10px;
  color: var(--error-text);
  margin-top: 4px;
}
</style>
