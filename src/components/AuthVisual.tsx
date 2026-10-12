import { MapContainer, TileLayer } from 'react-leaflet'

const AUTH_MAP_CENTER: [number, number] = [-22.2167, -49.9501]

export function AuthVisual() {
  return (
    <section className="login-visual" aria-hidden="true">
      <div className="login-visual__map-frame">
        <MapContainer
          center={AUTH_MAP_CENTER}
          zoom={13}
          scrollWheelZoom={false}
          dragging={false}
          doubleClickZoom={false}
          zoomControl={false}
          attributionControl={false}
          className="login-visual__map"
        >
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
        </MapContainer>
      </div>
      <div className="login-visual__overlay">
        <div className="login-visual__chip">Marília / SP</div>
        <div className="login-visual__chip login-visual__chip--soft">Mapa de atendimento</div>
      </div>
    </section>
  )
}
