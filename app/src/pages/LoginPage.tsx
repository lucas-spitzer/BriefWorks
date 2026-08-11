import { useState, type CSSProperties } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { signInWithGoogle, signOut } from '../features/auth/authService'
import { useAuth } from '../features/auth/authContext'
import '../gate.css'

interface LocationState {
  from?: {
    pathname?: string
  }
}

const systemModules = [
  {
    name: 'Intellex',
    tag: 'Knowledge Base',
    description:
      'Ingests and deconstructs source documents into a structured, source-grounded knowledge base.',
  },
  {
    name: 'Mathesys',
    tag: 'Generation',
    description:
      'Produces narration scripts, audio, and educational artifacts from Intellex output.',
  },
  {
    name: 'QnGen',
    tag: 'Assessment',
    description:
      'Builds flashcard, question, and scenario sets that test every production run.',
  },
]

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
      console.error(
        'Unable to start Google login:',
        error instanceof Error ? error.message : error,
      )
      setErrorMessage('Unable to start Google login. Try again.')
      setIsSubmitting(false)
    }
  }

  async function handleSignOut() {
    await signOut()
  }

  return (
    <main className="as-gate">
      <div className="as-gate__login">
        <section className="as-gate__brand" aria-label="About Arsenal">
          <div className="as-gate__brand-head">
            <div className="as-gate__mark">AS</div>
            <div>
              <div className="as-gate__wordmark">Arsenal</div>
              <div className="as-gate__tagline">Private Educational Production Studio</div>
            </div>
          </div>

          <ol className="as-gate__modules">
            {systemModules.map((module, index) => (
              <li
                key={module.name}
                className="as-gate__module"
                style={{ '--i': index } as CSSProperties}
              >
                <span className="as-gate__module-dot">{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <div className="as-gate__module-name">
                    {module.name}
                    <span className="as-gate__module-tag">{module.tag}</span>
                  </div>
                  <p>{module.description}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="as-gate__sysline">
            <span className="as-gate__livedot" aria-hidden="true" />
            Systems nominal · Intellex / Mathesys / QnGen
          </div>
        </section>

        <section className="as-gate__panel" aria-labelledby="auth-title">
          <p className="as-gate__eyebrow">Access Restricted</p>
          <h1 id="auth-title">Operator Sign-In</h1>
          <p className="as-gate__copy">
            Arsenal is a private production environment. Access is restricted to approved
            accounts.
          </p>

          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isSubmitting || isLoading}
            className="as-gate__cta"
          >
            {isSubmitting ? 'Redirecting…' : 'Continue with Google'}
          </button>

          <p className="as-gate__helper">Only approved Google accounts may access Arsenal.</p>

          {approvalStatus === 'rejected' ? (
            <div className="as-gate__error" role="alert">
              <p>{approvalError ?? 'This Google account is not approved for Arsenal access.'}</p>
              <button type="button" className="as-gate__inline-action" onClick={handleSignOut}>
                Sign out
              </button>
            </div>
          ) : null}

          {errorMessage ? (
            <div className="as-gate__error" role="alert">
              <p>{errorMessage}</p>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  )
}
