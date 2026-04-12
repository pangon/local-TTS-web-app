<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { createSynthesisJob } from '@/api/jobs'
import {
  useSSE,
  type JobProgressEvent,
  type JobCompletedEvent,
  type JobFailedEvent,
} from '@/composables/useSSE'

const MAX_FILE_SIZE = 2 * 1024 * 1024 // 2 MB

const selectedFile = ref<File | null>(null)
const fileError = ref<string | null>(null)
const submitting = ref(false)
const submitError = ref<string | null>(null)

/** Tracks the active job after submission. */
const activeJobId = ref<string | null>(null)
const jobStatus = ref<string | null>(null)
const jobProgress = ref(0)
const jobError = ref<string | null>(null)
const jobCompleted = ref(false)

const canSubmit = computed(
  () => selectedFile.value !== null && !fileError.value && !submitting.value && !activeJobId.value,
)

const { on, off } = useSSE()

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null

  // Reset state
  fileError.value = null
  submitError.value = null
  jobError.value = null
  jobCompleted.value = false
  activeJobId.value = null
  jobStatus.value = null
  jobProgress.value = 0

  if (!file) {
    selectedFile.value = null
    return
  }

  if (!file.name.toLowerCase().endsWith('.txt')) {
    fileError.value = 'Only .txt files are accepted'
    selectedFile.value = null
    return
  }

  if (file.size > MAX_FILE_SIZE) {
    fileError.value = `File exceeds the 2 MB size limit (${(file.size / (1024 * 1024)).toFixed(1)} MB)`
    selectedFile.value = null
    return
  }

  selectedFile.value = file
}

async function submitJob() {
  if (!selectedFile.value) return

  submitting.value = true
  submitError.value = null
  jobError.value = null
  jobCompleted.value = false

  try {
    const job = await createSynthesisJob(selectedFile.value)
    activeJobId.value = job.id
    jobStatus.value = job.status
    jobProgress.value = job.progress
  } catch (e) {
    const err = e as Error & { estimated_mb?: number; available_mb?: number }
    if (err.estimated_mb !== undefined && err.available_mb !== undefined) {
      submitError.value = `Insufficient disk space: need ${err.estimated_mb} MB, have ${err.available_mb} MB`
    } else {
      submitError.value = err.message || 'Failed to create synthesis job'
    }
  } finally {
    submitting.value = false
  }
}

function onJobProgress(data: JobProgressEvent) {
  if (data.job_id !== activeJobId.value) return
  jobStatus.value = data.status
  jobProgress.value = data.progress
}

function onJobCompleted(data: JobCompletedEvent) {
  if (data.job_id !== activeJobId.value) return
  jobStatus.value = 'completed'
  jobProgress.value = 100
  jobCompleted.value = true
}

function onJobFailed(data: JobFailedEvent) {
  if (data.job_id !== activeJobId.value) return
  jobStatus.value = 'failed'
  jobError.value = data.error_message
}

function resetForm() {
  selectedFile.value = null
  fileError.value = null
  submitError.value = null
  activeJobId.value = null
  jobStatus.value = null
  jobProgress.value = 0
  jobError.value = null
  jobCompleted.value = false

  // Clear the file input
  const input = document.querySelector('.create-view input[type="file"]') as HTMLInputElement | null
  if (input) input.value = ''
}

onMounted(() => {
  on('job-progress', onJobProgress)
  on('job-completed', onJobCompleted)
  on('job-failed', onJobFailed)
})

onUnmounted(() => {
  off('job-progress', onJobProgress)
  off('job-completed', onJobCompleted)
  off('job-failed', onJobFailed)
})
</script>

<template>
  <div class="create-view">
    <h1>Create Audiobook</h1>

    <div class="upload-section">
      <label class="file-label" for="file-input">
        Select a .txt file (UTF-8, max 2 MB)
      </label>
      <input
        id="file-input"
        type="file"
        accept=".txt"
        :disabled="!!activeJobId"
        @change="onFileChange"
      />
      <p v-if="fileError" class="error">{{ fileError }}</p>
    </div>

    <div v-if="selectedFile && !fileError" class="file-info">
      <span class="file-name">{{ selectedFile.name }}</span>
      <span class="file-size">({{ (selectedFile.size / 1024).toFixed(1) }} KB)</span>
    </div>

    <div class="actions">
      <button
        :disabled="!canSubmit"
        @click="submitJob"
      >
        {{ submitting ? 'Submitting...' : 'Start Synthesis' }}
      </button>

      <button
        v-if="jobCompleted || jobError"
        class="btn-secondary"
        @click="resetForm"
      >
        New Audiobook
      </button>
    </div>

    <p v-if="submitError" class="error">{{ submitError }}</p>

    <!-- Job progress section -->
    <div v-if="activeJobId" class="progress-section">
      <div class="status-row">
        <span class="status-label">Status:</span>
        <span
          class="status-value"
          :class="{
            'status-completed': jobStatus === 'completed',
            'status-failed': jobStatus === 'failed',
            'status-processing': jobStatus === 'processing',
            'status-queued': jobStatus === 'queued',
          }"
        >
          {{ jobStatus }}
        </span>
      </div>

      <div v-if="jobStatus === 'processing' || jobStatus === 'queued'" class="progress-bar">
        <progress :value="jobProgress" max="100"></progress>
        <span class="progress-text">{{ jobProgress }}%</span>
      </div>

      <p v-if="jobCompleted" class="success-message">
        Audiobook created successfully!
      </p>

      <p v-if="jobError" class="error">{{ jobError }}</p>
    </div>
  </div>
</template>

<style scoped>
.create-view {
  max-width: 600px;
  margin: 0 auto;
  padding: 1rem;
}

.upload-section {
  margin-bottom: 1rem;
}

.file-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.file-info {
  margin-bottom: 1rem;
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  border-radius: 4px;
}

.file-name {
  font-weight: 600;
}

.file-size {
  color: #666;
  font-size: 0.875rem;
  margin-left: 0.5rem;
}

.actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.error {
  color: #d32f2f;
}

.success-message {
  color: #2e7d32;
  font-weight: 500;
}

.progress-section {
  margin-top: 1.5rem;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.status-row {
  margin-bottom: 0.75rem;
}

.status-label {
  font-weight: 500;
  margin-right: 0.5rem;
}

.status-completed {
  color: #2e7d32;
  font-weight: 600;
}

.status-failed {
  color: #d32f2f;
  font-weight: 600;
}

.status-processing {
  color: #1565c0;
}

.status-queued {
  color: #757575;
}

.progress-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-bar progress {
  flex: 1;
  height: 1.25rem;
}

.progress-text {
  font-size: 0.875rem;
  min-width: 3rem;
}

button {
  padding: 0.5rem 1.5rem;
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

.btn-secondary {
  background: white;
  color: #1976d2;
}

.btn-secondary:hover:not(:disabled) {
  background: #e3f2fd;
}
</style>
