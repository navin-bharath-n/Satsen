import './StatusBar.css'

function StatusBar({ status, wsConnected }) {
  return (
    <div className="status-bar">


      <div className="status-item">
        <span className={`status-indicator ${wsConnected ? 'online' : 'offline'}`}></span>
        <span className="status-text">
          WebSocket: {wsConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      <div className="status-item">
        <span className="status-indicator online"></span>
        <span className="status-text">API: {status.status || 'Running'}</span>
      </div>
    </div>
  )
}

export default StatusBar




