import { NavLink, Outlet } from 'react-router-dom'
import { WorkspaceGate } from '../components/WorkspaceGate'
import { signOut } from '../features/auth/authService'
import { useAuth } from '../features/auth/authContext'
import { useWorkspace } from '../features/workspace/workspaceContext'

const navigationItems = [
  { label: 'Dashboard', path: '/app' },
  { label: 'Projects', path: '/app/projects' },
  { label: 'Sources', path: '/app/sources' },
  { label: 'Intellex', path: '/app/intellex' },
  { label: 'Mathesys', path: '/app/mathesys' },
  { label: 'QnGen', path: '/app/qngen' },
]

export function AppShell() {
  const { approvedUser, user } = useAuth()
  const { activeWorkspace, workspaces, selectWorkspace } = useWorkspace()
  const displayEmail = approvedUser?.email ?? user?.email ?? 'Approved user'

  async function handleSignOut() {
    await signOut()
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar" aria-label="BriefWorks workspace navigation">
        <div>
          <p className="eyebrow app-sidebar__eyebrow">BriefWorks</p>
          <h1>Production Studio</h1>
          <p className="app-sidebar__copy">
            Private workspace for source-grounded educational artifacts.
          </p>
        </div>

        {workspaces.length > 0 ? (
          <label className="workspace-switcher">
            <span className="workspace-switcher__label">Workspace</span>
            <select
              className="workspace-switcher__select"
              value={activeWorkspace?.id ?? ''}
              onChange={(event) => selectWorkspace(event.target.value)}
            >
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <nav className="app-nav">
          {navigationItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/app'}
              className={({ isActive }) => (isActive ? 'app-nav__link is-active' : 'app-nav__link')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="app-user-card">
          <p className="app-user-card__label">Signed in</p>
          <p className="app-user-card__email">{displayEmail}</p>
          <button type="button" className="button-secondary app-user-card__button" onClick={handleSignOut}>
            Sign Out
          </button>
        </div>
      </aside>

      <main className="app-main">
        <WorkspaceGate>
          <Outlet />
        </WorkspaceGate>
      </main>
    </div>
  )
}
