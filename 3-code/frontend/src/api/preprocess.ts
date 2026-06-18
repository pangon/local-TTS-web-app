/** API client for the text-preprocessing endpoint. */

export interface PreprocessResponse {
  /** Normalized, TTS-ready text — exactly what will be synthesized after confirmation. */
  normalized_text: string
  /** Resolved output language (echoes the request or the configured default). */
  language: string
  /** Id of the model whose preprocessing profile was applied, if any. */
  model_id: string | null
  original_char_count: number
  normalized_char_count: number
}

/**
 * Runs the normalization pipeline on an uploaded .txt file and returns the
 * normalized text for review (first step of the preprocess-then-confirm flow,
 * DEC-preprocess-review-flow).
 *
 * POST /api/v1/preprocess (multipart/form-data)
 *
 * @throws Error with message for 400 (validation: type/size/encoding/empty) or
 *   409 (no model loaded).
 */
export async function preprocessFile(
  file: File,
  language?: string,
): Promise<PreprocessResponse> {
  const form = new FormData()
  form.append('file', file)
  if (language) form.append('language', language)

  const res = await fetch('/api/v1/preprocess', {
    method: 'POST',
    body: form,
  })

  if (res.status === 400) {
    const body = await res.json()
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Invalid input')
  }

  if (res.status === 409) {
    const body = await res.json()
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Cannot preprocess text')
  }

  if (!res.ok) {
    throw new Error(`Failed to preprocess text: ${res.status}`)
  }

  return res.json()
}
