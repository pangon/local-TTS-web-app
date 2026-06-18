/** API client for synthesis job endpoints. */

export interface SynthesisJobRequest {
  /** Confirmed normalized text to synthesize exactly as-is (no re-preprocessing). */
  text: string
  /** Original uploaded filename, used to derive the audiobook title. */
  source_filename: string
  voice?: string
  language?: string
}

export interface SynthesisJobResponse {
  id: string
  type: 'synthesis'
  status: string
  progress: number
  created_at: string
}

export interface InsufficientDiskSpaceDetail {
  detail: string
  estimated_mb: number
  available_mb: number
}

/**
 * Creates a synthesis job from confirmed normalized text.
 *
 * POST /api/v1/jobs/synthesis (application/json)
 *
 * The text is the exact normalized text the user reviewed and confirmed after
 * `POST /preprocess` (DEC-preprocess-review-flow); the backend synthesizes it
 * as-is without re-running the preprocessing pipeline.
 *
 * @throws Error with message for 400 (empty text) or 409 (no model / disk
 *   space). Disk-space errors carry `estimated_mb` and `available_mb`
 *   properties.
 */
export async function createSynthesisJob(
  req: SynthesisJobRequest,
): Promise<SynthesisJobResponse> {
  const res = await fetch('/api/v1/jobs/synthesis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (res.status === 400) {
    const body = await res.json()
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Invalid request')
  }

  if (res.status === 409) {
    const body = await res.json()
    const detail = body.detail
    if (typeof detail === 'object' && detail !== null) {
      const err = new Error(detail.detail) as Error & {
        estimated_mb?: number
        available_mb?: number
      }
      err.estimated_mb = detail.estimated_mb
      err.available_mb = detail.available_mb
      throw err
    }
    throw new Error(typeof detail === 'string' ? detail : 'Cannot create synthesis job')
  }

  if (!res.ok) {
    throw new Error(`Failed to create synthesis job: ${res.status}`)
  }

  return res.json()
}
