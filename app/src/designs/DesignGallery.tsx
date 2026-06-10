import { useState } from 'react'
import './designs.css'
import { ConsoleVariant } from './variants/ConsoleVariant'
import { DriveVariant } from './variants/DriveVariant'
import { EditorialVariant } from './variants/EditorialVariant'

type Variant = 'drive' | 'console' | 'editorial'

const variants: { id: Variant; label: string; hint: string }[] = [
  { id: 'drive', label: 'Drive', hint: 'File explorer' },
  { id: 'console', label: 'Console', hint: 'Mission control' },
  { id: 'editorial', label: 'Editorial', hint: 'The brief' },
]

export function DesignGallery() {
  const [variant, setVariant] = useState<Variant>('drive')

  return (
    <div className="bw-gallery">
      <header className="bw-switcher">
        <div className="bw-switcher__brand">
          BriefWorks <small>Design Studies</small>
        </div>
        <div className="bw-switcher__tabs">
          {variants.map((item) => (
            <button
              key={item.id}
              className={`bw-switcher__tab${variant === item.id ? ' is-active' : ''}`}
              onClick={() => setVariant(item.id)}
              title={item.hint}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>

      <div className="bw-stage">
        {variant === 'drive' ? <DriveVariant /> : null}
        {variant === 'console' ? <ConsoleVariant /> : null}
        {variant === 'editorial' ? <EditorialVariant /> : null}
      </div>
    </div>
  )
}
