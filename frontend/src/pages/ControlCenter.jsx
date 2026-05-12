import { useEffect, useState, useRef } from "react";
import axios from "axios";
import {
  MapContainer,
  TileLayer,
  Circle,
  Marker,
  Popup
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import { Canvas } from "@react-three/fiber";
import { Sphere, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

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
    const res = await axios.get(`${API}/fire/events`);
    setEvents(res.data || []);
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

  /* ---------------- FIRE SPREAD ANIMATION ---------------- */
  useEffect(() => {
    const interval = setInterval(() => {
      setSpreadScale((prev) => (prev >= 2 ? 1 : prev + 0.05));
    }, 200);

    return () => clearInterval(interval);
  }, []);

  /* ---------------- VOICE SPEAK ---------------- */
  const speak = (text) => {
    const msg = new SpeechSynthesisUtterance(text);
    msg.rate = 0.9;
    window.speechSynthesis.speak(msg);
  };

  /* ---------------- VOICE COMMANDS ---------------- */
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;

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

  /* ---------------- UI ---------------- */
  return (
    <div
      style={{
        height: "100vh",
        background: "#0f172a",
        color: "white",
        position: "relative",
        animation: sirenMode ? "flash 0.5s infinite" : "none"
      }}
    >
      <style>
        {`
        @keyframes flash {
          0% { background-color: #0f172a; }
          50% { background-color: #550000; }
          100% { background-color: #0f172a; }
        }
      `}
      </style>

      {/* HEADER */}
      <div
        style={{
          padding: 10,
          background: "#111827",
          display: "flex",
          justifyContent: "space-between"
        }}
      >
        <h2>🔥 AI Fire Control Center</h2>

        <div>
          <button onClick={() => setGlobeMode(!globeMode)}>
            🛰 Toggle Globe
          </button>
          <button onClick={() => setSirenMode(!sirenMode)}>
            🚨 Toggle Siren
          </button>
        </div>
      </div>

      {/* 3D GLOBE MODE */}
      {globeMode ? (
        <Canvas style={{ height: "90%" }}>
          <ambientLight intensity={1} />
          <directionalLight position={[5, 5, 5]} />
          <Sphere args={[2, 64, 64]}>
            <meshStandardMaterial
              map={new THREE.TextureLoader().load(
                "https://threejs.org/examples/textures/land_ocean_ice_cloud_2048.jpg"
              )}
            />
          </Sphere>
          <OrbitControls autoRotate autoRotateSpeed={1} />
        </Canvas>
      ) : (
        /* MAP MODE */
        <MapContainer
          center={[20.5937, 78.9629]}
          zoom={5}
          style={{ height: "90%" }}
        >
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />

          {events.map((e) => (
            <Circle
              key={e.id}
              center={[e.lat, e.lon]}
              radius={
                (e.severity === "HIGH"
                  ? 6000
                  : e.severity === "MEDIUM"
                  ? 4000
                  : 2500) * spreadScale
              }
              pathOptions={{
                color: "red",
                fillOpacity: 0.4
              }}
            >
              <Popup>
                🔥 {e.severity} Fire <br />
                📍 {e.district} <br />
                🧠 CNN: {(e.cnn_probability * 100).toFixed(1)}%
              </Popup>
            </Circle>
          ))}

          {alert && (
            <Marker position={[alert.lat, alert.lon]}>
              <Popup>
                🚨 Emergency Zone <br />
                Direction: {alert.evacuation_direction}
              </Popup>
            </Marker>
          )}
        </MapContainer>
      )}

      {/* ALERT POPUP */}
      {alert && (
        <div
          style={{
            position: "absolute",
            bottom: 20,
            left: 20,
            background: "red",
            padding: 20,
            borderRadius: 10
          }}
        >
          <h3>🚨 FIRE ALERT</h3>
          <p>{alert.message}</p>
          <p>
            🧭 Evacuate Towards: {alert.evacuation_direction}
          </p>
        </div>
      )}
    </div>
  );
}
