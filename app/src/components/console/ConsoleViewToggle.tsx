import type { ConsoleView } from './types'

interface ConsoleViewToggleProps {
  onChange: (view: ConsoleView) => void
  view: ConsoleView
}

export function ConsoleViewToggle({ view, onChange }: ConsoleViewToggleProps) {
  return (
    <div className="bw-console__viewtoggle">
      <button
        className={`bw-console__viewbtn${view === 'grid' ? ' is-active' : ''}`}
        onClick={() => onChange('grid')}
        aria-label="Item view"
        aria-pressed={view === 'grid'}
      >
        ▦
      </button>
      <button
        className={`bw-console__viewbtn${view === 'list' ? ' is-active' : ''}`}
        onClick={() => onChange('list')}
        aria-label="List view"
        aria-pressed={view === 'list'}
      >
        ☰
      </button>
    </div>
  )
}
