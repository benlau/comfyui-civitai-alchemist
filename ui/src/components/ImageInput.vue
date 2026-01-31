<template>
  <div class="image-input">
    <label class="input-label">Image ID or URL</label>
    <div class="input-row">
      <input
        ref="inputEl"
        v-model="inputValue"
        type="text"
        class="input-field"
        placeholder="116872916"
        :disabled="disabled || loading"
        @keydown.enter="submit"
      />
      <button
        class="go-btn"
        :disabled="disabled || loading || !inputValue.trim()"
        @click="submit"
      >
        {{ loading ? '...' : 'Go' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  disabled?: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [value: string]
}>()

const inputValue = ref('')
const inputEl = ref<HTMLInputElement>()

function submit() {
  if (props.disabled || props.loading || !inputValue.value.trim()) return
  emit('submit', inputValue.value.trim())
}
</script>

<style scoped>
.image-input {
  margin-bottom: 8px;
}

.input-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--descrip-text);
  margin-bottom: 4px;
}

.input-row {
  display: flex;
  gap: 4px;
}

.input-field {
  flex: 1;
  min-width: 0;
  padding: 6px 8px;
  font-size: 12px;
  color: var(--input-text);
  background: var(--comfy-input-bg);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  outline: none;
  transition: border-color 0.15s;
}

.input-field:focus {
  border-color: var(--p-primary-500);
}

.input-field:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.go-btn {
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: var(--p-primary-600);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
  white-space: nowrap;
}

.go-btn:hover:not(:disabled) {
  background: var(--p-primary-500);
}

.go-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
