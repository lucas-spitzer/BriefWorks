import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { ArsenalMark } from '../../components/brand/ArsenalMark'
import { signOut } from './authService'
import { useAuth } from './authContext'
import '../../gate.css'

function SecurityCheckStatus({ message }: { message: string }) {
  return (
    <main className="as-gate" aria-live="polite">
      <section className="as-gate__status">
        <ArsenalMark className="as-gate__mark" />
        <p className="as-gate__eyebrow">Security Check</p>
        <p className="as-gate__status-msg">{message}</p>
        <div className="as-gate__scanner" aria-hidden="true" />
      </section>
    </main>
  )
}

function AccessNotice({ title, message }: { title: string; message: string }) {
  async function handleSignOut() {
    await signOut()
  }

  return (
    <main className="as-gate">
      <section
        className="as-gate__status as-gate__status--alert"
        role="alert"
        aria-labelledby="access-notice-title"
      >
        <ArsenalMark className="as-gate__mark" />
        <p className="as-gate__eyebrow">Access Restricted</p>
        <p className="as-gate__status-msg" id="access-notice-title">
          {title}
        </p>
        <p className="as-gate__copy">{message}</p>
        <button type="button" className="as-gate__cta" onClick={() => void handleSignOut()}>
          Sign Out
        </button>
      </section>
    </main>
  )
}

export function ProtectedRoute() {
  const { approvalError, approvalStatus, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <SecurityCheckStatus message="Verifying your Arsenal session." />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (approvalStatus === 'rejected') {
    return (
      <AccessNotice
        title="Account Not Approved"
        message={approvalError ?? 'This Google account is not approved for Arsenal access.'}
      />
    )
  }

  if (approvalStatus === 'unavailable') {
    return (
      <AccessNotice
        title="Approval Service Unavailable"
        message={approvalError ?? 'Arsenal could not complete the approval check.'}
      />
    )
  }

  if (approvalStatus !== 'approved') {
    return <SecurityCheckStatus message="Preparing the protected workspace." />
  }

  return <Outlet />
}
