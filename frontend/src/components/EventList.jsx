import { useState } from 'react'
import SatelliteImageModal from './SatelliteImageModal'
import './EventList.css'

const SatelliteImagePreview = ({ images, onViewAll }) => {
  const [imageLoaded, setImageLoaded] = useState(false)
  const [imageError, setImageError] = useState(false)
  const [currentSource, setCurrentSource] = useState(0)

  // Try multiple sources in order of preference
  const sources = [
    { name: 'NASA GIBS', url: images?.gibs, icon: '🛰️' },
    { name: 'Mapbox', url: images?.mapbox, icon: '📸' },
    { name: 'Landsat', url: images?.landsat, icon: '🌍' }
  ].filter(s => s.url)

  const currentImage = sources[currentSource]

  if (!sources.length) return null

  const tryNextSource = () => {
    if (currentSource < sources.length - 1) {
      setCurrentSource(currentSource + 1)
      setImageLoaded(false)
      setImageError(false)
    }
  }

  return (
    <div style={{ marginTop: '0.5rem' }}>
      <div style={{
        position: 'relative',
        width: '100%',
        height: '120px',
        border: '2px solid #ddd',
        borderRadius: '6px',
        overflow: 'hidden',
        background: '#f5f5f5'
      }}>
        {!imageLoaded && !imageError && (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#f5f5f5',
            zIndex: 2
          }}>
            <div style={{
              width: '20px',
              height: '20px',
              border: '2px solid #ddd',
              borderTop: '2px solid #667eea',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}></div>
            <div style={{ fontSize: '0.7em', color: '#666', marginTop: '0.25rem' }}>
              {currentImage?.name}
            </div>
          </div>
        )}

        {imageError ? (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#ffebee',
            color: '#c62828',
            fontSize: '0.8em',
            textAlign: 'center',
            padding: '0.5rem'
          }}>
            <div>🛰️</div>
            <div>Image Unavailable</div>
            {currentSource < sources.length - 1 ? (
              <button
                onClick={tryNextSource}
                style={{
                  marginTop: '0.25rem',
                  padding: '0.2rem 0.5rem',
                  fontSize: '0.7em',
                  background: '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '3px',
                  cursor: 'pointer'
                }}
              >
                Try {sources[currentSource + 1]?.name}
              </button>
            ) : (
              <button
                onClick={onViewAll}
                style={{
                  marginTop: '0.25rem',
                  padding: '0.2rem 0.5rem',
                  fontSize: '0.7em',
                  background: '#4caf50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '3px',
                  cursor: 'pointer'
                }}
              >
                View All Sources
              </button>
            )}
          </div>
        ) : (
          <img
            src={currentImage?.url}
            alt={`${currentImage?.name} satellite view`}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              display: imageLoaded ? 'block' : 'none'
            }}
            onLoad={() => setImageLoaded(true)}
            onError={() => {
              if (currentSource < sources.length - 1) {
                tryNextSource()
              } else {
                setImageError(true)
              }
            }}
          />
        )}

        {imageLoaded && (
          <>
            <div style={{
              position: 'absolute',
              top: '4px',
              left: '4px',
              background: 'rgba(0, 0, 0, 0.7)',
              color: 'white',
              padding: '2px 6px',
              borderRadius: '3px',
              fontSize: '0.7em',
              display: 'flex',
              alignItems: 'center',
              gap: '2px'
            }}>
              {currentImage?.icon} {currentImage?.name}
            </div>
            <div style={{
              position: 'absolute',
              bottom: '4px',
              right: '4px',
              background: 'rgba(0, 0, 0, 0.7)',
              color: 'white',
              padding: '2px 6px',
              borderRadius: '3px',
              fontSize: '0.7em',
              cursor: 'pointer'
            }}
              onClick={onViewAll}
              title="Click to view all satellite images"
            >
              📸 View All
            </div>
          </>
        )}
      </div>
    </div>
  )
}

const getSeverityBadge = (severity) => {
  const severityUpper = severity?.toUpperCase() || 'UNKNOWN'
  const colors = {
    'HIGH': { bg: '#fee', color: '#c00', emoji: '🔴' },
    'MEDIUM': { bg: '#ffe8cc', color: '#d66000', emoji: '🟠' },
    'LOW': { bg: '#fff4cc', color: '#d6a000', emoji: '🟡' },
  }
  const style = colors[severityUpper] || { bg: '#eee', color: '#666', emoji: '⚪' }

  return (
    <span
      className="severity-badge"
      style={{ backgroundColor: style.bg, color: style.color }}
    >
      {style.emoji} {severity}
    </span>
  )
}

