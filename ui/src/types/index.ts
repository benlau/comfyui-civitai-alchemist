/** Generation metadata from Civitai image */
export interface Metadata {
  prompt: string
  negativePrompt?: string
  sampler?: string
  steps?: number
  cfgScale?: number
  seed?: number | string
  width?: number
  height?: number
  clipSkip?: number
  resources?: MetadataResource[]
  hpiSteps?: number
  hiresDenoise?: number
  hiresUpscaler?: string
  hiresScale?: number
}

/** Resource entry from metadata */
export interface MetadataResource {
  hash?: string
  name?: string
  type?: string
  weight?: number
}

/** Resolved resource with download info and existence status */
export interface Resource {
  name: string
  type: string
  hash?: string
  downloadUrl?: string
  fileSize?: number
  modelVersionId?: number
  exists: boolean
  localPath?: string
}
