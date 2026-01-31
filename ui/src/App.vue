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
        <ModelList v-if="resources.length > 0" :resources="resources" />
      </template>

      <!-- Empty state hint -->
      <p v-if="!loading && !error && !metadata && apiKeySet" class="hint-text">
        Paste a Civitai image ID or URL to get started.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Metadata, Resource } from './types'
import { getApiKey, parseImageId, fetchMetadata, resolveModels } from './composables/useCivitaiApi'
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

function checkApiKey() {
  apiKeySet.value = !!getApiKey()
}

onMounted(() => {
  checkApiKey()
  // Re-check API key periodically in case user sets it via Settings
  setInterval(checkApiKey, 2000)
})

async function handleSubmit(input: string) {
  error.value = ''
  metadata.value = null
  resources.value = []

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
</style>
