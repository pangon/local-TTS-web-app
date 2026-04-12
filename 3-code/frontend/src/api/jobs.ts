/** API client for synthesis job endpoints. */

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
 * Creates a synthesis job by uploading a .txt file.
 *
 * POST /api/v1/jobs/synthesis (multipart/form-data)
 *
 * @throws Error with message for 400 (validation) or 409 (no model / disk space).
 *   Disk-space errors carry `estimated_mb` and `available_mb` properties.
 */
export async function createSynthesisJob(
  file: File,
  voice?: string,
  language?: string,
): Promise<SynthesisJobResponse> {
  const form = new FormData()
  form.append('file', file)
  if (voice) form.append('voice', voice)
  if (language) form.append('language', language)

  const res = await fetch('/api/v1/jobs/synthesis', {
    method: 'POST',
    body: form,
  })

  if (res.status === 400) {
    const body = await res.json()
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Invalid file')
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
