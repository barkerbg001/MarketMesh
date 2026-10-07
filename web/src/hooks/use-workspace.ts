import { createContext, useContext } from 'react'

import type { Agent, WorkspaceSettings } from '@/types/api'

export type WorkspaceContextValue = {
  agents: Agent[]
  agentById: (id: string | null | undefined) => Agent | undefined
  settings: WorkspaceSettings | null
  settingsError: string | null
  setSettings: (settings: WorkspaceSettings) => void
  refreshSettings: () => Promise<void>
}

export const WorkspaceContext = createContext<WorkspaceContextValue | null>(null)

export function useWorkspace() {
  const context = useContext(WorkspaceContext)
  if (!context) throw new Error('useWorkspace must be used within WorkspaceProvider')
  return context
}
