import { useWorkspace } from '../../features/workspace/workspaceContext'
import { useLibraryFocus } from '../../lib/libraryFocus'
import { DiscussionsView } from './DiscussionsView'
import { FlashcardsView } from './FlashcardsView'
import { LibraryView } from './LibraryView'
import { QuizView } from './QuizView'
import { ReaderView } from './ReaderView'
import { ScenarioView } from './ScenarioView'
import type { LearnerPage, LearnerScope } from './types'

type LearnerContentProps = {
  page: LearnerPage
  sourceId?: string | null
  seg?: number | null
  scope: LearnerScope
  onOpen: (page: LearnerPage, scope: LearnerScope) => void
}

export function LearnerContent({ page, sourceId = null, seg = null, scope, onOpen }: LearnerContentProps) {
  const { activeWorkspace } = useWorkspace()
  const { focus } = useLibraryFocus(activeWorkspace?.id ?? null)
  // With no explicit source, the reader opens the focused ebook; the demo
  // template is only shown when nothing is focused.
  const readerSourceId = sourceId ?? focus.ebookSourceId

  return (
    <div className="learner learner--integrated">
      <div className="learner__main">
        {page === 'library' && <LibraryView onOpen={onOpen} />}
        {page === 'reader' && <ReaderView sourceId={readerSourceId} seg={seg} onOpen={onOpen} />}
        {page === 'flashcards' && (
          <FlashcardsView sourceId={scope.sourceId} targetId={scope.targetId} />
        )}
        {page === 'quiz' && <QuizView sourceId={scope.sourceId} targetId={scope.targetId} />}
        {page === 'scenarios' && (
          <ScenarioView sourceId={scope.sourceId} targetId={scope.targetId} />
        )}
        {page === 'discussions' && <DiscussionsView sourceId={scope.sourceId} />}
      </div>
    </div>
  )
}
