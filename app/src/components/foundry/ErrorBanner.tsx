interface ErrorBannerProps {
  message: string
}

export function ErrorBanner({ message }: ErrorBannerProps) {
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
