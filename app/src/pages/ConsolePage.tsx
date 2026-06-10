import { ConsoleShell } from '../components/console/ConsoleShell'
import { WorkspaceGate } from '../components/WorkspaceGate'
import '../console.css'

export function ConsolePage() {
  return (
    <div className="bw-gallery bw-gallery--full">
      <WorkspaceGate>
        <ConsoleShell />
      </WorkspaceGate>
    </div>
  )
}
