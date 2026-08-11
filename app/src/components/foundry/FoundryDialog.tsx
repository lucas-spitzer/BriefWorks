import { useEffect, type ReactNode } from 'react'

interface FoundryDialogProps {
  title: string
  open: boolean
  onClose: () => void
  children: ReactNode
}

export function FoundryDialog({ title, open, onClose, children }: FoundryDialogProps) {
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="as-console__dialog-backdrop" onClick={onClose} role="presentation">
      <div
        className="as-console__dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="as-console-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="as-console__dialog-head">
          <h3 id="as-console-dialog-title">{title}</h3>
          <button type="button" className="as-console__cta as-console__cta--ghost" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="as-console__dialog-body">{children}</div>
      </div>
    </div>
  )
}
