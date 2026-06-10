import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { signInWithGoogle, signOut } from '../features/auth/authService'
import { useAuth } from '../features/auth/authContext'

interface LocationState {
  from?: {
    pathname?: string
  }
}

export function LoginPage() {
  const location = useLocation()
  const { approvalError, approvalStatus, isAuthenticated, isLoading } = useAuth()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const fromPath = (location.state as LocationState | null)?.from?.pathname ?? '/app'

  if (!isLoading && isAuthenticated && approvalStatus !== 'rejected') {
    return <Navigate to={fromPath} replace />
  }

  async function handleGoogleLogin() {
    try {
      setIsSubmitting(true)
      setErrorMessage(null)
      await signInWithGoogle()
    } catch (error) {
      console.error(error)
      setErrorMessage('Unable to start Google login. Try again.')
      setIsSubmitting(false)
    }
  }

  async function handleSignOut() {
    await signOut()
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <p className="eyebrow">Access Restricted</p>
        <h1 id="auth-title">BriefWorks</h1>
        <p className="auth-copy">
          Private educational production studio. Access is restricted to approved accounts.
        </p>

        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={isSubmitting || isLoading}
          className="button-primary auth-primary-button"
        >
          {isSubmitting ? 'Redirecting...' : 'Continue with Google'}
        </button>

        <p className="auth-helper">Only approved Google accounts may access BriefWorks.</p>

        {approvalStatus === 'rejected' ? (
          <div className="auth-error" role="alert">
            <p>{approvalError ?? 'This Google account is not approved for BriefWorks access.'}</p>
            <button type="button" className="auth-inline-action" onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        ) : null}

        {errorMessage ? (
          <p className="auth-error" role="alert">
            {errorMessage}
          </p>
        ) : null}
      </section>
    </main>
  )
}
