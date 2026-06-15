<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  fetchAudiobook,
  chapterAudioUrl,
  type AudiobookDetail,
  type Chapter,
} from '@/api/audiobooks'
import { fetchPlaybackPosition, savePlaybackPosition } from '@/api/playback'

const route = useRoute()
const id = route.params.id as string

const book = ref<AudiobookDetail | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)

/** Chapter number currently selected for playback. */
const currentChapter = ref(1)
/** Saved per-chapter timestamps (seconds), keyed by chapter number string. */
const savedPositions = ref<Record<string, number>>({})
/** Timestamp to seek to once the next chapter's audio metadata has loaded. */
const pendingSeek = ref(0)

const audioEl = ref<HTMLAudioElement | null>(null)

/** Chapters sorted by number so navigation is index-based and robust. */
const sortedChapters = computed<Chapter[]>(() =>
  [...(book.value?.chapters ?? [])].sort((a, b) => a.chapter_number - b.chapter_number),
)

const hasMultipleChapters = computed(() => sortedChapters.value.length > 1)

const currentIndex = computed(() =>
  sortedChapters.value.findIndex((c) => c.chapter_number === currentChapter.value),
)

const currentChapterInfo = computed<Chapter | null>(
  () => sortedChapters.value.find((c) => c.chapter_number === currentChapter.value) ?? null,
)

const canGoPrevious = computed(() => currentIndex.value > 0)
const canGoNext = computed(
  () => currentIndex.value >= 0 && currentIndex.value < sortedChapters.value.length - 1,
)

const currentAudioUrl = computed(() =>
  book.value ? chapterAudioUrl(id, currentChapter.value) : '',
)

async function load() {
  loading.value = true
  loadError.value = null
  try {
    const [detail, position] = await Promise.all([
      fetchAudiobook(id),
      fetchPlaybackPosition(id),
    ])
    savedPositions.value = position.chapters
    book.value = detail

    // Resume from the last active chapter if it still exists, otherwise the
    // first chapter (REQ-F-playback-resume).
    const exists = detail.chapters.some(
      (c) => c.chapter_number === position.last_chapter_number,
    )
    const startChapter = exists
      ? position.last_chapter_number
      : (sortedChapters.value[0]?.chapter_number ?? 1)
    currentChapter.value = startChapter
    pendingSeek.value = savedPositions.value[String(startChapter)] ?? 0
  } catch (e) {
    loadError.value = (e as Error).message || 'Failed to load audiobook'
  } finally {
    loading.value = false
  }
}

/**
 * Persists a chapter's position (and records it as the audiobook-level
 * bookmark). Updates local state and tolerates a failed network call so
 * playback is never interrupted by a bookmark error.
 */
async function persistPosition(chapterNumber: number, positionSeconds: number) {
  savedPositions.value[String(chapterNumber)] = positionSeconds
  try {
    await savePlaybackPosition(id, chapterNumber, positionSeconds)
  } catch {
    // Bookmark persistence is best-effort; ignore failures.
  }
}

/** Saves the current chapter and playback time (on pause, end, or unmount). */
function saveCurrentPosition() {
  if (!book.value || !audioEl.value) return
  void persistPosition(currentChapter.value, audioEl.value.currentTime)
}

function goToChapter(chapterNumber: number) {
  if (chapterNumber === currentChapter.value) return
  // Save where we are leaving before switching.
  saveCurrentPosition()
  const target = savedPositions.value[String(chapterNumber)] ?? 0
  pendingSeek.value = target
  currentChapter.value = chapterNumber
  // Record the new chapter as the active bookmark immediately.
  void persistPosition(chapterNumber, target)
}

function goPrevious() {
  if (!canGoPrevious.value) return
  goToChapter(sortedChapters.value[currentIndex.value - 1]!.chapter_number)
}

function goNext() {
  if (!canGoNext.value) return
  goToChapter(sortedChapters.value[currentIndex.value + 1]!.chapter_number)
}

