import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { signOut } from './authService'
import { useAuth } from './authContext'
import '../../gate.css'

function SecurityCheckStatus({ message }: { message: string }) {
  return (
    <main className="bw-gate" aria-live="polite">
      <section className="bw-gate__status">
        <div className="bw-gate__mark">BW</div>
        <p className="bw-gate__eyebrow">Security Check</p>
        <p className="bw-gate__status-msg">{message}</p>
        <div className="bw-gate__scanner" aria-hidden="true" />
      </section>
    </main>
  )
}

function AccessNotice({ title, message }: { title: string; message: string }) {
  async function handleSignOut() {
    await signOut()
  }

  return (
    <main className="bw-gate">
      <section
        className="bw-gate__status bw-gate__status--alert"
        role="alert"
        aria-labelledby="access-notice-title"
      >
        <div className="bw-gate__mark">BW</div>
        <p className="bw-gate__eyebrow">Access Restricted</p>
        <p className="bw-gate__status-msg" id="access-notice-title">
          {title}
        </p>
        <p className="bw-gate__copy">{message}</p>
        <button type="button" className="bw-gate__cta" onClick={() => void handleSignOut()}>
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
    return <SecurityCheckStatus message="Verifying your BriefWorks session." />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (approvalStatus === 'rejected') {
    return (
      <AccessNotice
        title="Account Not Approved"
        message={approvalError ?? 'This Google account is not approved for BriefWorks access.'}
      />
    )
  }

  if (approvalStatus === 'unavailable') {
    return (
      <AccessNotice
        title="Approval Service Unavailable"
        message={approvalError ?? 'BriefWorks could not complete the approval check.'}
      />
    )
  }

  if (approvalStatus !== 'approved') {
    return <SecurityCheckStatus message="Preparing the protected workspace." />
  }

  return <Outlet />
}
