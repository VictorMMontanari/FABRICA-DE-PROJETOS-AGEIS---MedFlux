import { ArrowRight, BrainCircuit, MapPinned, Stethoscope } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getTriageHistory, type TriageHistoryItem } from '../services/api'
import { getStoredSession } from '../services/session'

export function DashboardPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [history, setHistory] = useState<TriageHistoryItem[]>([])
  const firstName = getStoredSession()?.user.name.split(' ')[0] ?? ''

  useEffect(() => {
    let isMounted = true

    getTriageHistory().then((items) => {
      if (isMounted) {
        setHistory(items)
      }
    })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (!location.hash) {
      return
    }

    const target = document.querySelector(location.hash)
    if (target instanceof HTMLElement) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [location.hash])

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero">
        <div>
          <h1>Olá, {firstName} 👋</h1>
          <p>Boas-vindas ao MedFlux, escolha a opção que deseja.</p>
        </div>
      </section>

      <section className="section-grid">
        <article className="page-card dashboard-card dashboard-card--accent">
          <div className="map-thumb">
            <div className="map-thumb__pin map-thumb__pin--1" />
            <div className="map-thumb__pin map-thumb__pin--2" />
            <div className="map-thumb__pin map-thumb__pin--3" />
          </div>
          <div className="dashboard-card__eyebrow">
            <MapPinned size={14} />
            Mapa Interativo
          </div>
          <p className="dashboard-card__meta">• 12 clínicas próximas abertas</p>
          <h2 className="dashboard-card__title">Explore nosso mapa com as clínicas mais próximas</h2>
          <p className="dashboard-card__description">
            Veja unidades de saúde, locais de atenção básica e pontos de atendimento de urgência em um mapa pronto para uso.
          </p>
          <div className="dashboard-card__footer">
            <button type="button" className="primary-button" onClick={() => navigate('/map')}>
              Explore as clínicas mais próximas
            </button>
          </div>
        </article>

        <article className="page-card dashboard-card dashboard-card--accent">
          <div className="assistant-portrait">
            <div className="assistant-portrait__bubble assistant-portrait__bubble--one">Estou online</div>
            <div className="assistant-portrait__bubble assistant-portrait__bubble--two">Triagem inteligente</div>
            <div className="assistant-portrait__bubble assistant-portrait__bubble--three">Cuide-se com segurança</div>
            <div className="assistant-portrait__face">
              <div className="assistant-portrait__hair" />
            </div>
          </div>
          <div className="dashboard-card__eyebrow">
            <BrainCircuit size={14} />
            Assistente de Saúde
          </div>
          <p className="dashboard-card__meta">• Online para ajudar</p>
          <h2 className="dashboard-card__title">Consulte com a Clara, sua assistente de saúde</h2>
          <p className="dashboard-card__description">
            Converse sobre sintomas, receba orientação inicial e encaminhamento sugerido com base na triagem inteligente.
          </p>
          <div className="dashboard-card__footer">
            <button type="button" className="primary-button" onClick={() => navigate('/chat')}>
              Iniciar Conversa
            </button>
          </div>
        </article>
      </section>

      <section className="section-title-row" id="my-health">
        <div>
          <h2 className="section-title">Minha Saúde</h2>
          <p className="section-subtitle">Resumo rápido dos seus indicadores recentes e acompanhamento.</p>
        </div>
      </section>

      <section className="health-strip">
        <div className="mini-stat page-card">
          <Stethoscope size={18} color="#1a6b82" />
          <strong>Triagem ativa</strong>
          <span>Você pode continuar a conversa a qualquer momento.</span>
        </div>
        <div className="mini-stat page-card">
          <MapPinned size={18} color="#1a6b82" />
          <strong>Clínicas próximas</strong>
          <span>Mapa com unidades em Marília e arredores.</span>
        </div>
        <div className="mini-stat page-card">
          <BrainCircuit size={18} color="#1a6b82" />
          <strong>IA Clara</strong>
          <span>Assistente disponível para triagem e orientação.</span>
        </div>
      </section>

      <section className="section-title-row" id="history">
        <div>
          <h2 className="section-title">Consultas Recentes</h2>
          <p className="section-subtitle">Histórico recente de triagens e orientações.</p>
        </div>
      </section>

      <section className="page-card dashboard-card">
        <div className="history-list">
          {history.map((item) => (
            <article key={item.id} className="history-item">
              <div className="history-item__meta">
                <strong>{item.title}</strong>
                <p>{item.description}</p>
              </div>
              <button type="button" className="primary-button history-item__action" onClick={() => navigate(item.route)}>
                Continuar sua conversa <ArrowRight size={16} />
              </button>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}