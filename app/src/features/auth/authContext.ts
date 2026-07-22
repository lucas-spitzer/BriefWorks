import { createContext, useContext } from 'react'
import type { User } from '@supabase/supabase-js'
import type { CurrentUserResponse } from '../../lib/apiClient'

export type ApprovalStatus = 'idle' | 'checking' | 'approved' | 'rejected' | 'unavailable'

export interface AuthContextValue {
  approvalError: string | null
  approvalStatus: ApprovalStatus
  approvedUser: CurrentUserResponse | null
  isApproved: boolean
  isAuthenticated: boolean
  isLoading: boolean
  user: User | null
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider.')
  }

  return context
}
