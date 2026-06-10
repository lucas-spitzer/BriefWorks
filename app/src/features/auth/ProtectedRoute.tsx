import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { signOut } from './authService'
import { useAuth } from './authContext'

function FullScreenStatus({ message }: { message: string }) {
  return (
    <main className="status-page" aria-live="polite">
      <section className="status-card">
        <p className="eyebrow">BriefWorks</p>
        <h1>Checking Access</h1>
        <p>{message}</p>
      </section>
    </main>
  )
}

function AccessNotice({ title, message }: { title: string; message: string }) {
  async function handleSignOut() {
    await signOut()
  }

  return (
    <main className="status-page">
      <section className="status-card status-card--alert" aria-labelledby="access-notice-title">
        <p className="eyebrow">Access Restricted</p>
        <h1 id="access-notice-title">{title}</h1>
        <p>{message}</p>
        <button type="button" className="button-secondary" onClick={handleSignOut}>
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
    return <FullScreenStatus message="Verifying your BriefWorks session." />
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
    return <FullScreenStatus message="Preparing the protected workspace." />
  }

  return <Outlet />
}
