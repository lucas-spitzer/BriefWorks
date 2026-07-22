import { LogOut } from 'lucide-react'
import { useState } from 'react'
import { matchPath, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { LearnerContent } from '../learner/LearnerContent'
import {
  emptyLearnerScope,
  learnerRailItems,
  type LearnerPage,
  type LearnerScope,
} from '../learner/types'
import { signOut } from '../../features/auth/authService'
import { useAuth } from '../../features/auth/authContext'
import { ConsoleArtifacts } from './ConsoleArtifacts'
import { ConsoleAssessments } from './ConsoleAssessments'
import { ConsoleOps } from './ConsoleOps'
import { ConsoleStages } from './ConsoleStages'
import { ConsoleSources } from './ConsoleSources'
import { ConsoleStageSettings } from './ConsoleStageSettings'
import { ConsoleWiki } from './ConsoleWiki'
import { ConsoleWorkspaces } from './ConsoleWorkspaces'
import { railIconSize, railItems, type ConsolePage } from './types'

type AppMode = 'console' | 'learner'

export function ConsoleShell() {
  const [mode, setMode] = useState<AppMode>('console')
  const [consolePage, setConsolePage] = useState<ConsolePage>('ops')
  const [learnerPage, setLearnerPage] = useState<LearnerPage>('library')
  const [learnerScope, setLearnerScope] = useState<LearnerScope>(emptyLearnerScope)
  const { approvedUser, user } = useAuth()
  const displayEmail = approvedUser?.email ?? user?.email ?? 'Signed in'

  // Reader is the one URL-addressable screen: /app/reader/:sourceId?seg=N.
  // When that route is active it overrides the state-driven tabs.
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const readerMatch = matchPath('/app/reader/:sourceId', location.pathname)
  const routedSourceId = readerMatch?.params.sourceId ?? null
  const segParam = searchParams.get('seg')
  const parsedSeg = segParam != null && segParam !== '' ? Number.parseInt(segParam, 10) : NaN
  const seg = Number.isFinite(parsedSeg) ? parsedSeg : null

  const isLearner = routedSourceId ? true : mode === 'learner'
  const activeLearnerPage: LearnerPage = routedSourceId ? 'reader' : learnerPage
  const navItems = isLearner ? learnerRailItems : railItems
  const activePage = isLearner ? activeLearnerPage : consolePage

  const toggleMode = () => {
    if (routedSourceId) {
      navigate('/app', { replace: true })
      setMode('console')
      return
    }
    setMode((m) => (m === 'console' ? 'learner' : 'console'))
  }

  const setPage = (id: string) => {
    if (routedSourceId) {
      navigate('/app', { replace: true })
      setMode('learner')
    }
    if (isLearner) {
      setLearnerScope(emptyLearnerScope) // rail navigation clears any open-from-Library scope
      setLearnerPage(id as LearnerPage)
    } else {
      setConsolePage(id as ConsolePage)
    }
  }

  // Open a runner from the Library, carrying a source filter + focus target.
  const openLearner = (page: LearnerPage, scope: LearnerScope) => {
    if (routedSourceId) navigate('/app', { replace: true })
    setMode('learner')
    setLearnerScope(scope)
    setLearnerPage(page)
  }

  return (
    <div className={`bw-console${isLearner ? ' bw-console--learner' : ''}`}>
      <nav
        className="bw-console__rail"
        aria-label={isLearner ? 'BriefWorks learner navigation' : 'BriefWorks console navigation'}
      >
        <button
          type="button"
          className={`bw-console__rail-mark${isLearner ? ' is-learner' : ''}`}
          onClick={toggleMode}
          title={isLearner ? 'Switch to BriefWorks console' : 'Switch to BriefWorks Learner'}
          aria-label={isLearner ? 'BriefWorks Learner — switch to console' : 'BriefWorks — switch to learner'}
        >
          {isLearner ? 'BL' : 'BW'}
        </button>
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.id}
              className={`bw-console__rail-btn${activePage === item.id ? ' is-active' : ''}`}
              onClick={() => setPage(item.id)}
              aria-current={activePage === item.id ? 'page' : undefined}
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
        {isLearner ? (
          <LearnerContent
            page={activeLearnerPage}
            sourceId={routedSourceId}
            seg={seg}
            scope={learnerScope}
            onOpen={openLearner}
          />
        ) : (
          <>
            {consolePage === 'ops' ? <ConsoleOps onGoToSources={() => setConsolePage('sources')} /> : null}
            {consolePage === 'sources' ? <ConsoleSources /> : null}
            {consolePage === 'stages' ? <ConsoleStages /> : null}
            {consolePage === 'artifacts' ? <ConsoleArtifacts /> : null}
            {consolePage === 'wiki' ? <ConsoleWiki /> : null}
            {consolePage === 'assessments' ? <ConsoleAssessments onOpen={openLearner} /> : null}
            {consolePage === 'workspace' ? <ConsoleWorkspaces /> : null}
            {consolePage === 'settings' ? <ConsoleStageSettings /> : null}
          </>
        )}
      </div>
    </div>
  )
}
