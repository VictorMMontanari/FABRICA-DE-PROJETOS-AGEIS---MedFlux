import { MapPinned, PhoneCall, ShieldAlert } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { TriageRecommendation, UnitLevel } from '../services/api'

type TriageResultCardProps = {
  recommendation: TriageRecommendation
}

const ESTIMATE_LABEL: Record<UnitLevel, string> = {
  EMERGENCIA: 'Atendimento imediato',
  UPA: 'Estimativa: atendimento hoje',
  UBS: 'Estimativa: acompanhamento em breve',
}

// Em emergência o mapa mostra as UPAs (mesma regra do backend em /api/health/units)
const MAP_LABEL: Record<UnitLevel, string> = {
  EMERGENCIA: 'UPAs próximas',
  UPA: 'Localização UPA',
  UBS: 'Localização UBS',
}

export function TriageResultCard({ recommendation }: TriageResultCardProps) {
  const navigate = useNavigate()
  const level = recommendation.unit_type
  const isEmergency = level === 'EMERGENCIA'
  const isCritical = isEmergency || level === 'UPA'

  return (
    <div
      className={`triage-card${isCritical ? ' triage-card--critical' : ''}${isEmergency ? ' triage-card--emergency' : ''}`}
    >
      <div
        className={`triage-card__badge${isCritical ? ' triage-card__badge--critical' : ' triage-card__badge--routine'}`}
      >
        {recommendation.urgency_label}
        <span>{ESTIMATE_LABEL[level] ?? ''}</span>
      </div>
      <h3 className="triage-card__title">{recommendation.title}</h3>
      <p className="triage-card__description">{recommendation.description}</p>
      <div className="triage-card__warning">
        <ShieldAlert size={16} style={{ display: 'inline', marginRight: 8 }} />
        {recommendation.warning}
      </div>
      <div className="triage-card__action">
        {isEmergency ? (
          <a className="triage-card__button triage-card__button--emergency" href="tel:192">
            <PhoneCall size={16} />
            Ligar 192 (SAMU)
          </a>
        ) : null}
        <button
          type="button"
          className="triage-card__button"
          onClick={() => navigate(`/map?type=${level}`)}
        >
          <MapPinned size={16} />
          {MAP_LABEL[level] ?? 'Ver no mapa'}
        </button>
      </div>
    </div>
  )
}