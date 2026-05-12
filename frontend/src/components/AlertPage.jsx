import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Circle } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./AlertPage.css";

const siren = new Audio("/alert.mp3");

export default function AlertPage() {
  const [alert, setAlert] = useState(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/alerts");

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);

      if (data.type === "ALERT") {
        setAlert(data);
        siren.play();
      }
    };

    return () => ws.close();
  }, []);

  if (!alert) {
    return (
      <div className="alert-wait">
        🛰️ Waiting for nearby fire alerts...
      </div>
    );
  }

  return (
    <div className="alert-page">
      <h1 className="alert-title">🔥 FIRE ALERT NEAR YOU</h1>

      <div className="alert-info">
        <p><strong>Message:</strong> {alert.message}</p>
        <p><strong>Evacuate Towards:</strong> {alert.safe_direction}</p>
      </div>

      {/* DISTRICT VIEW MAP */}
      <MapContainer
        center={[alert.lat, alert.lon]}
        zoom={11}
        style={{ height: "70vh", width: "100%" }}
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />

        {/* Fire location */}
        <Circle
          center={[alert.lat, alert.lon]}
          radius={4000}
          pathOptions={{ color: "red", fillOpacity: 0.3 }}
        />

        {/* User marker */}
        <Marker
          position={[alert.lat, alert.lon]}
          icon={L.divIcon({
            html: "🚶",
            iconSize: [30, 30],
          })}
        />
      </MapContainer>
    </div>
  );
}
