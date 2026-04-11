<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { fetchModels, downloadModel, loadModel, type Model } from '@/api/models'
import {
  useSSE,
  type DownloadProgressEvent,
  type DownloadCompletedEvent,
  type DownloadFailedEvent,
} from '@/composables/useSSE'

const models = ref<Model[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

/** Maps model_id → download progress (0–100). */
const downloadProgress = ref<Record<string, number>>({})
/** Maps model_id → error message for failed downloads. */
const downloadErrors = ref<Record<string, string>>({})
/** model_id currently being loaded onto GPU. */
const loadingModelId = ref<string | null>(null)
/** Error from the most recent load attempt. */
const loadError = ref<string | null>(null)

const { on, off } = useSSE()

const loadedModel = computed(() => models.value.find((m) => m.is_loaded) ?? null)

async function refresh() {
  loading.value = true
  error.value = null
  try {
    models.value = await fetchModels()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load models'
  } finally {
    loading.value = false
  }
}

async function startDownload(modelId: string) {
  downloadErrors.value[modelId] = ''
  downloadProgress.value[modelId] = 0
  try {
    await downloadModel(modelId)
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Download failed'
    const diskErr = e as Error & { estimated_mb?: number; available_mb?: number }
    if (diskErr.estimated_mb !== undefined && diskErr.available_mb !== undefined) {
      downloadErrors.value[modelId] =
        `Insufficient disk space: need ${diskErr.estimated_mb} MB, have ${diskErr.available_mb} MB`
    } else {
      downloadErrors.value[modelId] = msg
    }
    delete downloadProgress.value[modelId]
  }
}

async function startLoad(modelId: string) {
  loadError.value = null
  loadingModelId.value = modelId
  try {
    await loadModel(modelId)
    await refresh()
  } catch (e) {
    const vramErr = e as Error & { required_mb?: number; available_mb?: number }
    if (vramErr.required_mb !== undefined && vramErr.available_mb !== undefined) {
      loadError.value =
        `Insufficient VRAM: need ${vramErr.required_mb} MB, have ${vramErr.available_mb} MB`
    } else {
      loadError.value = e instanceof Error ? e.message : 'Load failed'
    }
  } finally {
    loadingModelId.value = null
  }
}

function onDownloadProgress(data: DownloadProgressEvent) {
  downloadProgress.value[data.model_id] = data.progress
}

function onDownloadCompleted(data: DownloadCompletedEvent) {
  delete downloadProgress.value[data.model_id]
  delete downloadErrors.value[data.model_id]
  refresh()
}

function onDownloadFailed(data: DownloadFailedEvent) {
  downloadErrors.value[data.model_id] = data.error_message
  delete downloadProgress.value[data.model_id]
}

onMounted(() => {
  on('download-progress', onDownloadProgress)
  on('download-completed', onDownloadCompleted)
  on('download-failed', onDownloadFailed)
  refresh()
})

onUnmounted(() => {
  off('download-progress', onDownloadProgress)
  off('download-completed', onDownloadCompleted)
  off('download-failed', onDownloadFailed)
})

function isDownloading(modelId: string): boolean {
  return modelId in downloadProgress.value
}
</script>

<template>
  <div class="models-view">
    <h1>Model Management</h1>

    <p v-if="loading && models.length === 0">Loading models...</p>
    <p v-if="error" class="error">{{ error }}</p>

    <p v-if="loadError" class="error">{{ loadError }}</p>

    <div v-if="loadedModel" class="loaded-banner">
      Currently loaded: <strong>{{ loadedModel.name }}</strong>
    </div>

    <ul v-if="models.length > 0" class="model-list">
      <li v-for="model in models" :key="model.model_id" class="model-item">
        <div class="model-info">
          <span class="model-name">{{ model.name }}</span>
          <span class="model-id">{{ model.model_id }}</span>
          <span v-if="model.is_loaded" class="badge badge-loaded">Loaded</span>
          <span v-else-if="model.is_cached" class="badge badge-cached">Cached</span>
          <span v-else class="badge badge-remote">Not cached</span>
        </div>

        <div class="model-actions">
          <span v-if="!model.loader_available" class="badge badge-no-adapter">No adapter</span>

          <!-- Download button: shown when not cached, has adapter, and not currently downloading -->
          <button
            v-if="model.loader_available && !model.is_cached && !isDownloading(model.model_id)"
            @click="startDownload(model.model_id)"
          >
            Download
          </button>

          <!-- Download progress -->
          <div v-if="isDownloading(model.model_id)" class="progress-container">
            <progress
              :value="downloadProgress[model.model_id]"
              max="100"
            ></progress>
            <span class="progress-text">{{ downloadProgress[model.model_id] }}%</span>
          </div>

          <!-- Download error -->
          <p v-if="downloadErrors[model.model_id]" class="error">
            {{ downloadErrors[model.model_id] }}
          </p>

          <!-- Load button: shown when cached, has adapter, but not loaded -->
          <button
            v-if="model.loader_available && model.is_cached && !model.is_loaded"
            :disabled="loadingModelId !== null"
            @click="startLoad(model.model_id)"
          >
            {{ loadingModelId === model.model_id ? 'Loading...' : 'Load' }}
          </button>
        </div>
      </li>
    </ul>

    <p v-if="!loading && models.length === 0 && !error">No models available.</p>
  </div>
</template>

<style scoped>
.models-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
}

.error {
  color: #d32f2f;
}

.loaded-banner {
  background: #e8f5e9;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.model-list {
  list-style: none;
  padding: 0;
}

.model-item {
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 1rem;
  margin-bottom: 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.model-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.model-name {
  font-weight: 600;
}

.model-id {
  color: #666;
  font-size: 0.875rem;
}

.badge {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-weight: 500;
}

.badge-loaded {
  background: #c8e6c9;
  color: #2e7d32;
}

.badge-cached {
  background: #bbdefb;
  color: #1565c0;
}

.badge-remote {
  background: #f5f5f5;
  color: #757575;
}

.badge-no-adapter {
  background: #fff3e0;
  color: #e65100;
}

.model-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-text {
  font-size: 0.875rem;
  min-width: 3rem;
}

button {
  padding: 0.375rem 1rem;
  border: 1px solid #1976d2;
  background: #1976d2;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

button:hover:not(:disabled) {
  background: #1565c0;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
