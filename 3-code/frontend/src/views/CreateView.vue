<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { preprocessFile } from '@/api/preprocess'
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

// Optional output language. No selector yet (added by TASK-voice-language-selection-ui,
// Phase 6); kept here so the same language flows to both /preprocess and /jobs/synthesis.
const selectedLanguage = ref<string | undefined>(undefined)

// --- Step 1: preprocess & review (DEC-preprocess-review-flow) ---
const preprocessing = ref(false)
const preprocessError = ref<string | null>(null)
/** The normalized text under review. `null` means no review is active yet. */
const normalizedText = ref<string | null>(null)
const originalCharCount = ref(0)
const normalizedCharCount = ref(0)
/** Language resolved by /preprocess; forwarded verbatim to /jobs/synthesis. */
const resolvedLanguage = ref<string | undefined>(undefined)

// --- Step 2: synthesis ---
const submitting = ref(false)
const submitError = ref<string | null>(null)

/** Tracks the active job after submission. */
const activeJobId = ref<string | null>(null)
const jobStatus = ref<string | null>(null)
const jobProgress = ref(0)
const jobError = ref<string | null>(null)
const jobCompleted = ref(false)

const inReview = computed(() => normalizedText.value !== null)

const canPreprocess = computed(
  () =>
    selectedFile.value !== null &&
    !fileError.value &&
    !preprocessing.value &&
    !inReview.value &&
    !activeJobId.value,
)

const canSynthesize = computed(
  () =>
    inReview.value &&
    (normalizedText.value?.trim().length ?? 0) > 0 &&
    !submitting.value &&
    !activeJobId.value,
)

const { on, off } = useSSE()

function resetReviewAndJob() {
  preprocessError.value = null
  normalizedText.value = null
  originalCharCount.value = 0
  normalizedCharCount.value = 0
  resolvedLanguage.value = undefined
  submitError.value = null
  jobError.value = null
  jobCompleted.value = false
  activeJobId.value = null
  jobStatus.value = null
  jobProgress.value = 0
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null

  // Reset all downstream state when the input changes.
  fileError.value = null
  resetReviewAndJob()

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

/** Step 1: normalize the uploaded file and enter the review step. */
async function preprocess() {
  if (!selectedFile.value) return

  preprocessing.value = true
  preprocessError.value = null

  try {
    const result = await preprocessFile(selectedFile.value, selectedLanguage.value)
    normalizedText.value = result.normalized_text
    originalCharCount.value = result.original_char_count
    normalizedCharCount.value = result.normalized_char_count
    // Forward the resolved language to synthesis so both calls agree.
    resolvedLanguage.value = result.language
  } catch (e) {
    preprocessError.value = (e as Error).message || 'Failed to preprocess text'
  } finally {
    preprocessing.value = false
  }
}

/** Step 2: synthesize exactly the reviewed text (no re-preprocessing). */
async function submitJob() {
  if (!canSynthesize.value || normalizedText.value === null || !selectedFile.value) return

  submitting.value = true
  submitError.value = null
  jobError.value = null
  jobCompleted.value = false

  try {
    const job = await createSynthesisJob({
      text: normalizedText.value,
      source_filename: selectedFile.value.name,
      language: resolvedLanguage.value,
    })
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
  resetReviewAndJob()

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
        :disabled="preprocessing || inReview || !!activeJobId"
        @change="onFileChange"
      />
      <p v-if="fileError" class="error">{{ fileError }}</p>
    </div>

    <div v-if="selectedFile && !fileError" class="file-info">
      <span class="file-name">{{ selectedFile.name }}</span>
      <span class="file-size">({{ (selectedFile.size / 1024).toFixed(1) }} KB)</span>
    </div>

    <!-- Step 1: trigger preprocessing -->
    <div v-if="!inReview" class="actions">
      <button :disabled="!canPreprocess" @click="preprocess">
        {{ preprocessing ? 'Preprocessing…' : 'Preprocess & Review' }}
      </button>
    </div>

    <p v-if="preprocessing" class="busy-message">
      Normalizing text… this may take a few seconds.
    </p>
    <p v-if="preprocessError" class="error">{{ preprocessError }}</p>

    <!-- Step 2: review the normalized text and confirm (REQ-USA-normalized-text-review) -->
    <div v-if="inReview" class="review-section">
      <h2>Review normalized text</h2>
      <p class="review-hint">
        This is exactly what will be read aloud, including how numbers, dates, and
        symbols were verbalized. Review it — and edit if needed — then confirm to
        start generation.
      </p>
      <p class="char-counts">
        {{ originalCharCount }} → {{ normalizedCharCount }} characters after normalization
      </p>
      <textarea
        v-model="normalizedText"
        class="review-textarea"
        rows="16"
        :disabled="submitting || !!activeJobId"
        aria-label="Normalized text to be synthesized"
      ></textarea>

      <div v-if="!activeJobId" class="actions">
        <button :disabled="!canSynthesize" @click="submitJob">
          {{ submitting ? 'Submitting…' : 'Confirm & Start Synthesis' }}
        </button>
        <button class="btn-secondary" :disabled="submitting" @click="resetForm">
          Start Over
        </button>
      </div>

      <p v-if="submitError" class="error">{{ submitError }}</p>
    </div>

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

    <div v-if="jobCompleted || jobError" class="actions">
      <button class="btn-secondary" @click="resetForm">New Audiobook</button>
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

.busy-message {
  color: #1565c0;
  font-style: italic;
}

.success-message {
  color: #2e7d32;
  font-weight: 500;
}

.review-section {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
}

.review-section h2 {
  font-size: 1.1rem;
  margin-bottom: 0.25rem;
}

.review-hint {
  color: #555;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.char-counts {
  color: #666;
  font-size: 0.8125rem;
  margin-bottom: 0.5rem;
}

.review-textarea {
  width: 100%;
  box-sizing: border-box;
  font-family: inherit;
  font-size: 0.9375rem;
  line-height: 1.5;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  resize: vertical;
  margin-bottom: 0.75rem;
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
