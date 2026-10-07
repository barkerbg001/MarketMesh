import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { WorkspaceContext } from '@/hooks/use-workspace'
import { errorMessage, getJson } from '@/lib/api'
import type { Agent, WorkspaceSettings } from '@/types/api'

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null)
  const [settingsError, setSettingsError] = useState<string | null>(null)

  const refreshSettings = useCallback(async () => {
    try {
      setSettings(await getJson<WorkspaceSettings>('/api/settings', 'Could not load settings'))
      setSettingsError(null)
    } catch (err) {
      setSettingsError(errorMessage(err, 'Could not load settings'))
    }
  }, [])

  useEffect(() => {
    void refreshSettings()
  }, [refreshSettings])

  // The API may still be starting when the page loads, so keep retrying until the roster arrives.
  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined
    const load = (attempt: number) => {
      getJson<{ agents: Agent[] }>('/api/agents', 'Could not load agents')
        .then((body) => {
          if (!cancelled) setAgents(body.agents)
        })
        .catch(() => {
          if (cancelled || attempt >= 20) return
          timer = setTimeout(() => {
            void refreshSettings()
            load(attempt + 1)
          }, 3000)
        })
    }
    load(0)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [refreshSettings])

  const agentById = useCallback(
    (id: string | null | undefined) => agents.find((agent) => agent.id === id),
    [agents],
  )

  const value = useMemo(
    () => ({ agents, agentById, settings, settingsError, setSettings, refreshSettings }),
    [agents, agentById, settings, settingsError, refreshSettings],
  )

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}
