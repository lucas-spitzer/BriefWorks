type ArsenalMarkProps = {
  className?: string
  title?: string
}

/** Arsenal brand mark — gold-on-scarlet three-cartridge art (`public/arsenal-mark.svg`). */
export function ArsenalMark({ className, title = 'Arsenal' }: ArsenalMarkProps) {
  return <img className={className} src="/arsenal-mark.svg" alt={title} width={44} height={44} />
}
