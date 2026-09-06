import { Minus } from 'lucide-react'

interface ErrorBannerProps {
  message: string
  onDismiss?: () => void
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  if (!onDismiss) {
    return (
      <div
        className="as-console__chip"
        style={{
          borderColor: 'var(--color-scarlet)',
          color: '#ff8b8b',
          background: 'rgba(148,0,0,0.16)',
          marginBottom: 'var(--space-5)',
        }}
      >
        ⚠ {message}
      </div>
    )
  }

  return (
    <div className="as-console__log">
      <p className="as-console__log-body">⚠ {message}</p>
      <button
        type="button"
        className="as-console__log-dismiss"
        aria-label="Dismiss logs"
        onClick={onDismiss}
      >
        <Minus size={14} strokeWidth={2} />
      </button>
    </div>
  )
}
