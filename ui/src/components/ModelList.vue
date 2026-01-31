<template>
  <div class="model-list">
    <div class="section-header">
      <h3 class="section-title">Models</h3>
      <span class="summary-text" :class="{ 'has-missing': missingCount > 0 }">
        Missing: {{ missingCount }} of {{ resources.length }}
      </span>
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
  color: var(--p-text-color);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-text {
  font-size: 11px;
  color: var(--p-text-muted-color);
}

.summary-text.has-missing {
  color: var(--p-red-400);
  font-weight: 600;
}

.cards {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>
