import { divIcon } from 'leaflet'
import type { DivIcon, LatLngExpression } from 'leaflet'
import { LocateFixed, Phone } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { useSearchParams } from 'react-router-dom'
import { getErrorMessage, getHealthUnits, type HealthUnit, type UnitLevel } from '../services/api'

// Centro de Marília/SP: usado quando o navegador não libera a localização
const DEFAULT_LOCATION: [number, number] = [-22.2184, -49.9506]
const VALID_LEVELS: UnitLevel[] = ['UBS', 'UPA', 'EMERGENCIA']

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
const upaIcon = createPinIcon('#dc2626')
const ubsIcon = createPinIcon('#16a34a')

const FILTER_TITLE: Record<UnitLevel, string> = {
  UBS: 'Filtrando UBS',
  UPA: 'Filtrando UPA',
  EMERGENCIA: 'Emergência: UPAs mais próximas',
}

type Geo = { position: [number, number]; isReal: boolean }

/** Recentraliza o mapa quando a localização do usuário muda. */
function Recenter({ center }: { center: LatLngExpression }) {
  const map = useMap()
  useEffect(() => {
    map.setView(center)
  }, [center, map])
  return null
}

export function MapPage() {
  const [searchParams] = useSearchParams()
  const rawType = searchParams.get('type')?.toUpperCase() as UnitLevel | undefined
  const level = rawType && VALID_LEVELS.includes(rawType) ? rawType : null

  const [geo, setGeo] = useState<Geo>({ position: DEFAULT_LOCATION, isReal: false })
  const [units, setUnits] = useState<HealthUnit[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Geolocalização do navegador (com fallback para Marília/SP)
  useEffect(() => {
    if (!('geolocation' in navigator)) {
      return
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => setGeo({ position: [coords.latitude, coords.longitude], isReal: true }),
      () => undefined,
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 },
    )
  }, [])

  const [lat, lng] = geo.position

  useEffect(() => {
    let active = true

    getHealthUnits({ lat, lng, type: level })
      .then((items) => {
        if (!active) return
        setUnits(items)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!active) return
        setUnits([])
        setError(getErrorMessage(err))
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })

    return () => {
      active = false
    }
  }, [lat, lng, level])

  const center = useMemo<[number, number]>(() => [lat, lng], [lat, lng])

  return (
    <section className="map-page">
      <aside className="page-card map-sidebar">
        <div className="map-sidebar__section">
          <p className="dashboard-card__eyebrow">Mapa de atendimento</p>
          <h1 className="map-sidebar__title">Unidades de saúde próximas</h1>
          <p className="map-sidebar__text">
            UBS e UPAs ordenadas pela distância até {geo.isReal ? 'a sua localização' : 'o centro de Marília/SP'}.
          </p>
        </div>

        <div className="legend-list">
          <div className="legend-item">
            <span className="legend-item__dot legend-item__dot--user" />
            <div className="legend-item__meta">
              <strong>Sua localização</strong>
              <span>{geo.isReal ? 'Obtida pelo navegador' : 'Aproximada (Marília/SP)'}</span>
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
          <h2 className="section-title">{level ? FILTER_TITLE[level] : 'Todas as unidades'}</h2>
          {level === 'EMERGENCIA' ? (
            <a className="map-emergency-call" href="tel:192">
              <Phone size={16} /> Em emergência, ligue 192 (SAMU)
            </a>
          ) : null}
          {isLoading ? <p className="section-subtitle">Carregando unidades...</p> : null}
          {error ? <div className="error-banner">{error}</div> : null}
          {!isLoading && !error && units.length === 0 ? (
            <p className="section-subtitle">Nenhuma unidade cadastrada para este filtro.</p>
          ) : null}
        </div>

        {units.length > 0 ? (
          <ul className="unit-list" aria-label="Unidades mais próximas">
            {units.slice(0, 8).map((unit) => (
              <li key={unit.id} className="unit-list__item">
                <span className={`legend-item__dot legend-item__dot--${unit.type.toLowerCase()}`} />
                <div className="unit-list__meta">
                  <strong>{unit.name}</strong>
                  <span>{unit.address}</span>
                  {unit.phone ? <a href={`tel:${unit.phone.replace(/\D/g, '')}`}>{unit.phone}</a> : null}
                </div>
                <span className="unit-list__distance">{unit.distance_km.toFixed(1)} km</span>
              </li>
            ))}
          </ul>
        ) : null}
      </aside>

      <article className="page-card map-panel">
        <div className="map-panel__overlay">
          <strong>Mapa interativo</strong>
          <span>
            <LocateFixed size={12} style={{ display: 'inline', marginRight: 4 }} />
            {units.length} unidade(s) encontrada(s)
          </span>
        </div>
        <div className="map-panel__map">
          <MapContainer center={center} zoom={14} scrollWheelZoom className="map-panel__map">
            <Recenter center={center} />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker position={center} icon={userIcon}>
              <Popup>
                <strong>{geo.isReal ? 'Sua localização atual' : 'Localização aproximada'}</strong>
                <br />
                {geo.isReal ? 'Obtida pelo navegador' : 'Marília, SP'}
              </Popup>
            </Marker>

            {units.map((unit) => (
              <Marker key={unit.id} position={unit.position} icon={unit.type === 'UPA' ? upaIcon : ubsIcon}>
                <Popup>
                  <strong>{unit.name}</strong>
                  <br />
                  {unit.type} • {unit.distance_km.toFixed(1)} km
                  <br />
                  {unit.address}
                  {unit.phone ? (
                    <>
                      <br />
                      {unit.phone}
                    </>
                  ) : null}
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </article>
    </section>
  )
}