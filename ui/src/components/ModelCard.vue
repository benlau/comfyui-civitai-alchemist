<template>
  <div class="model-card" :class="{ 'model-missing': !resource.already_downloaded }">
    <div class="card-header">
      <span class="model-status">{{ resource.already_downloaded ? '✅' : '❌' }}</span>
      <span class="model-name" :title="resource.name">{{ resource.name }}</span>
    </div>
    <div class="card-details">
      <span class="model-type-tag">{{ resource.type }}</span>
      <span v-if="formattedSize" class="model-size">{{ formattedSize }}</span>
    </div>
    <div v-if="resource.already_downloaded && resource.target_path" class="card-path" :title="resource.target_path">
      Found in: {{ resource.target_path }}
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

const formattedSize = computed(() => {
  const kb = props.resource.size_kb
  if (kb == null) return ''
  if (kb >= 1024 * 1024) return `${(kb / (1024 * 1024)).toFixed(1)} GB`
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`
  return `${kb} KB`
})
</script>

<style scoped>
.model-card {
  padding: 8px 10px;
  background: var(--comfy-input-bg);
  border: 1px solid var(--p-content-border-color);
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
  margin-bottom: 4px;
}

.model-status {
  flex-shrink: 0;
  font-size: 12px;
}

.model-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--p-text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-details {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.model-type-tag {
  display: inline-block;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--p-primary-400);
  background: rgba(var(--p-primary-500-rgb, 59, 130, 246), 0.15);
  border-radius: 3px;
}

.model-size {
  font-size: 11px;
  color: var(--p-text-muted-color);
}

.card-path {
  font-size: 10px;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 4px;
}

.card-error {
  font-size: 10px;
  color: var(--p-red-400);
  margin-top: 4px;
}
</style>
