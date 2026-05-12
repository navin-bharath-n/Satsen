export default function MapControls({ layer, setLayer }) {
  return (
    <div className="map-controls">
      {['fire', 'wind', 'temp', 'rain'].map(l => (
        <button
          key={l}
          className={layer === l ? 'active' : ''}
          onClick={() => setLayer(l)}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
