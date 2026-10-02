import { HeartPulse } from 'lucide-react'

type BrandMarkProps = {
  compact?: boolean
}

export function BrandMark({ compact = false }: BrandMarkProps) {
  return (
    <div className="brand-mark">
      <div className="brand-mark__icon">
        <HeartPulse size={compact ? 18 : 20} strokeWidth={2.3} />
      </div>
      <div className="brand-mark__title">
        <strong>MedFlux</strong>
        <span>Health &amp; Wellness</span>
      </div>
    </div>
  )
}