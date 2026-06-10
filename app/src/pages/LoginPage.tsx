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
      console.error(error)
      setErrorMessage('Unable to start Google login. Try again.')
      setIsSubmitting(false)
    }
  }

  async function handleSignOut() {
    await signOut()
  }

  return (
    <main className="bw-gate">
      <div className="bw-gate__login">
        <section className="bw-gate__brand" aria-label="About BriefWorks">
          <div className="bw-gate__brand-head">
            <div className="bw-gate__mark">BW</div>
            <div>
              <div className="bw-gate__wordmark">BriefWorks</div>
              <div className="bw-gate__tagline">Private Educational Production Studio</div>
            </div>
          </div>

          <ol className="bw-gate__modules">
            {systemModules.map((module, index) => (
              <li
                key={module.name}
                className="bw-gate__module"
                style={{ '--i': index } as CSSProperties}
              >
                <span className="bw-gate__module-dot">{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <div className="bw-gate__module-name">
                    {module.name}
                    <span className="bw-gate__module-tag">{module.tag}</span>
                  </div>
                  <p>{module.description}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="bw-gate__sysline">
            <span className="bw-gate__livedot" aria-hidden="true" />
            Systems nominal · Intellex / Mathesys / QnGen
          </div>
        </section>

        <section className="bw-gate__panel" aria-labelledby="auth-title">
          <p className="bw-gate__eyebrow">Access Restricted</p>
          <h1 id="auth-title">Operator Sign-In</h1>
          <p className="bw-gate__copy">
            BriefWorks is a private production environment. Access is restricted to approved
            accounts.
          </p>

          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={isSubmitting || isLoading}
            className="bw-gate__cta"
          >
            {isSubmitting ? 'Redirecting…' : 'Continue with Google'}
          </button>

          <p className="bw-gate__helper">Only approved Google accounts may access BriefWorks.</p>

          {approvalStatus === 'rejected' ? (
            <div className="bw-gate__error" role="alert">
              <p>{approvalError ?? 'This Google account is not approved for BriefWorks access.'}</p>
              <button type="button" className="bw-gate__inline-action" onClick={handleSignOut}>
                Sign out
              </button>
            </div>
          ) : null}

          {errorMessage ? (
            <div className="bw-gate__error" role="alert">
              <p>{errorMessage}</p>
            </div>
          ) : null}
        </section>
      </div>
    </main>
  )
}
