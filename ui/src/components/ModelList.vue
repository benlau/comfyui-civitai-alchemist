<template>
  <div class="model-list">
    <div class="section-header">
      <h3 class="section-title">Models</h3>
      <span v-if="missingCount === 0" class="summary-text all-found">All found</span>
      <span v-else class="summary-text has-missing">Missing: {{ missingCount }} of {{ resources.length }}</span>
    </div>
    <div class="cards">
      <ModelCard
        v-for="(resource, index) in resources"
        :key="index"
        :resource="resource"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Resource } from '../types'
import ModelCard from './ModelCard.vue'

const props = defineProps<{
  resources: Resource[]
}>()

const missingCount = computed(() =>
  props.resources.filter(r => !r.already_downloaded).length
)
</script>

<style scoped>
.model-list {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-color);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-text {
  font-size: 11px;
}

.summary-text.all-found {
  color: var(--p-green-600);
  font-weight: 600;
}

.summary-text.has-missing {
  color: var(--error-text);
  font-weight: 600;
}

.cards {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>