function EventList({ events, onRefresh, onSelect }) {
  const [refreshing, setRefreshing] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [showSatelliteModal, setShowSatelliteModal] = useState(false)

  const handleRefresh = async () => {
    setRefreshing(true)
    await onRefresh()
    setTimeout(() => setRefreshing(false), 500)
  }

  const openSatelliteModal = (event) => {
    setSelectedEvent(event)
    setShowSatelliteModal(true)
  }

  const closeSatelliteModal = () => {
    setShowSatelliteModal(false)
    setSelectedEvent(null)
  }

  return (
    <div className="event-list">
      <div className="event-list-header">
        <h2>Fire Events</h2>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="refresh-btn"
        >
          {refreshing ? '🔄' : '↻'} Refresh
        </button>
      </div>

      <div className="event-count">
        {events.length} {events.length === 1 ? 'event' : 'events'} detected
      </div>

      <div className="events-container">
        {events.length === 0 ? (
          <div className="no-events">
            <p>No fire events detected yet.</p>
            <p className="subtext">The system is monitoring in real-time...</p>
          </div>
        ) : (
          [...events].sort((a, b) => {
            const sevOrder = { 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1 };
            const sevA = sevOrder[a.severity?.toUpperCase()] || 0;
            const sevB = sevOrder[b.severity?.toUpperCase()] || 0;
            return sevB - sevA;
          }).map((event) => (
            <div key={event.id} className="event-card" style={{
              padding: '1.25rem',
              marginBottom: '0.5rem',
              cursor: onSelect ? 'pointer' : 'default'
            }} onClick={() => onSelect && onSelect(event)}>
              <div className="event-header" style={{
                marginBottom: '1rem',
                paddingBottom: '0.75rem',
                borderBottom: '1px solid #e9ecef'
              }}>
                {getSeverityBadge(event.severity)}
                <span className="event-time">
                  {event.timestamp
                    ? new Date(event.timestamp).toLocaleTimeString()
                    : 'Unknown time'}
                </span>
              </div>

              <div className="event-details">
                <div className="detail-row" style={{ marginBottom: '0.75rem' }}>
                  <span className="label">📍 Location:</span>
                  <span className="value">
                    {event.district && event.district !== 'Unknown'
                      ? `${event.district}, ${event.state || 'Unknown'}`
                      : event.state && event.state !== 'Unknown'
                        ? event.state
                        : event.lat && event.lon
                          ? `${event.lat.toFixed(4)}, ${event.lon.toFixed(4)}`
                          : 'Unknown'}
                  </span>
                </div>

                <div className="detail-row" style={{ marginBottom: '0.75rem' }}>
                  <span className="label">📊 Spread Risk:</span>
                  <span className="value">{event.spread_risk || 'Unknown'}</span>
                </div>

                <div className="detail-row" style={{ marginBottom: '0.75rem' }}>
                  <span className="label">🧭 Fire Moving:</span>
                  <span className="value">{event.spread_direction || 'Unknown'}</span>
                </div>

                {event.evacuation_direction && (
                  <div className="detail-row evacuation-row" style={{
                    padding: '0.75rem',
                    borderRadius: '8px',
                    marginTop: '0.75rem',
                    marginBottom: '0.75rem',
                  }}>
                    <span className="label" style={{ fontWeight: 'bold', fontSize: '0.95rem' }}>➡️ Evacuate To:</span>
                    <span className="value" style={{ fontWeight: 'bold', fontSize: '0.95rem' }}>{event.evacuation_direction}</span>
                  </div>
                )}

                {event.satellite_images && (
                  <div className="satellite-section" style={{
                    marginTop: '1rem',
                    paddingTop: '1rem',
                    paddingBottom: '0.5rem',
                    borderTop: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(255,255,255,0.02)'
                  }}>
                    <strong style={{
                      fontSize: '1rem',
                      color: 'white',
                      display: 'block',
                      marginBottom: '0.75rem',
                      textAlign: 'center'
                    }}>
                      🛰️ Live Satellite Images
                    </strong>

                    {/* Display multiple satellite images */}
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.75rem',
                      padding: '0 0.25rem'
                    }}>

                      {/* Bing Maps Satellite Image (most reliable) */}
                      {event.satellite_images.bing && (
                        <div style={{ position: 'relative' }}>
                          <img
                            src={event.satellite_images.bing}
                            alt="Bing Maps satellite view"
                            style={{
                              width: '100%',
                              maxWidth: '320px',
                              height: '200px',
                              objectFit: 'cover',
                              border: '2px solid #0078d4',
                              borderRadius: '8px',
                              display: 'block',
                              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                            }}
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.nextSibling.style.display = 'flex';
                              e.target.nextSibling.nextSibling.style.display = 'none'; // Hide label
                            }}
                          />
                          <div className="error-overlay" style={{
                            display: 'none',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            background: '#f5f5f5',
                            border: '2px solid #ddd',
                            borderRadius: '8px',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#666',
                            fontSize: '0.8em',
                            textAlign: 'center',
                            padding: '1rem'
                          }}>
                            <div style={{ marginBottom: '0.5rem' }}>🗺️ Bing Maps</div>
                            <div>Image unavailable</div>
                          </div>
                          <div className="image-label" style={{
                            position: 'absolute',
                            top: '6px',
                            left: '6px',
                            background: 'rgba(0, 120, 212, 0.9)',
                            color: 'white',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75em',
                            fontWeight: 'bold',
                            zIndex: 1
                          }}>
                            🗺️ Bing Satellite
                          </div>
                        </div>
                      )}

                      {/* Mapbox Static Satellite Image */}
                      {event.satellite_images.static && (
                        <div style={{ position: 'relative' }}>
                          <img
                            src={event.satellite_images.static}
                            alt="Mapbox satellite view with fire marker"
                            style={{
                              width: '100%',
                              maxWidth: '320px',
                              height: '200px',
                              objectFit: 'cover',
                              border: '2px solid #4caf50',
                              borderRadius: '8px',
                              display: 'block',
                              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                            }}
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.nextSibling.style.display = 'flex';
                              e.target.nextSibling.nextSibling.style.display = 'none'; // Hide label
                            }}
                          />
                          <div className="error-overlay" style={{
                            display: 'none',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            background: '#f5f5f5',
                            border: '2px solid #ddd',
                            borderRadius: '8px',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#666',
                            fontSize: '0.8em',
                            textAlign: 'center',
                            padding: '1rem'
                          }}>
                            <div style={{ marginBottom: '0.5rem' }}>📸 Mapbox</div>
                            <div>Image unavailable</div>
                          </div>
                          <div className="image-label" style={{
                            position: 'absolute',
                            top: '6px',
                            left: '6px',
                            background: 'rgba(76, 175, 80, 0.9)',
                            color: 'white',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75em',
                            fontWeight: 'bold',
                            zIndex: 1
                          }}>
                            📸 Mapbox + Fire Marker
                          </div>
                        </div>
                      )}

                      {/* NASA GIBS Image */}
                      {event.satellite_images.gibs && (
                        <div style={{ position: 'relative' }}>
                          <img
                            src={event.satellite_images.gibs}
                            alt="NASA GIBS satellite view"
                            style={{
                              width: '100%',
                              maxWidth: '320px',
                              height: '200px',
                              objectFit: 'cover',
                              border: '2px solid #ff6b35',
                              borderRadius: '8px',
                              display: 'block',
                              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                            }}
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.nextSibling.style.display = 'flex';
                              e.target.nextSibling.nextSibling.style.display = 'none'; // Hide label
                            }}
                          />
                          <div className="error-overlay" style={{
                            display: 'none',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            background: '#f5f5f5',
                            border: '2px solid #ddd',
                            borderRadius: '8px',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#666',
                            fontSize: '0.8em',
                            textAlign: 'center',
                            padding: '1rem'
                          }}>
                            <div style={{ marginBottom: '0.5rem' }}>🛰️ NASA GIBS</div>
                            <div>Image unavailable</div>
                          </div>
                          <div className="image-label" style={{
                            position: 'absolute',
                            top: '6px',
                            left: '6px',
                            background: 'rgba(255, 107, 53, 0.9)',
                            color: 'white',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75em',
                            fontWeight: 'bold',
                            zIndex: 1
                          }}>
                            🛰️ NASA GIBS
                          </div>
                        </div>
                      )}

                      {/* Sentinel Hub Image (if available) */}
                      {event.satellite_images.sentinel && (
                        <div style={{ position: 'relative' }}>
                          <img
                            src={event.satellite_images.sentinel}
                            alt="Sentinel Hub satellite view"
                            style={{
                              width: '100%',
                              maxWidth: '320px',
                              height: '200px',
                              objectFit: 'cover',
                              border: '2px solid #9c27b0',
                              borderRadius: '8px',
                              display: 'block',
                              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                            }}
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.nextSibling.style.display = 'flex';
                              e.target.nextSibling.nextSibling.style.display = 'none'; // Hide label
                            }}
                          />
                          <div className="error-overlay" style={{
                            display: 'none',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            background: '#f5f5f5',
                            border: '2px solid #ddd',
                            borderRadius: '8px',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#666',
                            fontSize: '0.8em',
                            textAlign: 'center',
                            padding: '1rem'
                          }}>
                            <div style={{ marginBottom: '0.5rem' }}>🛰️ Sentinel Hub</div>
                            <div>Image unavailable</div>
                          </div>
                          <div className="image-label" style={{
                            position: 'absolute',
                            top: '6px',
                            left: '6px',
                            background: 'rgba(156, 39, 176, 0.9)',
                            color: 'white',
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75em',
                            fontWeight: 'bold',
                            zIndex: 1
                          }}>
                            🛰️ Sentinel Hub
                          </div>
                        </div>
                      )}

                    </div>

                    {/* Interactive satellite viewers */}
                    <div className="interactive-links" style={{
                      marginTop: '1rem',
                      padding: '0.75rem',
                      backgroundColor: 'rgba(255,255,255,0.02)',
                      borderRadius: '8px',
                      border: '1px solid rgba(255,255,255,0.1)'
                    }}>
                      <div style={{
                        fontSize: '0.9rem',
                        fontWeight: '600',
                        color: 'rgba(255,255,255,0.9)',
                        marginBottom: '0.75rem',
                        textAlign: 'center',
                        padding: '0.5rem',
                        backgroundColor: 'rgba(255,255,255,0.05)',
                        borderRadius: '6px',
                        border: '1px solid rgba(255,255,255,0.05)'
                      }}>
                        🌐 Interactive Satellite Viewers
                      </div>
                      <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.5rem'
                      }}>
                        {event.satellite_images.worldview && (
                          <a href={event.satellite_images.worldview} target="_blank" rel="noopener noreferrer"
                            style={{
                              fontSize: '0.85em',
                              color: '#66b2ff',
                              textDecoration: 'none',
                              padding: '0.5rem',
                              borderRadius: '4px',
                              backgroundColor: 'rgba(255,255,255,0.05)',
                              border: '1px solid rgba(255,255,255,0.1)',
                              display: 'block',
                              textAlign: 'center',
                              transition: 'all 0.2s'
                            }}
                            onMouseOver={(e) => e.target.style.backgroundColor = 'rgba(255,255,255,0.1)'}
                            onMouseOut={(e) => e.target.style.backgroundColor = 'rgba(255,255,255,0.05)'}>
                            🌐 NASA Worldview (Interactive) →
                          </a>
                        )}
                        {event.satellite_images.google_earth && (
                          <a href={event.satellite_images.google_earth} target="_blank" rel="noopener noreferrer"
                            style={{
                              fontSize: '0.85em',
                              color: '#81c784',
                              textDecoration: 'none',
                              padding: '0.5rem',
                              borderRadius: '4px',
                              backgroundColor: 'rgba(255,255,255,0.05)',
                              border: '1px solid rgba(255,255,255,0.1)',
                              display: 'block',
                              textAlign: 'center',
                              transition: 'all 0.2s'
                            }}
                            onMouseOver={(e) => e.target.style.backgroundColor = 'rgba(255,255,255,0.1)'}
                            onMouseOut={(e) => e.target.style.backgroundColor = 'rgba(255,255,255,0.05)'}>
                            🌍 Google Earth (3D View) →
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {event.safety_zones && event.safety_zones.length > 0 && (
                  <div className="safety-zones-section" style={{
                    marginTop: '1rem',
                    padding: '0.75rem',
                    borderRadius: '8px',
                  }}>
                    <strong style={{
                      fontSize: '0.9rem',
                      color: '#f3c162',
                      display: 'block',
                      marginBottom: '0.5rem'
                    }}>
                      🛡️ Nearby Safe Zones:
                    </strong>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      {event.safety_zones.slice(0, 3).map((zone, idx) => (
                        <div key={idx} style={{
                          fontSize: '0.85em',
                          color: 'rgba(255,255,255,0.9)',
                          padding: '0.25rem 0.5rem',
                          backgroundColor: 'rgba(255, 255, 255, 0.05)',
                          borderRadius: '4px',
                          border: '1px solid rgba(255, 255, 255, 0.1)'
                        }}>
                          • {zone.name}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {event.lat && event.lon && (
                  <div className="detail-row coordinates-row" style={{
                    marginTop: '0.75rem',
                    padding: '0.5rem',
                    borderRadius: '8px',
                  }}>
                    <span className="label" style={{ fontSize: '0.85rem' }}>🌐 Coordinates:</span>
                    <span className="value small" style={{
                      fontFamily: 'monospace',
                      backgroundColor: 'rgba(255,255,255,0.05)',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      border: '1px solid rgba(255,255,255,0.1)'
                    }}>
                      {event.lat.toFixed(4)}, {event.lon.toFixed(4)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Satellite Image Modal */}
      {showSatelliteModal && selectedEvent && (
        <SatelliteImageModal
          event={selectedEvent}
          onClose={closeSatelliteModal}
        />
      )}
    </div>
  )
}

export default EventList


