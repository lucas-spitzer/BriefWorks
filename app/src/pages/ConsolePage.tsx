import { ConsoleShell } from '../components/console/ConsoleShell'
import { WorkspaceGate } from '../components/WorkspaceGate'
import { WorkspaceDataProvider } from '../features/workspace/WorkspaceDataProvider'
import '../console.css'
import '../learner.css'

export function ConsolePage() {
  return (
    <div className="bw-gallery bw-gallery--full">
      <WorkspaceGate>
        <WorkspaceDataProvider>
          <ConsoleShell />
        </WorkspaceDataProvider>
      </WorkspaceGate>
    </div>
  )
}
