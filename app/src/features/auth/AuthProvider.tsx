import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { ApiError, getCurrentUser, hasApiBaseUrl } from '../../lib/apiClient'
import type { CurrentUserResponse } from '../../lib/apiClient'
import { supabase } from '../../lib/supabaseClient'
import { AuthContext } from './authContext'
import type { ApprovalStatus, AuthContextValue } from './authContext'

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [session, setSession] = useState<Session | null>(null)
  const [isSessionLoading, setIsSessionLoading] = useState(true)
  const [approvalStatus, setApprovalStatus] = useState<ApprovalStatus>('idle')
  const [approvalError, setApprovalError] = useState<string | null>(null)
  const [approvedUser, setApprovedUser] = useState<CurrentUserResponse | null>(null)

  useEffect(() => {
    let isMounted = true

    supabase.auth.getSession().then(({ data, error }) => {
      if (!isMounted) return

      if (error) {
        console.error('Failed to load Supabase session:', error.message)
      }

      setSession(data.session ?? null)
      setIsSessionLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setIsSessionLoading(false)
    })

    return () => {
      isMounted = false
      listener.subscription.unsubscribe()
    }
  }, [])

  useEffect(() => {
    let isCurrent = true

    async function verifyApproval() {
      setApprovedUser(null)
      setApprovalError(null)

      if (!session) {
        setApprovalStatus('idle')
        return
      }

      if (!hasApiBaseUrl()) {
        setApprovalStatus('unavailable')
        setApprovalError('Set VITE_API_BASE_URL to enable the BriefWorks approval check.')
        return
      }

      setApprovalStatus('checking')

      try {
        const currentUser = await getCurrentUser()

        if (!isCurrent) return

        setApprovedUser(currentUser)
        setApprovalStatus('approved')
      } catch (error) {
        if (!isCurrent) return

        if (error instanceof ApiError && error.status === 403) {
          setApprovalStatus('rejected')
          setApprovalError('This Google account is not approved for BriefWorks access.')
          return
        }

        if (error instanceof ApiError && error.status === 401) {
          setApprovalStatus('rejected')
          setApprovalError('Your session could not be verified. Sign in again.')
          return
        }

        console.error(
          'BriefWorks approval check failed:',
          error instanceof Error ? error.message : error,
        )
        setApprovalStatus('unavailable')
        setApprovalError('BriefWorks could not reach the approval service.')
      }
    }

    void verifyApproval()

    return () => {
      isCurrent = false
    }
  }, [session])

  const value = useMemo<AuthContextValue>(() => {
    return {
      approvalError,
      approvalStatus,
      approvedUser,
      isApproved: approvalStatus === 'approved',
      isAuthenticated: Boolean(session),
      isLoading: isSessionLoading || approvalStatus === 'checking',
      user: session?.user ?? null,
    }
  }, [approvalError, approvalStatus, approvedUser, isSessionLoading, session])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
