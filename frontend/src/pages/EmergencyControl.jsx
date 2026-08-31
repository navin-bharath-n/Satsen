import { useEffect, useState, useRef } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  MapContainer,
  TileLayer,
  Circle,
  Polyline,
  Polygon,
  Marker,
  Popup,
  useMap
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import "./EmergencyControl.css";

const userIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const safeZoneIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const API = "http://127.0.0.1:8000";
const WS = "ws://localhost:8000/ws/alerts";

/* ---------------- AUTO ZOOM ---------------- */
function AutoZoom({ alert }) {
  const map = useMap();

  useEffect(() => {
    if (alert?.lat && alert?.lon) {
      setTimeout(() => {
        map.flyTo([alert.lat, alert.lon], 11, {
          animate: true,
          duration: 2
        });
      }, 500);
    }
  }, [alert]);

  return null;
}

export default function EmergencyControl() {
  const navigate = useNavigate();

  const [events, setEvents] = useState([]);
  const [alert, setAlert] = useState(null);
  const [spreadScale, setSpreadScale] = useState(1);
  const [flash, setFlash] = useState(false);
  const [audioReady, setAudioReady] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);

  const sirenRef = useRef(null);

  /* ---------------- INITIALIZE AUDIO ---------------- */
  useEffect(() => {
    const audio = new Audio("/siren.mp3");
    audio.loop = true;
    audio.preload = "auto";
    sirenRef.current = audio;

    return () => {
      if (sirenRef.current) {
        sirenRef.current.pause();
        sirenRef.current = null;
      }
    };
  }, []);

  /* ---------------- UNLOCK AUDIO ON FIRST CLICK ---------------- */
  useEffect(() => {
    const unlock = () => {
      if (!sirenRef.current) return;

      sirenRef.current.play()
        .then(() => {
          sirenRef.current.pause();
          sirenRef.current.currentTime = 0;
          setAudioReady(true);
          console.log("🔓 Audio unlocked");
        })
        .catch(() => {});

      document.removeEventListener("click", unlock);
    };

    document.addEventListener("click", unlock);

    return () => document.removeEventListener("click", unlock);
  }, []);

  /* ---------------- FETCH EVENTS ---------------- */
  const fetchEvents = async () => {
    try {
      const res = await axios.get(`${API}/fire/events`);
      setEvents(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  /* ---------------- LOAD LOCAL ALERT ---------------- */
  useEffect(() => {
    const stored = localStorage.getItem("alertData");
    if (stored) {
      const data = JSON.parse(stored);
      setTimeout(() => triggerEmergency(data), 1000);
      localStorage.removeItem("alertData");
    }
  }, []);

  /* ---------------- WEBSOCKET ---------------- */
  useEffect(() => {
    fetchEvents();

    const ws = new WebSocket(WS);

    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data);

      if (data.type === "ALERT") {
        triggerEmergency(data);
      }

      fetchEvents();
    };

    return () => ws.close();
  }, []);

  /* ---------------- SPREAD ANIMATION ---------------- */
  useEffect(() => {
    const interval = setInterval(() => {
      setSpreadScale(prev => prev > 2 ? 1 : prev + 0.1);
    }, 400);
    return () => clearInterval(interval);
  }, []);

  /* ---------------- EMERGENCY TRIGGER ---------------- */
  const triggerEmergency = (data) => {
    console.log("🚨 EMERGENCY TRIGGERED");
    setAlert(data);
    setFlash(true);
    setShowOverlay(true);

    // 🔊 FORCE SIREN
    if (sirenRef.current) {
      sirenRef.current.currentTime = 0;
      sirenRef.current.play()
        .then(() => {
          console.log("🔥 SIREN PLAYING");
        })
        .catch(err => {
          console.log("⚠️ Autoplay blocked. Click anywhere once.");
        });
    }

    speakEvacuation(data);
  };

  /* ---------------- VOICE ---------------- */
  const speakEvacuation = (data) => {
    const text = `Emergency alert. Level ${data.severity} forest fire detected near your location. Evacuate immediately towards the ${data.evacuation_direction || "safe zone"}.`;

    const msg = new SpeechSynthesisUtterance(text);
    msg.rate = 0.95;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(msg);
  };

  const handleDeactivate = () => {
    if (sirenRef.current) {
      sirenRef.current.pause();
      sirenRef.current.currentTime = 0;
    }
    setFlash(false);
    navigate("/dashboard");
  };

  const handleAcknowledgeAlert = () => {
    setShowOverlay(false);
    setFlash(false);
    if (sirenRef.current) {
      sirenRef.current.pause();
    }
  };

  const getColor = (severity) => {
    if (severity === "HIGH") return "red";
    if (severity === "MEDIUM") return "orange";
    return "yellow";
  };

  /* ---------------- HEATMAP ---------------- */
  function HeatmapLayer({ events }) {
    const map = useMap();

    useEffect(() => {
      if (!map || !events.length) return;

      const heatData = events.map(e => [
        e.lat,
        e.lon,
        e.severity === "HIGH" ? 1.0 :
        e.severity === "MEDIUM" ? 0.6 : 0.3
      ]);

      const heat = L.heatLayer(heatData, {
        radius: 40,
        blur: 25
      });

      heat.addTo(map);
      return () => map.removeLayer(heat);

    }, [events, map]);

    return null;
  }

  return (
    <div className="emergency-control-container">
      {/* UNLOCK AUDIO OVERLAY IF NEEDED */}
      {!audioReady && (
        <>
          <div className="unlock-overlay" />
          <button className="unlock-audio-btn">
            🔓 INITIALIZE EMERGENCY AUDIO
          </button>
        </>
      )}

      {/* SATSEN HUD HEADER */}
      <header className="emergency-header">
        <div className="emergency-logo-group">
          <span style={{ fontSize: "1.6rem" }}>🚨</span>
          <span className="emergency-title">SATSEN CRITICAL ALARM PANEL</span>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <span style={{ 
            fontSize: "0.75rem", 
            letterSpacing: "1.5px", 
            color: "#ff3b30", 
            background: "rgba(255,59,48,0.1)", 
            padding: "4px 10px", 
            borderRadius: "4px",
            border: "1px solid rgba(255,59,48,0.25)",
            fontFamily: "Orbitron" 
          }}>
            STATUS: ACTIVE DANGER
          </span>
          <button className="deactivate-btn" onClick={handleDeactivate}>
            🔕 DEACTIVATE SIREN & RETURN
          </button>
        </div>
      </header>

      <div className={`emergency-wrapper ${flash ? "emergency-active" : ""}`}>
        <div className="emergency-grid">
          
          {/* LEFT SIDEBAR HUD READOUT */}
          <aside className="emergency-sidebar">
            {/* THREAT ANALYSIS CARD */}
            <div className="hud-panel">
              <div className="hud-panel-title">📡 THREAT TELEMETRY</div>
              <div className="telemetry-row">
                <span className="telemetry-label">SECTOR REGION</span>
                <span className="telemetry-val">{alert?.district || "Unknown"}, {alert?.state || "Unknown"}</span>
              </div>
              <div className="telemetry-row">
                <span className="telemetry-label">COORDINATES</span>
                <span className="telemetry-val">
                  {alert?.lat?.toFixed(4) || "0.0000"}, {alert?.lon?.toFixed(4) || "0.0000"}
                </span>
              </div>
              <div className="telemetry-row">
                <span className="telemetry-label">SEVERITY LEVEL</span>
                <span className="telemetry-val" style={{ color: "#ff3b30" }}>
                  {alert?.severity || "HIGH"}
                </span>
              </div>
              <div className="telemetry-row">
                <span className="telemetry-label">SPREAD RISK (LSTM)</span>
                <span className="telemetry-val" style={{ color: "#ffb800" }}>
                  {alert?.advancedWeather?.lstmSpreadRisk || "EXTREME"}
                </span>
              </div>
            </div>

            {/* EVACUATION GUIDANCE CARD */}
            <div className="hud-panel">
              <div className="hud-panel-title">🟢 ESCAPE VECTORS</div>
              <div className="readout-box">
                <div className="telemetry-label">RECOMMENDED ESCAPE DIRECTION</div>
                <div className="readout-large readout-green">
                  {alert?.evacuation_direction || "NE"}
                </div>
              </div>
              <div className="telemetry-row">
                <span className="telemetry-label">SAFE DISTANCE TARGET</span>
                <span className="telemetry-val">&gt; 10 Kilometers</span>
              </div>
              <button 
                className="voice-replay-btn" 
                onClick={() => alert && speakEvacuation(alert)}
                style={{ marginTop: "10px" }}
              >
                🎙️ REPLAY ESCAPE AUDIO
              </button>
            </div>

            {/* SAFE ZONE DIRECTIVES */}
            <div className="hud-panel" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
              <div className="hud-panel-title">🛡️ VERIFIED REFUGE ZONES</div>
              <div style={{ flex: 1, overflowY: "auto" }}>
                {alert?.safety_zones && alert.safety_zones.map((zone, idx) => (
                  <div key={idx} className="safe-zone-card">
                    <div className="safe-zone-name">🟢 {zone.name}</div>
                    <div className="safe-zone-details">
                      <span>DISTANCE: {zone.distance_km}km</span>
                      <span>DIRECTION: {zone.direction}</span>
                    </div>
                  </div>
                )) || (
                  <div style={{ color: "#64748b", fontSize: "0.85rem", fontStyle: "italic", textAlign: "center", marginTop: "20px" }}>
                    Loading safe zone vectors...
                  </div>
                )}
              </div>
            </div>
          </aside>

          {/* MAIN INTERACTIVE LEAFLET MAP AREA */}
          <main className="emergency-map-area">
            <MapContainer
              center={[20.5937, 78.9629]}
              zoom={6}
              style={{ height: "100%" }}
            >
              <TileLayer
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              />

              <AutoZoom alert={alert} />
              <HeatmapLayer events={events} />

              {events.map(e => (
                <Circle
                  key={e.id}
                  center={[e.lat, e.lon]}
                  radius={5000 * spreadScale}
                  pathOptions={{
                    color: getColor(e.severity),
                    fillOpacity: 0.4
                  }}
                />
              ))}

              {alert && (
                <Marker position={[alert.lat, alert.lon]} icon={userIcon}>
                  <Popup>
                    <b>📍 Evacuating User Location</b><br />
                    Coordinates: {alert.lat.toFixed(4)}, {alert.lon.toFixed(4)}
                  </Popup>
                </Marker>
              )}

              {alert && alert.route && (
                <Polyline
                  positions={alert.route.coordinates.map(coord => [coord[1], coord[0]])}
                  pathOptions={{ color: "lime", weight: 6, opacity: 0.85 }}
                />
              )}

              {alert && alert.fire_polygon && (
                <Polygon
                  positions={alert.fire_polygon.coordinates[0].map(coord => [coord[1], coord[0]])}
                  pathOptions={{ color: "red", fillColor: "red", fillOpacity: 0.35, weight: 3 }}
                />
              )}

              {alert && alert.safety_zones && alert.safety_zones.map((zone, idx) => (
                <Marker key={idx} position={[zone.lat, zone.lon]} icon={safeZoneIcon}>
                  <Popup>
                    <b>🟢 Evacuation Safe Zone ({zone.distance_km}km)</b><br />
                    Direction: {zone.direction}
                  </Popup>
                </Marker>
              ))}
            </MapContainer>

            {/* FULLSCREEN POPUP MODAL OVERLAY */}
            {alert && showOverlay && (
              <div className="alert-box-overlay">
                <div style={{ fontSize: "4.5rem", marginBottom: "10px" }}>🚨</div>
                <h1 className="alert-main-title">CRITICAL ALARM</h1>
                <h2 className="alert-sub-title">FOREST FIRE DETECTED IN PROXIMITY</h2>
                <div style={{ color: "#fecaca", fontSize: "1.1rem", marginBottom: "25px", lineHeight: "1.6", maxWidth: "420px", marginLeft: "auto", marginRight: "auto" }}>
                  Active fire registered in <strong style={{ color: "#fff" }}>{alert.district}</strong>. Recommended evacuation escape direction is <strong style={{ color: "#00ff95", fontSize: "1.2rem" }}>{alert.evacuation_direction || "NE"}</strong>.
                </div>
                <button className="dismiss-overlay-btn" onClick={handleAcknowledgeAlert}>
                  Acknowledge Warning
                </button>
              </div>
            )}
          </main>

        </div>
      </div>
    </div>
  );
}
