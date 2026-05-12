import { useEffect, useState, useRef } from "react";
import axios from "axios";
import {
  MapContainer,
  TileLayer,
  Circle,
  Polyline,
  useMap
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";

const API = "http://127.0.0.1:8000";
const WS = "ws://localhost:8000/ws/alerts";

/* ---------------- AUTO ZOOM ---------------- */
function AutoZoom({ alert }) {
  const map = useMap();

  useEffect(() => {
    if (alert?.lat && alert?.lon) {
      setTimeout(() => {
        map.flyTo([alert.lat, alert.lon], 12, {
          animate: true,
          duration: 2
        });
      }, 500);
    }
  }, [alert]);

  return null;
}

export default function EmergencyControl() {

  const [events, setEvents] = useState([]);
  const [alert, setAlert] = useState(null);
  const [spreadScale, setSpreadScale] = useState(1);
  const [flash, setFlash] = useState(false);
  const [audioReady, setAudioReady] = useState(false);

  const sirenRef = useRef(null);

  /* ---------------- INITIALIZE AUDIO ---------------- */
  useEffect(() => {
    const audio = new Audio("/siren.mp3");
    audio.loop = true;
    audio.preload = "auto";
    sirenRef.current = audio;
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
    const text =
      `Emergency alert. ${data.severity} forest fire detected.
       Evacuate immediately.`;

    const msg = new SpeechSynthesisUtterance(text);
    msg.rate = 0.9;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(msg);
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
    <div style={{
      height: "100vh",
      background: flash ? "#7f1d1d" : "#0f172a",
      color: "white",
      position: "relative",
      overflow: "hidden"
    }}>

      {/* FLASH */}
      {flash && (
        <div style={{
          position: "absolute",
          inset: 0,
          background: "rgba(255,0,0,0.4)",
          animation: "flash 1s infinite",
          zIndex: 1000
        }} />
      )}

      {/* ALERT OVERLAY */}
      {alert && (
        <div style={{
          position: "absolute",
          top: "25%",
          width: "100%",
          textAlign: "center",
          zIndex: 1100
        }}>
          <h1 style={{
            fontSize: "4rem",
            color: "red",
            textShadow: "0 0 30px red"
          }}>
            🚨 EMERGENCY ALERT 🚨
          </h1>

          <h2 style={{ fontSize: "2.5rem" }}>
            {alert.severity} FIRE
          </h2>
        </div>
      )}

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
          <Polyline
            positions={[
              [alert.lat, alert.lon],
              [alert.lat + 0.08, alert.lon + 0.08]
            ]}
            pathOptions={{ color: "lime", weight: 5 }}
          />
        )}
      </MapContainer>

      <style>{`
        @keyframes flash {
          0% {opacity: 0.2;}
          50% {opacity: 0.7;}
          100% {opacity: 0.2;}
        }
      `}</style>

    </div>
  );
}
