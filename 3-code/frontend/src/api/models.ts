/** API client for model management endpoints. */

export interface Model {
  model_id: string
  name: string
  is_cached: boolean
  is_loaded: boolean
  loader_available: boolean
}

export interface DownloadResponse {
  model_id: string
  status: string
}

export interface LoadResponse {
  model_id: string
  status: string
}

export interface InsufficientSpaceDetail {
  detail: string
  estimated_mb: number
  available_mb: number
}

export interface InsufficientVRAMDetail {
  detail: string
  required_mb: number
  available_mb: number
}

export async function fetchModels(): Promise<Model[]> {
  const res = await fetch('/api/v1/models')
  if (!res.ok) {
    throw new Error(`Failed to fetch models: ${res.status}`)
  }
  return res.json()
}

export async function downloadModel(modelId: string): Promise<DownloadResponse> {
  const res = await fetch(`/api/v1/models/${modelId}/download`, { method: 'POST' })
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
    throw new Error(typeof detail === 'string' ? detail : 'Download failed')
  }
  if (!res.ok) {
    throw new Error(`Failed to start download: ${res.status}`)
  }
  return res.json()
}

export async function loadModel(modelId: string): Promise<LoadResponse> {
  const res = await fetch(`/api/v1/models/${modelId}/load`, { method: 'POST' })
  if (res.status === 404) {
    throw new Error('Model not cached')
  }
  if (res.status === 409) {
    const body = await res.json()
    const detail = body.detail
    if (typeof detail === 'object' && detail !== null) {
      const err = new Error(detail.detail) as Error & {
        required_mb?: number
        available_mb?: number
      }
      err.required_mb = detail.required_mb
      err.available_mb = detail.available_mb
      throw err
    }
    throw new Error(typeof detail === 'string' ? detail : 'Load failed')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : `Failed to load model: ${res.status}`
    throw new Error(message)
  }
  return res.json()
}
