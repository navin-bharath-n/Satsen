import './StatusBar.css'

function StatusBar({ status, wsConnected }) {
  const isOnline = status.status === 'healthy' || status.status === 'running' || status.status === 'Active';
  const gibsOnline = status.gibs_tile_server === 'online';
  const cnnOnline = status.torch_ml_engine === 'online' || status.cnn_model_loaded;
  const latency = status.api_response_time_ms ? `${status.api_response_time_ms} ms` : null;
  const env = status.environment || 'Live';
  const matched = status.system_match_status || 'SYNCHRONIZED';

  return (
    <div className="status-bar" style={{
      display: "flex",
      flexWrap: "wrap",
      gap: "20px",
      alignItems: "center",
      background: "rgba(10, 15, 30, 0.65)",
      backdropFilter: "blur(12px)",
      padding: "10px 18px",
      borderRadius: "10px",
      border: "1px solid rgba(255, 255, 255, 0.1)",
      margin: "8px 0"
    }}>
      <div className="status-item">
        <span className={`status-indicator-dot ${wsConnected ? 'online' : 'offline'}`}></span>
        <span className="status-text">
          WebSocket: <strong>{wsConnected ? 'Connected' : 'Disconnected'}</strong>
        </span>
      </div>

      <div className="status-item">
        <span className={`status-indicator-dot ${isOnline ? 'online' : 'offline'}`}></span>
        <span className="status-text">
          NASA FIRMS API: <strong>{isOnline ? 'Online (VIIRS/MODIS)' : 'Degraded'}</strong>
        </span>
      </div>

      <div className="status-item">
        <span className={`status-indicator-dot ${gibsOnline ? 'online' : 'offline'}`}></span>
        <span className="status-text">
          NASA GIBS Imagery: <strong>{gibsOnline ? 'Active' : 'Standby'}</strong>
        </span>
      </div>

      <div className="status-item">
        <span className={`status-indicator-dot ${cnnOnline ? 'online' : 'offline'}`}></span>
        <span className="status-text">
          ResNet18 CNN Model: <strong>{cnnOnline ? 'Loaded' : 'Offline'}</strong>
        </span>
      </div>

      {latency && (
        <div className="status-item">
          <span className="status-indicator-dot latency"></span>
          <span className="status-text">
            Fireping Latency: <strong style={{ color: "#38bdf8" }}>{latency}</strong>
          </span>
        </div>
      )}

      <div className="status-item" style={{ marginLeft: "auto", display: "flex", gap: "12px", alignItems: "center" }}>
        <span style={{
          background: "rgba(16, 185, 129, 0.15)",
          border: "1px solid rgba(16, 185, 129, 0.4)",
          color: "#34d399",
          padding: "2px 8px",
          borderRadius: "4px",
          fontSize: "11px",
          fontWeight: 600,
          letterSpacing: "0.5px"
        }}>
          🛰️ Telemetry: {matched}
        </span>
        <span className="status-text" style={{ fontSize: "11px", letterSpacing: "1px", textTransform: "uppercase", color: "#94a3b8" }}>
          Mode: <strong style={{ color: env.includes('Sandbox') ? '#f59e0b' : '#34d399' }}>{env}</strong>
        </span>
      </div>
    </div>
  )
}

export default StatusBar

