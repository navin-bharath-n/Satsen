import { Fragment, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline, useMap } from 'react-leaflet'
import { Icon, divIcon } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

// Fix for default Leaflet icon issue
if (L.Icon.Default.prototype._getIconUrl) {
  delete L.Icon.Default.prototype._getIconUrl
}
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const getSeverityColor = (severity) => {
  switch (severity?.toUpperCase()) {
    case 'HIGH':
      return '#ff0000'
    case 'MEDIUM':
      return '#ff8800'
    case 'LOW':
      return '#ffaa00'
    default:
      return '#888888'
  }
}

const getSeverityRadius = (severity) => {
  switch (severity?.toUpperCase()) {
    case 'HIGH':
      return 5000
    case 'MEDIUM':
      return 3000
    case 'LOW':
      return 2000
    default:
      return 1000
  }
}

const createCustomIcon = (color) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><circle cx="16" cy="16" r="12" fill="${color}" stroke="white" stroke-width="2"/><circle cx="16" cy="16" r="6" fill="white"/></svg>`
  const encoded = encodeURIComponent(svg)
  return new Icon({
    iconUrl: `data:image/svg+xml;charset=utf-8,${encoded}`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  })
}

const createDirectionArrow = (direction, color) => {
  const angles = {
    'N': 0, 'NE': 45, 'E': 90, 'SE': 135,
    'S': 180, 'SW': 225, 'W': 270, 'NW': 315
  }
  const angle = angles[direction] || 0
  
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><path d="M20,5 L25,30 L20,25 L15,30 Z" fill="${color}" stroke="white" stroke-width="2" transform="rotate(${angle} 20 20)"/></svg>`
  const encoded = encodeURIComponent(svg)
  
  return new Icon({
    iconUrl: `data:image/svg+xml;charset=utf-8,${encoded}`,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  })
}

const getDirectionOffset = (direction, distance = 0.05) => {
  const angles = {
    'N': 0, 'NE': 45, 'E': 90, 'SE': 135,
    'S': 180, 'SW': 225, 'W': 270, 'NW': 315
  }
  const angle = angles[direction] || 0
  const rad = angle * Math.PI / 180
  return {
    lat: Math.cos(rad) * distance,
    lon: Math.sin(rad) * distance
  }
}

// Component to handle map updates
function MapUpdater({ events }) {
  const map = useMap()
  
  useEffect(() => {
    if (map) {
      // Force map to resize multiple times to ensure it works
      const resizeMap = () => {
        map.invalidateSize()
      }
      
      // Immediate resize
      resizeMap()
      
      // Resize after a short delay
      setTimeout(resizeMap, 100)
      setTimeout(resizeMap, 300)
      setTimeout(resizeMap, 500)
      
      // Also listen for window resize
      window.addEventListener('resize', resizeMap)
      
      return () => {
        window.removeEventListener('resize', resizeMap)
      }
    }
  }, [map, events])
  
  return null
}

