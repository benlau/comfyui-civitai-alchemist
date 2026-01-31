<template>
  <div class="generation-info">
    <h3 class="section-title">Generation Info</h3>

    <!-- Prompt (collapsible accordion panel) -->
    <div v-if="metadata.prompt" class="accordion-panel" :class="{ open: promptOpen }">
      <button class="accordion-header" @click="promptOpen = !promptOpen">
        <span class="toggle-icon" :class="{ open: promptOpen }">&#9656;</span>
        <span>Prompt</span>
      </button>
      <div v-show="promptOpen" class="accordion-body prompt-text">
        {{ metadata.prompt }}
      </div>
    </div>

    <!-- Negative Prompt (collapsible accordion panel) -->
    <div v-if="metadata.negative_prompt" class="accordion-panel" :class="{ open: negPromptOpen }">
      <button class="accordion-header" @click="negPromptOpen = !negPromptOpen">
        <span class="toggle-icon" :class="{ open: negPromptOpen }">&#9656;</span>
        <span>Negative Prompt</span>
      </button>
      <div v-show="negPromptOpen" class="accordion-body prompt-text">
        {{ metadata.negative_prompt }}
      </div>
    </div>

    <!-- Parameters: two-column grid -->
    <div class="param-grid">
      <template v-for="param in visibleParams" :key="param.label">
        <span class="param-label">{{ param.label }}</span>
        <span class="param-value">{{ param.value }}</span>
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
  color: var(--fg-color);
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.accordion-panel {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  margin-bottom: 6px;
  overflow: hidden;
}

.accordion-header {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  padding: 6px 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--descrip-text);
  background: var(--comfy-input-bg);
  border: none;
  cursor: pointer;
  transition: color 0.15s;
}

.accordion-header:hover {
  color: var(--fg-color);
}

.toggle-icon {
  font-size: 10px;
  transition: transform 0.15s;
  display: inline-block;
}

.toggle-icon.open {
  transform: rotate(90deg);
}

.accordion-body {
  padding: 8px;
  border-top: 1px solid var(--border-color);
}

.prompt-text {
  font-size: 11px;
  line-height: 1.5;
  color: var(--descrip-text);
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
  color: var(--descrip-text);
  font-weight: 600;
  white-space: nowrap;
}

.param-value {
  color: var(--fg-color);
}
</style>
