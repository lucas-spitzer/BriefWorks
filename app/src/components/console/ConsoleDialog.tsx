import { useEffect, type ReactNode } from 'react'

interface ConsoleDialogProps {
  title: string
  open: boolean
  onClose: () => void
  children: ReactNode
}

export function ConsoleDialog({ title, open, onClose, children }: ConsoleDialogProps) {
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
    <div className="bw-console__dialog-backdrop" onClick={onClose} role="presentation">
      <div
        className="bw-console__dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="bw-console-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="bw-console__dialog-head">
          <h3 id="bw-console-dialog-title">{title}</h3>
          <button type="button" className="bw-console__cta bw-console__cta--ghost" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="bw-console__dialog-body">{children}</div>
      </div>
    </div>
  )
}
