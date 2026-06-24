import { LogOut } from 'lucide-react'
import { useState } from 'react'
import { signOut } from '../../features/auth/authService'
import { useAuth } from '../../features/auth/authContext'
import { ConsoleArtifacts } from './ConsoleArtifacts'
import { ConsoleAssessments } from './ConsoleAssessments'
import { ConsoleOps } from './ConsoleOps'
import { ConsoleStages } from './ConsoleStages'
import { ConsoleSources } from './ConsoleSources'
import { ConsoleStageSettings } from './ConsoleStageSettings'
import { ConsoleWorkspaces } from './ConsoleWorkspaces'
import { railIconSize, railItems, type ConsolePage } from './types'

export function ConsoleShell() {
  const [page, setPage] = useState<ConsolePage>('ops')
  const { approvedUser, user } = useAuth()
  const displayEmail = approvedUser?.email ?? user?.email ?? 'Signed in'

  return (
    <div className="bw-console">
      <nav className="bw-console__rail" aria-label="BriefWorks console navigation">
        <div className="bw-console__rail-mark">BW</div>
        {railItems.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.id}
              className={`bw-console__rail-btn${page === item.id ? ' is-active' : ''}`}
              onClick={() => setPage(item.id)}
              aria-current={page === item.id ? 'page' : undefined}
            >
              <Icon className="bw-console__rail-icon" size={railIconSize} strokeWidth={1.75} aria-hidden />
              {item.label}
            </button>
          )
        })}

        <div className="bw-console__rail-foot">
          <button
            type="button"
            className="bw-console__rail-btn bw-console__rail-btn--account"
            onClick={() => void signOut()}
            title={`Sign out (${displayEmail})`}
          >
            <LogOut className="bw-console__rail-icon" size={railIconSize} strokeWidth={1.75} aria-hidden />
            OUT
          </button>
        </div>
      </nav>

      <div className="bw-console__main">
        {page === 'ops' ? <ConsoleOps onGoToSources={() => setPage('sources')} /> : null}
        {page === 'sources' ? <ConsoleSources /> : null}
        {page === 'stages' ? <ConsoleStages onGoToOps={() => setPage('ops')} /> : null}
        {page === 'artifacts' ? <ConsoleArtifacts /> : null}
        {page === 'assessments' ? <ConsoleAssessments /> : null}
        {page === 'workspace' ? <ConsoleWorkspaces /> : null}
        {page === 'settings' ? <ConsoleStageSettings /> : null}
      </div>
    </div>
  )
}
