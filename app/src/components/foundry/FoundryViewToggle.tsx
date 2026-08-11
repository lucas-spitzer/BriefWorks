import type { FoundryView } from './types'

interface FoundryViewToggleProps {
  onChange: (view: FoundryView) => void
  view: FoundryView
}

export function FoundryViewToggle({ view, onChange }: FoundryViewToggleProps) {
  return (
    <div className="as-console__viewtoggle">
      <button
        className={`as-console__viewbtn${view === 'grid' ? ' is-active' : ''}`}
        onClick={() => onChange('grid')}
        aria-label="Item view"
        aria-pressed={view === 'grid'}
      >
        ▦
      </button>
      <button
        className={`as-console__viewbtn${view === 'list' ? ' is-active' : ''}`}
        onClick={() => onChange('list')}
        aria-label="List view"
        aria-pressed={view === 'list'}
      >
        ☰
      </button>
    </div>
  )
}
