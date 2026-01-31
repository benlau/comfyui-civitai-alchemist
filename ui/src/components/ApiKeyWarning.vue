<template>
  <div class="api-key-warning">
    <div class="warning-box">
      <p class="warning-title">⚠ Civitai API Key not configured.</p>
      <p class="warning-text">
        Go to Settings (Ctrl+,) → Civitai Alchemist to set your API key.
      </p>
      <button class="open-settings-btn" @click="openSettings">Open Settings</button>
    </div>
  </div>
</template>

<script setup lang="ts">
function openSettings() {
  // Trigger ComfyUI's settings dialog by dispatching Ctrl+, keyboard event
  document.dispatchEvent(new KeyboardEvent('keydown', {
    key: ',',
    code: 'Comma',
    ctrlKey: true,
    bubbles: true,
  }))
}
</script>

<style scoped>
.api-key-warning {
  margin-bottom: 8px;
}

.warning-box {
  background: var(--comfy-input-bg);
  border: 1px solid var(--p-yellow-500);
  border-radius: 6px;
  padding: 12px;
}

.warning-title {
  margin: 0 0 6px 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--p-yellow-500);
}

.warning-text {
  margin: 0 0 10px 0;
  font-size: 12px;
  color: var(--descrip-text);
  line-height: 1.4;
}

.open-settings-btn {
  display: block;
  width: 100%;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--fg-color);
  background: var(--comfy-menu-secondary-bg);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}

.open-settings-btn:hover {
  background: var(--border-color);
}
</style>
