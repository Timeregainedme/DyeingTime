import type React from 'react'
import { useOutletContext } from 'react-router-dom'

export type StepKey =
  | 'consistency'
  | 'divide'
  | 'extract'

export type PrepFlowContext = {
  projectId: string
  chapterId: string

  baseRawText: string
  setBaseRawText: React.Dispatch<React.SetStateAction<string>>
  workingScriptText: string
  setWorkingScriptText: React.Dispatch<React.SetStateAction<string>>
  openScriptEditor: () => void

  consistencyResult: Record<string, any> | null
  setConsistencyResult: React.Dispatch<React.SetStateAction<Record<string, any> | null>>
  consistencyDone: boolean
  setConsistencyDone: React.Dispatch<React.SetStateAction<boolean>>

  scriptDivision: Record<string, any> | null
  setScriptDivision: React.Dispatch<React.SetStateAction<Record<string, any> | null>>

  editableShots: Array<Record<string, any>>
  setEditableShots: React.Dispatch<React.SetStateAction<Array<Record<string, any>>>>

  extractionDraft: Record<string, any> | null
  setExtractionDraft: React.Dispatch<React.SetStateAction<Record<string, any> | null>>
}

export function usePrepFlow() {
  return useOutletContext<PrepFlowContext>()
}

