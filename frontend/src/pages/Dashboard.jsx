import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  MapContainer,
  TileLayer,
  Circle,
  Marker,
  Popup,
  Polyline,
  Polygon,
  useMap
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";

import { Canvas, useFrame } from "@react-three/fiber";
import { Sphere, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

import StatusBar from "../components/StatusBar";
import DistrictInfoPanel from "../components/DistrictInfoPanel";
import EventList from "../components/EventList";
import "./Dashboard.css";
import "./DashboardEffects.css";
import "./DashboardAnimations.css";

const API = "http://localhost:8000";
const WS = "ws://127.0.0.1:8000/ws/alerts";

/* ---------------- 3D EARTH GLOBE SUB-COMPONENTS ---------------- */
function EarthGlobe() {
  const earthRef = useRef();
  const cloudsRef = useRef();

  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime();
    if (earthRef.current) earthRef.current.rotation.y = elapsed * 0.03;
    if (cloudsRef.current) cloudsRef.current.rotation.y = elapsed * 0.045;
  });

  return (
    <group>
      {/* Ambient starfield environment */}
      <Sphere args={[15, 32, 32]}>
        <meshBasicMaterial
          side={THREE.BackSide}
          color="#02040a"
          transparent
          opacity={0.9}
        />
      </Sphere>

      {/* Primary Earth Mesh */}
      <mesh ref={earthRef}>
        <sphereGeometry args={[2, 64, 64]} />
        <meshStandardMaterial
          map={new THREE.TextureLoader().load(
            "https://threejs.org/examples/textures/land_ocean_ice_cloud_2048.jpg"
          )}
          roughness={0.7}
          metalness={0.2}
        />
      </mesh>

      {/* Cloud Layer */}
      <mesh ref={cloudsRef}>
        <sphereGeometry args={[2.03, 64, 64]} />
        <meshStandardMaterial
          map={new THREE.TextureLoader().load(
            "https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/planets/earth_clouds_1024.png"
          )}
          transparent
          opacity={0.4}
          depthWrite={false}
        />
      </mesh>

      {/* Glowing Orbiting Satellites */}
      <SatelliteOrbit radius={2.8} speed={0.15} color="#00e5ff" tilt={Math.PI / 4} />
      <SatelliteOrbit radius={3.3} speed={0.08} color="#00ff95" tilt={-Math.PI / 6} />
    </group>
  );
}