function MapView({ events }) {
  const defaultCenter = [20.5937, 78.9629] // India center
  const defaultZoom = 5

  return (
    <div style={{ 
      height: '100%', 
      width: '100%', 
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      zIndex: 0 
    }}>
      <MapContainer
        key="fire-monitoring-map"
        center={defaultCenter}
        zoom={defaultZoom}
        style={{ 
          height: '100%', 
          width: '100%', 
          minHeight: '600px',
          position: 'relative',
          zIndex: 0 
        }}
        scrollWheelZoom={true}
        whenReady={() => {
          // Force map to resize after initialization
          setTimeout(() => {
            const mapElement = document.querySelector('.leaflet-container')
            if (mapElement && window.dispatchEvent) {
              window.dispatchEvent(new Event('resize'))
            }
          }, 100)
        }}
      >
        <MapUpdater events={events} />
      <TileLayer
        attribution='&copy; <a href="https://www.esri.com/">Esri</a> &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        maxZoom={19}
      />
      
      {events.map((event) => {
        if (!event.lat || !event.lon) return null
        
        const color = getSeverityColor(event.severity)
        const radius = getSeverityRadius(event.severity)
        const offset = event.spread_direction ? getDirectionOffset(event.spread_direction, 0.08) : { lat: 0, lon: 0 }
        
        return (
          <Fragment key={event.id}>
            {/* Fire danger zone */}
            <Circle
              center={[event.lat, event.lon]}
              radius={radius}
              pathOptions={{
                color: color,
                fillColor: color,
                fillOpacity: 0.2,
                weight: 2,
              }}
            />
            
            {/* Fire spread direction arrow */}
            {event.spread_direction && (
              <Marker
                position={[event.lat + offset.lat, event.lon + offset.lon]}
                icon={createDirectionArrow(event.spread_direction, color)}
              />
            )}
            
            {/* Safety zones */}
            {event.safety_zones && event.safety_zones.map((zone, idx) => (
              <Fragment key={`zone-${event.id}-${idx}`}>
                <Circle
                  center={[zone.lat, zone.lon]}
                  radius={1000}
                  pathOptions={{
                    color: '#4caf50',
                    fillColor: '#4caf50',
                    fillOpacity: 0.3,
                    weight: 2,
                    dashArray: '5, 5'
                  }}
                />
                <Marker
                  position={[zone.lat, zone.lon]}
                  icon={new Icon({
                    iconUrl: `data:image/svg+xml;charset=utf-8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#4caf50" stroke="white" stroke-width="2"/><text x="12" y="16" font-size="12" fill="white" text-anchor="middle">✓</text></svg>')}`,
                    iconSize: [24, 24],
                    iconAnchor: [12, 12],
                  })}
                >
                  <Popup>
                    <div>
                      <strong style={{ color: '#4caf50' }}>🛡️ Safe Zone</strong>
                      <p>{zone.name}</p>
                      <p>Distance: {zone.distance_km}km</p>
                      <p>Direction: {zone.direction}</p>
                    </div>
                  </Popup>
                </Marker>
              </Fragment>
            ))}
            
            {/* Main fire marker */}
            <Marker
              position={[event.lat, event.lon]}
              icon={createCustomIcon(color)}
            >
              <Popup>
                <div style={{ minWidth: '250px' }}>
                  <h3 style={{ margin: '0 0 8px 0', color: color }}>
                    🔥 {event.severity || 'Unknown'} Severity Fire
                  </h3>
                  <p style={{ margin: '4px 0' }}>
                    <strong>📍 Location:</strong> {
                      event.district && event.district !== 'Unknown' 
                        ? `${event.district}, ${event.state || 'Unknown'}` 
                        : event.state && event.state !== 'Unknown'
                        ? event.state
                        : event.lat && event.lon
                        ? `${event.lat.toFixed(4)}, ${event.lon.toFixed(4)}`
                        : 'Unknown'
                    }
                  </p>
                  <p style={{ margin: '4px 0' }}>
                    <strong>📊 Spread Risk:</strong> {event.spread_risk || 'Unknown'}
                  </p>
                  <p style={{ margin: '4px 0' }}>
                    <strong>🧭 Fire Moving:</strong> {event.spread_direction || 'Unknown'}
                  </p>
                  <p style={{ margin: '4px 0', color: '#4caf50', fontWeight: 'bold' }}>
                    <strong>➡️ Evacuate:</strong> {event.evacuation_direction || 'Away from fire'}
                  </p>
                  {event.satellite_images && (
                    <div style={{ marginTop: '8px' }}>
                      <strong>🛰️ Satellite Images:</strong>
                      <div style={{ marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {event.satellite_images.worldview && (
                          <a href={event.satellite_images.worldview} target="_blank" rel="noopener noreferrer" 
                             style={{ fontSize: '0.85em', color: '#0066cc' }}>
                            NASA Worldview
                          </a>
                        )}
                        {event.satellite_images.google_earth && (
                          <a href={event.satellite_images.google_earth} target="_blank" rel="noopener noreferrer"
                             style={{ fontSize: '0.85em', color: '#0066cc' }}>
                            Google Earth
                          </a>
                        )}
                      </div>
                    </div>
                  )}
                  {event.timestamp && (
                    <p style={{ margin: '4px 0', fontSize: '0.85em', color: '#666' }}>
                      {new Date(event.timestamp).toLocaleString()}
                    </p>
                  )}
                </div>
              </Popup>
            </Marker>
          </Fragment>
        )
      })}
      </MapContainer>
    </div>
  )
}

export default MapView

