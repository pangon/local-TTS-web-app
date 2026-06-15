/** API client for the two-level playback position bookmark (REQ-F-playback-resume). */

export interface PlaybackPosition {
  /** Audiobook-level bookmark: the last active chapter number. */
  last_chapter_number: number
  /** Per-chapter timestamps (seconds), keyed by chapter number as a string. */
  chapters: Record<string, number>
}

/**
 * Fetches the saved playback position for an audiobook.
 *
 * GET /api/v1/audiobooks/{id}/position (REQ-F-playback-resume).
 * Returns `{ last_chapter_number: 1, chapters: {} }` when the audiobook has
 * never been played.
 *
 * @throws Error if the audiobook is not found (404) or the request fails.
 */
export async function fetchPlaybackPosition(id: string): Promise<PlaybackPosition> {
  const res = await fetch(`/api/v1/audiobooks/${id}/position`)
  if (res.status === 404) {
    throw new Error('Audiobook not found')
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch playback position: ${res.status}`)
  }
  return res.json()
}

/**
 * Saves both the audiobook-level bookmark (the given chapter) and that
 * chapter's timestamp.
 *
 * PUT /api/v1/audiobooks/{id}/position (REQ-F-playback-resume). Called on
 * pause, on chapter change, and when leaving the view.
 *
 * @throws Error if the request fails.
 */
export async function savePlaybackPosition(
  id: string,
  chapterNumber: number,
  positionSeconds: number,
): Promise<void> {
  const res = await fetch(`/api/v1/audiobooks/${id}/position`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chapter_number: chapterNumber,
      position_seconds: positionSeconds,
    }),
  })
  if (!res.ok) {
    throw new Error(`Failed to save playback position: ${res.status}`)
  }
}
