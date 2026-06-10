import { createContext, useContext } from 'react'
import type { Workspace } from '../../lib/workspaceApi'

export interface WorkspaceContextValue {
  activeWorkspace: Workspace | null
  workspaces: Workspace[]
  isLoading: boolean
  error: string | null
  refreshWorkspaces: () => Promise<void>
  selectWorkspace: (workspaceId: string) => void
  createWorkspace: (name: string, description?: string) => Promise<void>
}

export const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined)

export function useWorkspace(): WorkspaceContextValue {
  const context = useContext(WorkspaceContext)

  if (!context) {
    throw new Error('useWorkspace must be used within WorkspaceProvider.')
  }

  return context
}
