import { useEffect, useState, useRef } from "react";
import axios from "axios";
import {
  MapContainer,
  TileLayer,
  Circle,
  Marker,
  Popup
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";

import { Canvas } from "@react-three/fiber";
import { Sphere, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

import "./ControlCenter.css";

const API = "http://127.0.0.1:8000";
const WS = "ws://localhost:8000/ws/alerts";

export default function ControlCenter() {
  const [events, setEvents] = useState([]);
  const [alert, setAlert] = useState(null);
  const [spreadScale, setSpreadScale] = useState(1);
  const [sirenMode, setSirenMode] = useState(false);
  const [globeMode, setGlobeMode] = useState(false);

  const recognitionRef = useRef(null);

  /* ---------------- FETCH EVENTS ---------------- */

  const fetchEvents = async () => {
    try {
      const res = await axios.get(`${API}/fire/events`);
      setEvents(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  /* ---------------- WEBSOCKET ---------------- */

  useEffect(() => {
    fetchEvents();

    const ws = new WebSocket(WS);

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);

      if (data.type === "ALERT") {
        setAlert(data);
        setSirenMode(true);
        speak(data.message || "Emergency fire alert.");
      }

      fetchEvents();
    };

    return () => ws.close();
  }, []);

  /* ---------------- SPREAD ANIMATION ---------------- */

  useEffect(() => {
    const interval = setInterval(() => {
      setSpreadScale((prev) => (prev >= 2 ? 1 : prev + 0.05));
    }, 200);

    return () => clearInterval(interval);
  }, []);

  /* ---------------- SPEECH ---------------- */

  const speak = (text) => {
    const msg = new SpeechSynthesisUtterance(text);
    msg.rate = 0.9;

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(msg);
  };

  /* ---------------- VOICE COMMANDS ---------------- */

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const transcript =
        event.results[event.results.length - 1][0].transcript.toLowerCase();

      if (transcript.includes("siren off")) setSirenMode(false);

      if (transcript.includes("siren on")) setSirenMode(true);

      if (transcript.includes("globe mode")) setGlobeMode(true);

      if (transcript.includes("map mode")) setGlobeMode(false);
    };

    recognition.start();

    recognitionRef.current = recognition;

    return () => recognition.stop();
  }, []);

  return (
    <div
      className={`control-center ${sirenMode ? "siren-active" : ""
        }`}
    >
      {/* HEADER */}

      <header className="control-header">
        <h2 className="control-title">
          🔥 AI FIRE CONTROL CENTER
        </h2>

        <div className="control-actions">
          <button
            className="control-btn"
            onClick={() => setGlobeMode(!globeMode)}
          >
            🛰 {globeMode ? "Map View" : "Globe View"}
          </button>

          <button
            className="control-btn"
            onClick={() => setSirenMode(!sirenMode)}
          >
            {sirenMode ? "🔕 Siren OFF" : "🚨 Siren ON"}
          </button>
        </div>
      </header>

      {/* STATUS PANEL */}

      <div className="status-card">
        <h3>Mission Status</h3>

        <div className="status-item">
          <span>Hotspots</span>
          <span>{events.length}</span>
        </div>

        <div className="status-item">
          <span>System</span>
          <span className="online">ONLINE</span>
        </div>

        <div className="status-item">
          <span>Voice AI</span>
          <span className="online">ACTIVE</span>
        </div>

        <div className="status-item">
          <span>Siren</span>
          <span className={sirenMode ? "online" : "offline"}>
            {sirenMode ? "ACTIVE" : "OFF"}
          </span>
        </div>
      </div>

      {/* GLOBE */}

      {globeMode ? (
        <div className="globe-wrapper">
          <Canvas>
            <ambientLight intensity={1} />

            <directionalLight
              position={[5, 5, 5]}
            />

            <Sphere args={[2, 64, 64]}>
              <meshStandardMaterial
                map={new THREE.TextureLoader().load(
                  "https://threejs.org/examples/textures/land_ocean_ice_cloud_2048.jpg"
                )}
              />
            </Sphere>

            <OrbitControls
              autoRotate
              autoRotateSpeed={1}
              enableZoom
            />
          </Canvas>
        </div>
      ) : (
        <div className="map-wrapper">
          <MapContainer
            center={[20.5937, 78.9629]}
            zoom={5}
          >
            <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />

            {events.map((e) => (
              <Circle
                key={e.id}
                center={[e.lat, e.lon]}
                radius={
                  (
                    e.severity === "HIGH"
                      ? 6000
                      : e.severity === "MEDIUM"
                        ? 4000
                        : 2500
                  ) * spreadScale
                }
                pathOptions={{
                  color:
                    e.severity === "HIGH"
                      ? "red"
                      : e.severity === "MEDIUM"
                        ? "orange"
                        : "yellow",
                  fillOpacity: 0.4
                }}
              >
                <Popup>
                  <b>🔥 {e.severity} Fire</b>

                  <br />

                  📍 {e.district}

                  <br />

                  🧠 CNN:
                  {" "}
                  {(e.cnn_probability * 100).toFixed(
                    1
                  )}
                  %
                </Popup>
              </Circle>
            ))}

            {alert && (
              <Marker
                position={[alert.lat, alert.lon]}
              >
                <Popup>
                  <b>🚨 Emergency Zone</b>

                  <br />

                  Direction:
                  {" "}
                  {alert.evacuation_direction}
                </Popup>
              </Marker>
            )}
          </MapContainer>
        </div>
      )}

      {/* ALERT */}

      {alert && (
        <div className="alert-panel">
          <h2 className="alert-title">
            🚨 FIRE ALERT
          </h2>

          <p className="alert-text">
            {alert.message}
          </p>

          <p className="alert-text">
            <strong>
              Evacuate Towards:
            </strong>
            <br />
            {alert.evacuation_direction}
          </p>
        </div>
      )}
    </div>
  );
}