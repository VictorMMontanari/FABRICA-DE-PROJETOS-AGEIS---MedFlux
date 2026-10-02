import { divIcon } from 'leaflet'
import type { DivIcon } from 'leaflet'
import { useEffect, useState } from 'react'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { useSearchParams } from 'react-router-dom'
import { getHealthUnits, type HealthUnit } from '../services/api'

const USER_LOCATION: [number, number] = [-22.2184, -49.9506]

function createPinIcon(color: string): DivIcon {
  return divIcon({
    className: 'medflux-pin',
    iconSize: [28, 38],
    iconAnchor: [14, 36],
    popupAnchor: [0, -34],
    html: `
      <div style="width:28px;height:38px;display:grid;place-items:center;filter:drop-shadow(0 10px 16px rgba(15,23,42,.18));">
        <svg viewBox="0 0 24 24" width="28" height="38" aria-hidden="true">
          <path d="M12 22s7-6.1 7-12a7 7 0 10-14 0c0 5.9 7 12 7 12z" fill="${color}" />
          <circle cx="12" cy="10" r="3.6" fill="white" />
        </svg>
      </div>
    `,
  })
}

const userIcon = createPinIcon('#1a6b82')
const redIcon = createPinIcon('#dc2626')

export function MapPage() {
  const [searchParams] = useSearchParams()
  const [units, setUnits] = useState<HealthUnit[]>([])

  useEffect(() => {
    let active = true

    getHealthUnits().then((items) => {
      if (active) {
        setUnits(items)
      }
    })

    return () => {
      active = false
    }
  }, [])

  const highlightedType = searchParams.get('type')?.toUpperCase()

  return (
    <section className="map-page">
      <aside className="page-card map-sidebar">
        <div className="map-sidebar__section">
          <p className="dashboard-card__eyebrow">Mapa de atendimento</p>
          <h1 className="map-sidebar__title">Unidades próximas de Marília/SP</h1>
          <p className="map-sidebar__text">
            Veja UBS e UPA disponíveis com um pino para sua localização atual e popups com endereço.
          </p>
        </div>

        <div className="legend-list">
          <div className="legend-item">
            <span className="legend-item__dot legend-item__dot--user" />
            <div className="legend-item__meta">
              <strong>Sua localização</strong>
              <span>Marília/SP</span>
            </div>
          </div>
          <div className="legend-item">
            <span className="legend-item__dot legend-item__dot--upa" />
            <div className="legend-item__meta">
              <strong>UPA</strong>
              <span>Atendimento de urgência</span>
            </div>
          </div>
          <div className="legend-item">
            <span className="legend-item__dot legend-item__dot--ubs" />
            <div className="legend-item__meta">
              <strong>UBS</strong>
              <span>Acompanhamento básico</span>
            </div>
          </div>
        </div>

        <div className="map-sidebar__section">
          <h2 className="section-title">{highlightedType === 'UPA' ? 'Filtrando UPA' : 'Filtrando todas as unidades'}</h2>
          <p className="section-subtitle">As unidades carregadas são mockadas até o backend Flask ficar disponível.</p>
        </div>
      </aside>

      <article className="page-card map-panel">
        <div className="map-panel__overlay">
          <strong>Mapa interativo</strong>
          <span>OpenStreetMap + react-leaflet</span>
        </div>
        <div className="map-panel__map">
          <MapContainer center={USER_LOCATION} zoom={14} scrollWheelZoom className="map-panel__map">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker position={USER_LOCATION} icon={userIcon}>
              <Popup>
                <strong>Sua localização atual</strong>
                <br />
                Marília, SP
              </Popup>
            </Marker>

            {units
              .filter((unit) => {
                if (!highlightedType) {
                  return true
                }

                return unit.type === highlightedType
              })
              .map((unit) => (
                <Marker key={unit.id} position={unit.position} icon={redIcon}>
                  <Popup>
                    <strong>{unit.name}</strong>
                    <br />
                    {unit.type}
                    <br />
                    {unit.address}
                  </Popup>
                </Marker>
              ))}
          </MapContainer>
        </div>
      </article>
    </section>
  )
}