/** Formats a file size in bytes as e.g. "3.2 MB", "812 KB", or "640 B". */
function formatFileSize(bytes: number | null): string | null {
  if (bytes === null || !isFinite(bytes) || bytes < 0) return null
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`
  return `${bytes} B`
}

/** Seeks to the saved position once a chapter's audio metadata is available. */
function onLoadedMetadata() {
  if (audioEl.value && pendingSeek.value > 0) {
    audioEl.value.currentTime = pendingSeek.value
  }
  pendingSeek.value = 0
}

onMounted(load)
onUnmounted(saveCurrentPosition)
</script>

<template>
  <div class="playback-view">
    <RouterLink :to="{ name: 'library' }" class="back-link">&larr; Library</RouterLink>

    <p v-if="loading" class="loading">Loading…</p>

    <p v-else-if="loadError" class="error">{{ loadError }}</p>

    <template v-else-if="book">
      <h1>{{ book.title }}</h1>
      <p class="book-model">Model: {{ book.model_id }}</p>

      <div class="player">
        <p class="now-playing">
          <span v-if="currentChapterInfo">{{ currentChapterInfo.title }}</span>
          <span
            v-if="currentChapterInfo && formatFileSize(currentChapterInfo.file_size_bytes)"
            class="chapter-size"
          >
            · {{ formatFileSize(currentChapterInfo.file_size_bytes) }}
          </span>
        </p>

        <audio
          ref="audioEl"
          class="audio-player"
          :src="currentAudioUrl"
          controls
          @pause="saveCurrentPosition"
          @ended="saveCurrentPosition"
          @loadedmetadata="onLoadedMetadata"
        ></audio>

        <div v-if="hasMultipleChapters" class="chapter-nav">
          <button class="btn-secondary" :disabled="!canGoPrevious" @click="goPrevious">
            ‹ Previous
          </button>
          <span class="chapter-indicator">
            Chapter {{ currentIndex + 1 }} of {{ sortedChapters.length }}
          </span>
          <button class="btn-secondary" :disabled="!canGoNext" @click="goNext">
            Next ›
          </button>
        </div>
      </div>

      <ul v-if="hasMultipleChapters" class="chapter-list">
        <li v-for="chapter in sortedChapters" :key="chapter.chapter_number">
          <button
            class="chapter-link"
            :class="{ active: chapter.chapter_number === currentChapter }"
            @click="goToChapter(chapter.chapter_number)"
          >
            <span class="chapter-title">{{ chapter.title }}</span>
            <span v-if="formatFileSize(chapter.file_size_bytes)" class="chapter-size">
              {{ formatFileSize(chapter.file_size_bytes) }}
            </span>
          </button>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.playback-view {
  max-width: 700px;
  margin: 0 auto;
  padding: 1rem;
}

.back-link {
  display: inline-block;
  margin-bottom: 1rem;
  color: #1976d2;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.loading {
  color: #666;
}

.error {
  color: #d32f2f;
}

.book-model {
  color: #666;
  font-size: 0.875rem;
  margin: -0.5rem 0 1rem;
}

.player {
  margin-bottom: 1.5rem;
}

.now-playing {
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.chapter-size {
  color: #666;
  font-weight: 400;
  font-size: 0.875rem;
}

.audio-player {
  width: 100%;
}

.chapter-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 0.75rem;
}

.chapter-indicator {
  font-size: 0.875rem;
  color: #666;
}

.chapter-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.chapter-list li {
  margin-bottom: 0.25rem;
}

.chapter-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  color: inherit;
  cursor: pointer;
  font-size: 0.875rem;
}

.chapter-link .chapter-size {
  flex-shrink: 0;
}

.chapter-link:hover {
  background: #f5f5f5;
}

.chapter-link.active {
  border-color: #1976d2;
  color: #1976d2;
  font-weight: 600;
}

button {
  padding: 0.4rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  border: 1px solid #1976d2;
  background: white;
  color: #1976d2;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary:hover:not(:disabled) {
  background: #e3f2fd;
}
</style>
