import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  createWorkspace as createWorkspaceRequest,
  listWorkspaces,
  type Workspace,
} from '../../lib/workspaceApi'
import { useAuth } from '../auth/authContext'
import { WorkspaceContext } from './workspaceContext'

const STORAGE_KEY = 'arsenal.activeWorkspaceId'

interface WorkspaceProviderProps {
  children: ReactNode
}

export function WorkspaceProvider({ children }: WorkspaceProviderProps) {
  const { isApproved } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(
    () => localStorage.getItem(STORAGE_KEY),
  )
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshWorkspaces = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const rows = await listWorkspaces()
      setWorkspaces(rows)

      if (!rows.length) {
        setActiveWorkspaceId(null)
        localStorage.removeItem(STORAGE_KEY)
        return
      }

      const storedId = localStorage.getItem(STORAGE_KEY)
      const nextId = rows.some((row) => row.id === storedId) ? storedId : rows[0].id

      if (nextId) {
        setActiveWorkspaceId(nextId)
        localStorage.setItem(STORAGE_KEY, nextId)
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load workspaces.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isApproved) {
      setWorkspaces([])
      setActiveWorkspaceId(null)
      setIsLoading(false)
      return
    }

    void refreshWorkspaces()
  }, [isApproved, refreshWorkspaces])

  const selectWorkspace = useCallback((workspaceId: string) => {
    setActiveWorkspaceId(workspaceId)
    localStorage.setItem(STORAGE_KEY, workspaceId)
  }, [])

  const createWorkspace = useCallback(
    async (name: string, description?: string) => {
      const workspace = await createWorkspaceRequest(name, description)
      await refreshWorkspaces()
      selectWorkspace(workspace.id)
    },
    [refreshWorkspaces, selectWorkspace],
  )

  const activeWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.id === activeWorkspaceId) ?? null,
    [workspaces, activeWorkspaceId],
  )

  const value = useMemo(
    () => ({
      activeWorkspace,
      workspaces,
      isLoading,
      error,
      refreshWorkspaces,
      selectWorkspace,
      createWorkspace,
    }),
    [activeWorkspace, workspaces, isLoading, error, refreshWorkspaces, selectWorkspace, createWorkspace],
  )

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
}
