import { MapPinned, ShieldAlert } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { TriageRecommendation } from '../services/api'

type TriageResultCardProps = {
  recommendation: TriageRecommendation
}

function getEstimateLabel(unitType: TriageRecommendation['unit_type']) {
  return unitType === 'UPA' ? 'Estimativa: atendimento hoje' : 'Estimativa: acompanhamento em breve'
}

export function TriageResultCard({ recommendation }: TriageResultCardProps) {
  const navigate = useNavigate()
  const isCritical = recommendation.unit_type === 'UPA'

  return (
    <div className={`triage-card${isCritical ? ' triage-card--critical' : ''}`}>
      <div
        className={`triage-card__badge${isCritical ? ' triage-card__badge--critical' : ' triage-card__badge--routine'}`}
      >
        {recommendation.urgency_label}
        <span>{getEstimateLabel(recommendation.unit_type)}</span>
      </div>
      <h3 className="triage-card__title">{recommendation.title}</h3>
      <p className="triage-card__description">{recommendation.description}</p>
      <div className="triage-card__warning">
        <ShieldAlert size={16} style={{ display: 'inline', marginRight: 8 }} />
        {recommendation.warning}
      </div>
      <div className="triage-card__action">
        <button
          type="button"
          className="triage-card__button"
          onClick={() => navigate(`/map?type=${recommendation.unit_type}`)}
        >
          <MapPinned size={16} />
          Localização {recommendation.unit_type}
        </button>
      </div>
    </div>
  )
}