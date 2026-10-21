import { FilmService } from './generated'
import type { GenerationTaskLinkRead } from './generated'

type ListTaskLinksParams = Parameters<typeof FilmService.listTaskLinksApiV1FilmTaskLinksGet>[0]

type UnknownRecord = Record<string, unknown>

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null
}

function toTaskLinkArray(value: unknown): GenerationTaskLinkRead[] {
  if (Array.isArray(value)) {
    return value.filter(isRecord) as GenerationTaskLinkRead[]
  }

  if (!isRecord(value)) {
    return []
  }

  const collectionKeys = ['items', 'list', 'records', 'rows'] as const
  for (const key of collectionKeys) {
    const candidate = value[key]
    if (Array.isArray(candidate)) {
      return candidate.filter(isRecord) as GenerationTaskLinkRead[]
    }
  }

  if (isRecord(value.data)) {
    return toTaskLinkArray(value.data)
  }

  return []
}

export function normalizeTaskLinksResponse(response: unknown): GenerationTaskLinkRead[] {
  if (!isRecord(response)) {
    return []
  }

  return toTaskLinkArray(response.data)
}

export async function listTaskLinksNormalized(params: ListTaskLinksParams): Promise<GenerationTaskLinkRead[]> {
  const response = await FilmService.listTaskLinksApiV1FilmTaskLinksGet(params)
  return normalizeTaskLinksResponse(response)
}

