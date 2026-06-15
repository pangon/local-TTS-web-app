<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { fetchAudiobooks, deleteAudiobook, type AudiobookSummary } from '@/api/audiobooks'

const audiobooks = ref<AudiobookSummary[]>([])
const loading = ref(true)
const loadError = ref<string | null>(null)

/** Id of the audiobook awaiting delete confirmation, or null. */
const pendingDeleteId = ref<string | null>(null)
const deletingId = ref<string | null>(null)
const deleteError = ref<string | null>(null)

async function loadAudiobooks() {
  loading.value = true
  loadError.value = null
  try {
    audiobooks.value = await fetchAudiobooks()
  } catch (e) {
    loadError.value = (e as Error).message || 'Failed to load library'
  } finally {
    loading.value = false
  }
}

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (isNaN(date.getTime())) return iso
  return date.toLocaleString()
}

function requestDelete(id: string) {
  deleteError.value = null
  pendingDeleteId.value = id
}

function cancelDelete() {
  pendingDeleteId.value = null
}

async function confirmDelete(id: string) {
  deletingId.value = id
  deleteError.value = null
  try {
    await deleteAudiobook(id)
    audiobooks.value = audiobooks.value.filter((a) => a.id !== id)
    pendingDeleteId.value = null
  } catch (e) {
    deleteError.value = (e as Error).message || 'Failed to delete audiobook'
  } finally {
    deletingId.value = null
  }
}

onMounted(loadAudiobooks)
</script>

<template>
  <div class="library-view">
    <h1>Library</h1>

    <p v-if="loading" class="loading">Loading…</p>

    <p v-else-if="loadError" class="error">{{ loadError }}</p>

    <p v-else-if="audiobooks.length === 0" class="empty-state">
      No audiobooks yet. Create one from the Create tab.
    </p>

    <ul v-else class="audiobook-list">
      <li v-for="book in audiobooks" :key="book.id" class="audiobook-item">
        <RouterLink :to="{ name: 'playback', params: { id: book.id } }" class="book-link">
          <span class="book-title">{{ book.title }}</span>
          <span class="book-meta">
            {{ formatDate(book.created_at) }} ·
            {{ book.chapter_count }} {{ book.chapter_count === 1 ? 'chapter' : 'chapters' }}
          </span>
        </RouterLink>

        <div class="book-actions">
          <template v-if="pendingDeleteId === book.id">
            <span class="confirm-text">Delete "{{ book.title }}"?</span>
            <button
              class="btn-danger"
              :disabled="deletingId === book.id"
              @click="confirmDelete(book.id)"
            >
              {{ deletingId === book.id ? 'Deleting…' : 'Confirm' }}
            </button>
            <button
              class="btn-secondary"
              :disabled="deletingId === book.id"
              @click="cancelDelete"
            >
              Cancel
            </button>
          </template>
          <button v-else class="btn-secondary" @click="requestDelete(book.id)">Delete</button>
        </div>
      </li>
    </ul>

    <p v-if="deleteError" class="error">{{ deleteError }}</p>
  </div>
</template>

<style scoped>
.library-view {
  max-width: 700px;
  margin: 0 auto;
  padding: 1rem;
}

.loading,
.empty-state {
  color: #666;
}

.error {
  color: #d32f2f;
}

.audiobook-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.audiobook-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.book-link {
  display: flex;
  flex-direction: column;
  text-decoration: none;
  color: inherit;
  flex: 1;
  min-width: 0;
}

.book-link:hover .book-title {
  text-decoration: underline;
}

.book-title {
  font-weight: 600;
}

.book-meta {
  color: #666;
  font-size: 0.875rem;
}

.book-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.confirm-text {
  font-size: 0.875rem;
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

.btn-danger {
  border-color: #d32f2f;
  background: #d32f2f;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #b71c1c;
}
</style>
