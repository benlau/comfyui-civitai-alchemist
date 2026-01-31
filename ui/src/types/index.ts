/** Generation metadata returned by POST /civitai/fetch */
export interface Metadata {
  image_id?: number
  image_url?: string
  prompt: string
  negative_prompt?: string
  sampler?: string
  steps?: number
  cfg_scale?: number
  seed?: number | string
  size?: { width: number; height: number }
  base_size?: { width: number; height: number }
  model_name?: string
  model_hash?: string
  clip_skip?: number | string
  resources?: MetadataResource[]
  workflow_type?: string
  denoise?: number
  upscalers?: string[]
  raw_meta?: Record<string, unknown>
}

/** Resource entry from metadata (before resolution) */
export interface MetadataResource {
  hash?: string
  name?: string
  type?: string
  weight?: number
  model_version_id?: number
}

/** Resolved resource returned by POST /civitai/resolve */
export interface Resource {
  name: string
  type: string
  hash?: string
  weight?: number
  model_id?: number
  model_version_id?: number
  download_url?: string
  filename?: string
  size_kb?: number
  target_dir?: string
  target_path?: string
  already_downloaded: boolean
  resolved: boolean
  resolve_method?: string
  error?: string
}

/** Response from POST /civitai/resolve */
export interface ResolveResponse {
  resources: Resource[]
  resolved_count: number
  unresolved_count: number
}
