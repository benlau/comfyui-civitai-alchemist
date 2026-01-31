<template>
  <div class="generation-info">
    <h3 class="section-title">Generation Info</h3>

    <!-- Prompt (collapsible) -->
    <div v-if="metadata.prompt" class="collapsible-section">
      <button class="collapsible-header" @click="promptOpen = !promptOpen">
        <span class="collapsible-arrow" :class="{ open: promptOpen }">&#9654;</span>
        <span class="collapsible-label">Prompt</span>
      </button>
      <div v-show="promptOpen" class="collapsible-body prompt-text">
        {{ metadata.prompt }}
      </div>
    </div>

    <!-- Negative Prompt (collapsible) -->
    <div v-if="metadata.negative_prompt" class="collapsible-section">
      <button class="collapsible-header" @click="negPromptOpen = !negPromptOpen">
        <span class="collapsible-arrow" :class="{ open: negPromptOpen }">&#9654;</span>
        <span class="collapsible-label">Negative Prompt</span>
      </button>
      <div v-show="negPromptOpen" class="collapsible-body prompt-text">
        {{ metadata.negative_prompt }}
      </div>
    </div>

    <!-- Parameter grid -->
    <div class="param-grid">
      <template v-for="param in visibleParams" :key="param.label">
        <div class="param-label">{{ param.label }}</div>
        <div class="param-value">{{ param.value }}</div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Metadata } from '../types'

const props = defineProps<{
  metadata: Metadata
}>()

const promptOpen = ref(true)
const negPromptOpen = ref(false)

const visibleParams = computed(() => {
  const m = props.metadata
  const params: { label: string; value: string | number }[] = []

  if (m.sampler) params.push({ label: 'Sampler', value: m.sampler })
  if (m.steps != null) params.push({ label: 'Steps', value: m.steps })
  if (m.cfg_scale != null) params.push({ label: 'CFG Scale', value: m.cfg_scale })
  if (m.seed != null) params.push({ label: 'Seed', value: m.seed })
  if (m.size) params.push({ label: 'Size', value: `${m.size.width} × ${m.size.height}` })
  if (m.clip_skip != null) params.push({ label: 'Clip Skip', value: m.clip_skip })
  if (m.denoise != null) params.push({ label: 'Denoise', value: m.denoise })
  if (m.workflow_type) params.push({ label: 'Workflow', value: m.workflow_type })

  return params
})
</script>

<style scoped>
.generation-info {
  margin-bottom: 16px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.collapsible-section {
  margin-bottom: 6px;
}

.collapsible-header {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 6px 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--p-text-color);
  background: var(--comfy-input-bg);
  border: 1px solid var(--p-content-border-color);
  border-radius: 4px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.collapsible-header:hover {
  background: var(--comfy-menu-secondary-bg);
}

.collapsible-arrow {
  font-size: 8px;
  transition: transform 0.15s;
  display: inline-block;
}

.collapsible-arrow.open {
  transform: rotate(90deg);
}

.collapsible-label {
  flex: 1;
}

.collapsible-body {
  padding: 8px;
  margin-top: 2px;
  background: var(--comfy-input-bg);
  border: 1px solid var(--p-content-border-color);
  border-radius: 4px;
}

.prompt-text {
  font-size: 11px;
  line-height: 1.5;
  color: var(--p-text-muted-color);
  word-break: break-word;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

.param-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  margin-top: 8px;
  font-size: 12px;
}

.param-label {
  color: var(--p-text-muted-color);
  font-weight: 500;
  white-space: nowrap;
}

.param-value {
  color: var(--p-text-color);
  word-break: break-all;
}
</style>