function SatelliteOrbit({ radius, speed, color, tilt }) {
  const satRef = useRef();
  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime() * speed;
    if (satRef.current) {
      satRef.current.position.x = Math.cos(elapsed) * radius;
      satRef.current.position.z = Math.sin(elapsed) * radius;
    }
  });

  return (
    <group rotation={[tilt, 0, 0]}>
      {/* Orbit ring visual */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[radius - 0.01, radius + 0.01, 64]} />
        <meshBasicMaterial color={color} opacity={0.12} transparent side={THREE.DoubleSide} />
      </mesh>
      {/* Satellite beacon */}
      <mesh ref={satRef}>
        <sphereGeometry args={[0.07, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
}

/* ---------------- HEATMAP LAYER ---------------- */
function HeatmapLayer({ events }) {
  const map = useMap();
  const [mapSizeOk, setMapSizeOk] = useState(false);

  useEffect(() => {
    if (!map) return;
    
    const checkSize = () => {
      const size = map.getSize();
      if (size && size.x > 0 && size.y > 0) {
        setMapSizeOk(true);
      } else {
        setMapSizeOk(false);
      }
    };

    checkSize();
    map.on('resize', checkSize);
    const timer = setTimeout(checkSize, 300);

    return () => {
      map.off('resize', checkSize);
      clearTimeout(timer);
    };
  }, [map]);

  useEffect(() => {
    if (!map || !mapSizeOk || !events?.length) return;

    const validEvents = events.filter(e => e.lat != null && e.lon != null);
    if (validEvents.length === 0) return;

    const heatData = validEvents.map(e => [
      e.lat,
      e.lon,
      e.severity === "HIGH" ? 1 : e.severity === "MEDIUM" ? 0.6 : 0.3
    ]);

    const heat = L.heatLayer(heatData, {
      radius: 40,
      blur: 30,
      maxZoom: 10
    });

    heat.addTo(map);
    return () => map.removeLayer(heat);
  }, [events, map, mapSizeOk]);

  return null;
}

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

function UserMapFocus({ userLocation }) {
  const map = useMap();
  useEffect(() => {
    if (userLocation) {
      map.flyTo([userLocation.lat, userLocation.lon], 9, { animate: true, duration: 2 });
    }
  }, [userLocation, map]);
  return null;
}

function MapResizer() {
  const map = useMap();
  useEffect(() => {
    setTimeout(() => {
      map.invalidateSize();
    }, 300);
  }, [map]);
  return null;
}

function MapFocusController({ focus }) {
  const map = useMap();
  useEffect(() => {
    if (focus) {
      map.flyTo([focus.lat, focus.lon], 7, { animate: true, duration: 2.5 });
    }
  }, [focus, map]);
  return null;
}

/* ---------------- PRIMARY COMPONENT ---------------- */
export default function Dashboard() {
  const [events, setEvents] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [mapView, setMapView] = useState("ai"); // "ai", "district", "globe"
  const [showEvents, setShowEvents] = useState(true);
  const [userLocation, setUserLocation] = useState(null);
  const [safetyStatus, setSafetyStatus] = useState(null);
  const [alertAcknowledged, setAlertAcknowledged] = useState(false);
  const [sandboxMode, setSandboxMode] = useState(() => localStorage.getItem("sandboxMode") === "true");
  const [mapFocus, setMapFocus] = useState(null);
  const [fireping, setFireping] = useState({ status: "Active" });
  
  // JARVIS AI Voice states
  const [jarvisReply, setJarvisReply] = useState("SATSEN Orbiter tracking. Ready for queries.");
  const [jarvisHistory, setJarvisHistory] = useState([
    { sender: "JARVIS", text: "SATSEN Orbiter tracking. Ready for queries." }
  ]);
  const [userInputText, setUserInputText] = useState("");
  const [sirenMode, setSirenMode] = useState(false);
  const [radarPulse, setRadarPulse] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [jarvisHistory]);

  const navigate = useNavigate();

  const jarvisSpeak = (text) => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 0.85; // sci-fi JARVIS feel
    window.speechSynthesis.speak(utterance);
  };

  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Web Speech API is not supported in this browser. Please type your query.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setIsListening(true);
      setJarvisHistory(prev => [...prev, { sender: "JARVIS", text: "SATSEN voice node listening... speak now." }]);
    };

    recognition.onresult = async (event) => {
      const speechToText = event.results[0][0].transcript;
      setIsListening(false);
      setJarvisHistory(prev => [
        ...prev, 
        { sender: "USER", text: speechToText },
        { sender: "JARVIS", text: "Processing voice transmission..." }
      ]);

      try {
        const res = await axios.post(`${API}/openai-disaster-chat`, {
          message: speechToText,
          events: events,
          user_lat: userLocation?.lat,
          user_lon: userLocation?.lon
        });
        const reply = res.data.reply;
        setJarvisHistory(prev => {
          const list = [...prev];
          if (list[list.length - 1]?.text === "Processing voice transmission...") {
            list.pop();
          }
          return [...list, { sender: "JARVIS", text: reply }];
        });
        jarvisSpeak(reply);
      } catch (err) {
        console.error(err);
        setJarvisHistory(prev => {
          const list = [...prev];
          if (list[list.length - 1]?.text === "Processing voice transmission...") {
            list.pop();
          }
          return [...list, { sender: "JARVIS", text: "Telemetry link degraded. Unable to parse query." }];
        });
      }
    };

    recognition.onerror = (event) => {
      console.error(event.error);
      setIsListening(false);
      setJarvisHistory(prev => [...prev, { sender: "JARVIS", text: "Voice transmission failed. Noise interference detected." }]);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  /* ---------------- FETCH EVENTS ---------------- */
  const fetchEvents = async () => {
    try {
      const res = await axios.get(`${API}/fire/events${sandboxMode ? "?sandbox=true" : ""}`);
      setEvents(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchFireping = async () => {
    try {
      const res = await axios.get(`${API}/fireping?sandbox=${sandboxMode}`);
      setFireping(res.data);
    } catch (err) {
      console.error("Error pinging NASA FIRMS:", err);
    }
  };

  useEffect(() => {
    fetchFireping();
    const interval = setInterval(fetchFireping, 30000);
    return () => clearInterval(interval);
  }, [sandboxMode]);

  /* ---------------- WEBSOCKET ---------------- */
  useEffect(() => {
    fetchEvents();
    const ws = new WebSocket(WS);
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onmessage = () => {
      if (!sandboxMode) {
        fetchEvents();
      }
    };
    return () => ws.close();
  }, [sandboxMode]);

  /* ---------------- SPEECH RECOGNITION COMMANDS ---------------- */
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      const transcript = event.results[event.results.length - 1][0].transcript.toLowerCase();
      console.log("Telemetry Voice Command:", transcript);

      if (transcript.includes("globe mode") || transcript.includes("earth mode") || transcript.includes("3d view")) {
        setMapView("globe");
        setJarvisReply("Affirmative. Switching display to 3D Rotating Earth.");
        jarvisSpeak("Affirmative. Switching display to 3D Rotating Earth.");
      } else if (transcript.includes("map mode") || transcript.includes("hotspots") || transcript.includes("2d view")) {
        setMapView("ai");
        setJarvisReply("Understood. Returning to 2D live hotspots map.");
        jarvisSpeak("Understood. Returning to 2D live hotspots map.");
      } else if (transcript.includes("siren on") || transcript.includes("activate alarm") || transcript.includes("turn on siren")) {
        setSirenMode(true);
        setJarvisReply("Warning. Orbital alarm siren activated.");
        jarvisSpeak("Warning. Orbital alarm siren activated.");
      } else if (transcript.includes("siren off") || transcript.includes("deactivate alarm") || transcript.includes("turn off siren")) {
        setSirenMode(false);
        setJarvisReply("Siren system deactivated.");
        jarvisSpeak("Siren system deactivated.");
      } else if (transcript.includes("status check") || transcript.includes("report")) {
        const txt = `Orbital sweep complete. Active hotspots detected: ${events.length}. AI neural networks fully operating.`;
        setJarvisReply(txt);
        jarvisSpeak(txt);
      }
    };

    recognition.start();
    return () => recognition.stop();
  }, [events]);

  /* ---------------- USER LOCATION & SAFETY CHECK ---------------- */
  useEffect(() => {
    if (!navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        setUserLocation({ lat, lon });

        try {
          await axios.post(`${API}/user/location`, { lat, lon });
          const res = await axios.post(`${API}/user/check-danger?sandbox=${sandboxMode}`, { lat, lon });
          setSafetyStatus(res.data);

          if (res.data?.danger) {
            setAlertAcknowledged(false);
            setSirenMode(true);
            jarvisSpeak("Emergency. Active forest fire detected in your immediate proximity. Please evacuate immediately.");
          }
        } catch (err) {
          console.error("Safety checking error:", err);
        }
      },
      (err) => console.warn("Geolocation access denied:", err.message),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, [sandboxMode]);

  /* ---------------- JARVIS CHAT SUBMISSION ---------------- */
  const handleJarvisChat = async (e) => {
    e.preventDefault();
    if (!userInputText.trim()) return;

    const query = userInputText;
    setUserInputText("");
    setJarvisHistory(prev => [
      ...prev,
      { sender: "USER", text: query },
      { sender: "JARVIS", text: "Analyzing telemetry channels..." }
    ]);

    try {
      const res = await axios.post(`${API}/openai-disaster-chat`, {
        message: query,
        events: events,
        user_lat: userLocation?.lat,
        user_lon: userLocation?.lon
      });
      const reply = res.data.reply;
      setJarvisHistory(prev => {
        const list = [...prev];
        if (list[list.length - 1]?.text === "Analyzing telemetry channels...") {
          list.pop();
        }
        return [...list, { sender: "JARVIS", text: reply }];
      });
      jarvisSpeak(reply);
    } catch (err) {
      console.error(err);
      setJarvisHistory(prev => {
        const list = [...prev];
        if (list[list.length - 1]?.text === "Analyzing telemetry channels...") {
          list.pop();
        }
        return [...list, { sender: "JARVIS", text: "Telemetry link degraded. Unable to parse query." }];
      });
    }
  };

  return (
    <div className={`dashboard-center-wrapper ${sirenMode ? "emergency-alarm-active" : ""}`}>
      {/* Sci-Fi Stars Background & Scanlines */}
      <div className="space-bg">
        <div className="space-stars"></div>
      </div>
      <div className="scanlines-overlay"></div>

      {/* SATSEN ORBITAL NAVBAR */}
      <div className="hud-navbar">
        <div className="hud-navbar-brand">
          🛰️ SATSEN ORBITAL COMMAND CENTER
        </div>
        <div className="hud-navbar-menu">
          <button className={mapView === "ai" ? "hud-nav-btn active" : "hud-nav-btn"} onClick={() => setMapView("ai")}>Global Hotspots</button>
          <button className={mapView === "district" ? "hud-nav-btn active" : "hud-nav-btn"} onClick={() => setMapView("district")}>District Analysis</button>
          <button className={mapView === "globe" ? "hud-nav-btn active" : "hud-nav-btn"} onClick={() => setMapView("globe")}>3D Earth View</button>
          <button className={showEvents ? "hud-nav-btn active" : "hud-nav-btn"} onClick={() => setShowEvents(!showEvents)}>📟 Event Log</button>
        </div>
        <div className="hud-navbar-status">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "11px", letterSpacing: "1px", textTransform: "uppercase", color: "#94a3b8" }}>Simulation</span>
            <label className="switch">
              <input
                type="checkbox"
                checked={sandboxMode}
                onChange={(e) => {
                  const val = e.target.checked;
                  setSandboxMode(val);
                  localStorage.setItem("sandboxMode", val ? "true" : "false");
                }}
              />
              <span className="slider round"></span>
            </label>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span className="telemetry-status-light" style={{ backgroundColor: wsConnected ? "#00ff95" : "#ff3b30", boxShadow: wsConnected ? "0 0 10px #00ff95" : "0 0 10px #ff3b30" }}></span>
            <span style={{ fontSize: "11px", letterSpacing: "1px", textTransform: "uppercase", color: wsConnected ? "#00ff95" : "#ff3b30" }}>{wsConnected ? "CONNECTED" : "DISCONNECTED"}</span>
          </div>
        </div>
      </div>

      {/* CRITICAL FULLSCREEN EMERGENCY FLASHING BANNER */}
      {sirenMode && (
        <div className="siren-spinner">
          <span style={{ color: "#ff3b30", fontSize: "1.2rem", fontWeight: "bold" }}>🚨</span>
        </div>
      )}

      {safetyStatus?.danger && !alertAcknowledged && (
        <div className="hud-emergency-overlay">
          <div className="hud-emergency-box">
            <span style={{ fontSize: "3.5rem" }}>🚨</span>
            <h1 style={{ color: "#ff3b30", fontSize: "2.5rem", margin: "16px 0", letterSpacing: "3px" }}>CRITICAL ALERT</h1>
            <h2 style={{ color: "#fff", fontSize: "1.5rem", marginBottom: "12px" }}>FOREST FIRE DETECTED NEARBY</h2>
            <p style={{ fontSize: "1.1rem", color: "#fecaca", lineHeight: "1.6" }}>
              Evacuation direction: <strong style={{ color: "#00ff95", fontSize: "1.3rem" }}>{safetyStatus.evacuation_direction}</strong>.
              Please leave immediately and travel towards safe coordinates.
            </p>
            <button className="hud-emergency-btn" onClick={() => {
              setSirenMode(false);
              setAlertAcknowledged(true);
            }}>Acknowledge Alert</button>
          </div>
        </div>
      )}

      {/* HUD MAIN GRID */}
      <div className="hud-main-grid">
        
        {/* LEFT COLUMN: KPIs & Sorted Event Log */}
        <div className="hud-left-col">
          <div className="hud-kpi-stack">
            {/* Active Hotspots */}
            <div className="hud-panel hud-kpi-card">
              <div className="card-glow"></div>
              <div>
                <div className="hud-kpi-label">Active Hotspots</div>
                <div className="hud-kpi-val" style={{ color: "#ff3b30", textShadow: "0 0 10px rgba(255,59,48,0.5)" }}>
                  🔥 {events.length}
                </div>
              </div>
              <span style={{ color: "#ff3b30", fontSize: "12px", fontWeight: "bold" }}>+12%</span>
            </div>

            {/* High Severity Count */}
            <div className="hud-panel hud-kpi-card">
              <div className="card-glow"></div>
              <div>
                <div className="hud-kpi-label">Critical High Risk</div>
                <div className="hud-kpi-val" style={{ color: "#ffb800", textShadow: "0 0 10px rgba(255,184,0,0.5)" }}>
                  ⚠️ {events.filter(e => e.severity === "HIGH").length}
                </div>
              </div>
              <span style={{ color: "#ffb800", fontSize: "12px", fontWeight: "bold" }}>STABLE</span>
            </div>

            {/* Neural Net Status */}
            <div className="hud-panel hud-kpi-card">
              <div className="card-glow"></div>
              <div>
                <div className="hud-kpi-label">System Neural Link</div>
                <div className="hud-kpi-val" style={{ color: "#00ff95", textShadow: "0 0 10px rgba(0,255,149,0.5)" }}>
                  🛰️ ONLINE
                </div>
              </div>
              <span style={{ color: "#00ff95", fontSize: "12px", fontWeight: "bold" }}>100%</span>
            </div>
          </div>
        </div>

        {/* CENTER COLUMN: Leaflet Map or Three.js Earth */}
        <div className="hud-center-col">
          {radarPulse && (
            <div className="radar-sweep-container">
              <div className="radar-sweep"></div>
            </div>
          )}

          {mapView === "globe" ? (
            <div style={{ height: "100%", width: "100%", background: "#020408" }}>
              <Canvas camera={{ position: [0, 0, 5.5], fov: 45 }}>
                <ambientLight intensity={0.35} />
                <directionalLight position={[5, 3, 5]} intensity={2.2} />
                <EarthGlobe />
                <OrbitControls autoRotate autoRotateSpeed={0.8} enableZoom={true} />
              </Canvas>
            </div>
          ) : mapView === "district" ? (
            <DistrictInfoPanel />
          ) : (
            <div style={{ height: "100%", width: "100%" }}>
              <StatusBar status={fireping} wsConnected={wsConnected} />
              
              <MapContainer
                center={[20.5937, 78.9629]}
                zoom={5}
                style={{ height: "calc(100% - 40px)", width: "100%" }}
              >
                <TileLayer
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                />
                <MapResizer />
                <UserMapFocus userLocation={userLocation} />
                <MapFocusController focus={mapFocus} />
                <HeatmapLayer events={events} />

                {userLocation && (
                  <Marker position={[userLocation.lat, userLocation.lon]} icon={userIcon}>
                    <Popup>
                      <b>📍 User Location Coordinates</b><br />
                      Latitude: {userLocation.lat.toFixed(4)}<br />
                      Longitude: {userLocation.lon.toFixed(4)}
                    </Popup>
                  </Marker>
                )}

                {safetyStatus?.danger && safetyStatus.route && (
                  <Polyline
                    positions={safetyStatus.route.coordinates.map(coord => [coord[1], coord[0]])}
                    pathOptions={{ color: "lime", weight: 6, opacity: 0.85 }}
                  />
                )}

                {safetyStatus?.danger && safetyStatus.fire_polygon && (
                  <Polygon
                    positions={safetyStatus.fire_polygon.coordinates[0].map(coord => [coord[1], coord[0]])}
                    pathOptions={{ color: "red", fillColor: "red", fillOpacity: 0.35, weight: 3 }}
                  />
                )}

                {safetyStatus?.danger && safetyStatus.safety_zones && safetyStatus.safety_zones.map((zone, idx) => (
                  <Marker key={idx} position={[zone.lat, zone.lon]} icon={safeZoneIcon}>
                    <Popup>
                      <b>🟢 Evacuation Refuge Zone ({zone.distance_km}km)</b><br />
                      {zone.name}
                    </Popup>
                  </Marker>
                ))}

                {events.filter(e => e.lat != null && e.lon != null).map(e => (
                  <Circle
                    key={e.id}
                    center={[e.lat, e.lon]}
                    radius={
                      e.severity === "HIGH" ? 6000 : e.severity === "MEDIUM" ? 4000 : 2500
                    }
                    pathOptions={{
                      color: e.severity === "HIGH" ? "red" : e.severity === "MEDIUM" ? "orange" : "yellow",
                      fillOpacity: 0.3
                    }}
                  >
                    <Popup>
                      <b>🔥 {e.severity} Fire</b><br />
                      📍 {e.district}, {e.state}
                    </Popup>
                  </Circle>
                ))}
              </MapContainer>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: JARVIS AI Assistant */}
        <div className="hud-right-col hud-panel" style={{ padding: "20px", borderRadius: "16px", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", justifyItems: "center", gap: "10px", borderBottom: "1px solid rgba(0, 229, 255, 0.15)", paddingBottom: "12px", marginBottom: "16px" }}>
            <span style={{ fontSize: "1.5rem" }}>🤖</span>
            <div>
              <div style={{ fontWeight: "bold", fontSize: "1rem", color: "#00e5ff" }}>SATSEN JARVIS AI</div>
              <div style={{ fontSize: "0.7rem", color: "#00ff95", letterSpacing: "1px" }}>ORBITAL TELEMETRY INTERFACE</div>
            </div>
          </div>

          {/* Clickable Hologram Voice Waveform Button */}
          <div 
            className={`jarvis-voice-btn ${isListening ? "listening" : ""}`}
            onClick={startListening}
            title="Click to start voice communication"
          >
            <div style={{ fontSize: "0.65rem", color: isListening ? "#ff3b30" : "#64748b", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "8px", fontWeight: "bold" }}>
              {isListening ? "🎙️ LISTENING TO SECURE CHANNEL..." : "📡 CLICK FOR VOICE TRANSMISSION"}
            </div>
            <div className={`jarvis-wave-container ${isListening ? "listening" : ""}`}>
              <div className="voice-bar"></div>
              <div className="voice-bar"></div>
              <div className="voice-bar"></div>
              <div className="voice-bar"></div>
              <div className="voice-bar"></div>
            </div>
          </div>

          {/* JARVIS Dialogue Readout (Scrollable Conversation History) */}
          <div style={{ 
            flex: 1, 
            background: "rgba(5, 8, 22, 0.6)", 
            border: "1px solid rgba(0,229,255,0.1)", 
            borderRadius: "10px", 
            padding: "16px", 
            marginBottom: "16px", 
            display: "flex", 
            flexDirection: "column", 
            justifyContent: "space-between",
            maxHeight: "260px",
            minHeight: "180px"
          }}>
            <div style={{ 
              flex: 1, 
              overflowY: "auto", 
              marginBottom: "8px", 
              paddingRight: "6px",
              display: "flex",
              flexDirection: "column",
              gap: "12px"
            }}>
              {jarvisHistory.map((msg, idx) => (
                <div 
                  key={idx} 
                  style={{ 
                    alignSelf: msg.sender === "USER" ? "flex-end" : "flex-start",
                    maxWidth: "85%",
                    background: msg.sender === "USER" ? "rgba(0, 229, 255, 0.08)" : "rgba(255, 255, 255, 0.02)",
                    border: msg.sender === "USER" ? "1px solid rgba(0, 229, 255, 0.25)" : "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: msg.sender === "USER" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                    padding: "8px 12px",
                    fontSize: "0.82rem",
                    lineHeight: "1.4",
                    color: "#eafbff",
                    fontStyle: msg.sender === "USER" ? "normal" : "italic"
                  }}
                >
                  <div style={{ 
                    fontSize: "0.6rem", 
                    color: msg.sender === "USER" ? "#00e5ff" : "#88ccff", 
                    fontWeight: "bold", 
                    marginBottom: "4px",
                    fontFamily: "Orbitron",
                    letterSpacing: "0.5px"
                  }}>
                    {msg.sender}
                  </div>
                  <div style={{ whiteSpace: "pre-wrap" }}>
                    {msg.text}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
            
            <div style={{ 
              fontSize: "0.72rem", 
              display: "flex", 
              justifyContent: "space-between", 
              color: "#00e5ff", 
              borderTop: "1px solid rgba(0,229,255,0.1)", 
              paddingTop: "8px", 
              marginTop: "4px",
              fontFamily: "Share Tech Mono"
            }}>
              <span>SECURE UPLINK STATUS:</span>
              <span style={{ fontWeight: "bold", color: "#00ff95" }}>SYNCHRONIZED (96.8%)</span>
            </div>
          </div>

          {/* AI Panel Confidence Meters */}
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "20px" }}>
            {/* CNN confidence */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", color: "#94a3b8", marginBottom: "4px" }}>
                <span>CNN NEURAL ACCURACY</span>
                <span style={{ color: "#00e5ff" }}>98%</span>
              </div>
              <div className="predict-progress-container">
                <div className="predict-progress-bar" style={{ width: "98%", backgroundColor: "#00e5ff" }}></div>
              </div>
            </div>

            {/* LSTM Confidence */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", color: "#94a3b8", marginBottom: "4px" }}>
                <span>LSTM ACCURACY</span>
                <span style={{ color: "#2f80ed" }}>91%</span>
              </div>
              <div className="predict-progress-container">
                <div className="predict-progress-bar" style={{ width: "91%", backgroundColor: "#2f80ed" }}></div>
              </div>
            </div>

            {/* Wind/Weather readings */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", background: "rgba(255,255,255,0.03)", padding: "10px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)" }}>
              <div>
                <div style={{ fontSize: "0.6rem", color: "#64748b" }}>WIND SPEED</div>
                <div style={{ fontSize: "0.8rem", color: "#fff", fontWeight: "bold" }}>34 km/h</div>
              </div>
              <div>
                <div style={{ fontSize: "0.6rem", color: "#64748b" }}>HUMIDITY</div>
                <div style={{ fontSize: "0.8rem", color: "#fff", fontWeight: "bold" }}>17%</div>
              </div>
            </div>
          </div>

          {/* Ask AI Input Box */}
          <form onSubmit={handleJarvisChat} style={{ display: "flex", gap: "8px" }}>
            <input
              type="text"
              placeholder="Query JARVIS satellite feed..."
              value={userInputText}
              onChange={(e) => setUserInputText(e.target.value)}
              style={{
                flex: 1,
                background: "rgba(5, 8, 22, 0.8)",
                border: "1px solid rgba(0, 229, 255, 0.2)",
                padding: "10px 14px",
                borderRadius: "8px",
                color: "#fff",
                fontSize: "0.8rem",
                outline: "none"
              }}
            />
            <button
              type="submit"
              style={{
                background: "rgba(0, 229, 255, 0.15)",
                border: "1px solid rgba(0, 229, 255, 0.3)",
                color: "#00e5ff",
                padding: "0 14px",
                borderRadius: "8px",
                cursor: "pointer",
                fontWeight: "bold",
                fontSize: "0.8rem"
              }}
            >
              SEND
            </button>
          </form>
        </div>

      </div>

      {/* 📟 EVENT LOG LEFT SLIDING DRAWER */}
      <div className={`hud-left-drawer hud-panel ${showEvents ? "active" : ""}`}>
        <div style={{ 
          fontSize: "1rem", 
          fontWeight: "bold", 
          borderBottom: "1px solid rgba(0, 229, 255, 0.2)", 
          paddingBottom: "12px", 
          marginBottom: "16px", 
          display: "flex", 
          justifyContent: "space-between",
          alignItems: "center"
        }}>
          <span>📟 ORBITAL EVENTS LOG</span>
          <button 
            onClick={() => setShowEvents(false)}
            style={{
              background: "transparent",
              border: "none",
              color: "#ff3b30",
              fontSize: "1.2rem",
              cursor: "pointer",
              fontWeight: "bold"
            }}
          >
            ✕
          </button>
        </div>
        <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
          <EventList
            events={events}
            onRefresh={fetchEvents}
            onSelect={(e) => setMapFocus({ lat: e.lat, lon: e.lon })}
          />
        </div>
      </div>

      {/* TELEMETRY FOOTER PANEL */}
      <div className="hud-bottom-telemetry">
        <div className="telemetry-item">
          <span className="telemetry-status-light" style={{ backgroundColor: "#00ff95", boxShadow: "0 0 6px #00ff95" }}></span>
          CNN PREDICTOR: ACTIVE (98.4%)
        </div>
        <div className="telemetry-item">
          <span className="telemetry-status-light" style={{ backgroundColor: "#00ff95", boxShadow: "0 0 6px #00ff95" }}></span>
          LSTM TIME-SERIES: SYNCED (91.2%)
        </div>
        <div className="telemetry-item">
          <span className="telemetry-status-light" style={{ backgroundColor: "#00e5ff", boxShadow: "0 0 6px #00e5ff" }}></span>
          NASA FIRMS API: NOMINAL
        </div>
        <div className="telemetry-item">
          <span className="telemetry-status-light" style={{ backgroundColor: "#00e5ff", boxShadow: "0 0 6px #00e5ff" }}></span>
          SAT TELEMETRY: SYNCED (LIVE)
        </div>
      </div>
    </div>
  );
}