/** API client for audiobook library endpoints. */

export interface AudiobookSummary {
  id: string
  title: string
  source_filename: string
  model_id: string
  voice: string | null
  language: string | null
  created_at: string
  chapter_count: number
}

/**
 * Fetches all audiobooks for the library view.
 *
 * GET /api/v1/audiobooks (REQ-F-library-listing)
 */
export async function fetchAudiobooks(): Promise<AudiobookSummary[]> {
  const res = await fetch('/api/v1/audiobooks')
  if (!res.ok) {
    throw new Error(`Failed to fetch audiobooks: ${res.status}`)
  }
  return res.json()
}

/**
 * Deletes an audiobook and all its associated audio files.
 *
 * DELETE /api/v1/audiobooks/{id} (REQ-F-delete-audiobook)
 *
 * @throws Error if the audiobook is not found (404) or the request fails.
 */
export async function deleteAudiobook(id: string): Promise<void> {
  const res = await fetch(`/api/v1/audiobooks/${id}`, { method: 'DELETE' })
  if (res.status === 404) {
    throw new Error('Audiobook not found')
  }
  if (!res.ok) {
    throw new Error(`Failed to delete audiobook: ${res.status}`)
  }
}
