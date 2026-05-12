import { useState } from 'react'
import './SatelliteImageModal.css'

function SatelliteImageModal({ event, onClose }) {
  const [selectedImage, setSelectedImage] = useState('worldview')
  const [loading, setLoading] = useState(false)

  const imageSources = [
    {
      id: 'gibs',
      name: 'NASA GIBS',
      description: 'Live VIIRS satellite imagery',
      url: event.satellite_images?.gibs,
      icon: '🛰️',
      type: 'image',
      priority: 1
    },
    {
      id: 'mapbox',
      name: 'Mapbox Satellite',
      description: 'High-resolution satellite',
      url: event.satellite_images?.mapbox,
      icon: '📸',
      type: 'image',
      priority: 2
    },
    {
      id: 'landsat',
      name: 'Landsat Imagery',
      description: 'NASA Landsat satellite',
      url: event.satellite_images?.landsat,
      icon: '🌍',
      type: 'image',
      priority: 3
    },
    {
      id: 'sentinel',
      name: 'Sentinel Hub',
      description: 'ESA satellite data',
      url: event.satellite_images?.sentinel,
      icon: '🛰️',
      type: 'image',
      priority: 4
    },
    {
      id: 'worldview',
      name: 'NASA Worldview',
      description: 'Interactive satellite viewer',
      url: event.satellite_images?.worldview,
      icon: '🌐',
      type: 'iframe',
      priority: 5
    },
    {
      id: 'google_earth',
      name: 'Google Earth',
      description: '3D satellite view',
      url: event.satellite_images?.google_earth,
      icon: '🌍',
      type: 'iframe',
      priority: 6
    },
    {
      id: 'bing_maps',
      name: 'Bing Maps',
      description: 'Microsoft satellite',
      url: event.satellite_images?.bing_maps,
      icon: '🗺️',
      type: 'iframe',
      priority: 7
    }
  ].filter(source => source.url).sort((a, b) => (a.priority || 99) - (b.priority || 99))

  const handleImageLoad = () => {
    setLoading(false)
  }

  const handleImageError = () => {
    setLoading(false)
  }

  const selectedSource = imageSources.find(src => src.id === selectedImage)

  return (
    <div className="satellite-modal-overlay" onClick={onClose}>
      <div className="satellite-modal" onClick={e => e.stopPropagation()}>
        <div className="satellite-modal-header">
          <h3>🛰️ Live Satellite Images</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="satellite-modal-content">
          <div className="satellite-info">
            <div className="event-details">
              <h4>{event.severity} Fire Event</h4>
              <p><strong>Location:</strong> {event.district || 'Unknown'}, {event.state || 'Unknown'}</p>
              <p><strong>Coordinates:</strong> {event.lat?.toFixed(4)}, {event.lon?.toFixed(4)}</p>
              <p><strong>Fire Direction:</strong> {event.spread_direction || 'Unknown'}</p>
              <p><strong>Evacuation:</strong> {event.evacuation_direction || 'Away from fire'}</p>
              {event.live_data?.weather && (
                <div className="weather-info">
                  <h5>🌡️ Current Weather:</h5>
                  <p>🌡️ {event.live_data.weather.temperature}°C | 💧 {event.live_data.weather.humidity}% | 💨 {event.live_data.weather.wind_speed} m/s</p>
                  <p>🔥 Fire Risk: {event.live_data.weather.fire_risk}</p>
                </div>
              )}
            </div>

            <div className="image-sources">
              <h4>Available Views:</h4>
              {imageSources.map(source => (
                <button
                  key={source.id}
                  className={`source-button ${selectedImage === source.id ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedImage(source.id)
                    setLoading(true)
                  }}
                >
                  {source.icon} {source.name}
                  <small>{source.description}</small>
                </button>
              ))}
            </div>
          </div>

          <div className="satellite-image-display">
            <div className="image-header">
              <h4>{selectedSource?.name}</h4>
              <small>{selectedSource?.description}</small>
            </div>

            <div className="image-container">
              {loading && (
                <div className="loading-overlay">
                  <div className="spinner"></div>
                  <p>Loading satellite image...</p>
                  <p style={{ fontSize: '0.8em', color: '#999', marginTop: '0.5rem' }}>
                    {selectedSource?.name} - {selectedSource?.description}
                  </p>
                </div>
              )}

              {selectedSource?.type === 'image' && selectedSource.url && (
                <div className="satellite-image-wrapper">
                  <img
                    src={selectedSource.url}
                    alt={`${selectedSource.name} satellite view`}
                    className="satellite-image"
                    onLoad={handleImageLoad}
                    onError={handleImageError}
                    style={{
                      maxWidth: '100%',
                      maxHeight: '100%',
                      objectFit: 'contain',
                      borderRadius: '4px'
                    }}
                  />
                  <div className="image-info-overlay">
                    <div className="image-info">
                      <span className="image-source">{selectedSource.name}</span>
                      <span className="image-quality">
                        {selectedSource.id === 'gibs' && '🛰️ Live Satellite'}
                        {selectedSource.id === 'mapbox' && '📸 High Resolution'}
                        {selectedSource.id === 'landsat' && '🌍 Landsat Imagery'}
                        {selectedSource.id === 'sentinel' && '🛰️ ESA Sentinel'}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {selectedSource?.type === 'iframe' && selectedSource.url && (
                <div className="iframe-wrapper">
                  <div className="iframe-notice">
                    <span>🌐 Interactive View</span>
                    <small>This opens an external satellite viewer</small>
                  </div>
                  <iframe
                    src={selectedSource.url}
                    className="satellite-iframe"
                    title={`${selectedSource.name} satellite view`}
                    onLoad={handleImageLoad}
                    onError={handleImageError}
                    sandbox="allow-scripts allow-same-origin allow-forms"
                  />
                </div>
              )}

              {!selectedSource?.url && (
                <div className="no-image">
                  <div className="no-image-icon">🛰️</div>
                  <h3>Satellite Image Unavailable</h3>
                  <p>This satellite imagery source is currently not accessible.</p>
                  <p style={{ fontSize: '0.9em', color: '#666', marginTop: '0.5rem' }}>
                    Try switching to a different satellite source or check back later.
                  </p>
                  <div className="alternative-sources">
                    <small>Available alternatives:</small>
                    <div className="source-buttons">
                      {imageSources.filter(s => s.type === 'image' && s.url).map(source => (
                        <button
                          key={source.id}
                          onClick={() => {
                            setSelectedImage(source.id)
                            setLoading(true)
                          }}
                          className="alt-source-btn"
                        >
                          {source.icon} {source.name}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {selectedSource?.url && (
              <div className="image-actions">
                <a
                  href={selectedSource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="external-link"
                >
                  🔗 Open in New Tab
                </a>
                <button
                  onClick={() => {
                    setLoading(true)
                    // Force reload
                    setTimeout(() => setLoading(false), 1000)
                  }}
                  className="refresh-button"
                >
                  🔄 Refresh
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SatelliteImageModal
