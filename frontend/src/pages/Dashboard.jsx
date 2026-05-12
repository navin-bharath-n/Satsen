import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  MapContainer,
  TileLayer,
  Circle,
  Marker,
  Popup,
  useMap
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";

import AIAssistant from "../components/AIAssistant";
import StatusBar from "../components/StatusBar";
import DistrictInfoPanel from "../components/DistrictInfoPanel";
import EventList from "../components/EventList"; // ✅ ADDED
import DeforestationPanel from "../components/DeforestationPanel";
import "./Dashboard.css";

const API = "http://localhost:8000";
const WS = "ws://127.0.0.1:8000/ws/alerts";

/* ---------------- HEATMAP ---------------- */
function HeatmapLayer({ events }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !events?.length) return;

    const validEvents = events.filter(e => e.lat != null && e.lon != null);

    if (validEvents.length === 0) return;

    const heatData = validEvents.map(e => [
      e.lat,
      e.lon,
      e.severity === "HIGH" ? 1 :
        e.severity === "MEDIUM" ? 0.6 : 0.3
    ]);

    const heat = L.heatLayer(heatData, {
      radius: 40,
      blur: 30,
      maxZoom: 10
    });

    heat.addTo(map);
    return () => map.removeLayer(heat);
  }, [events, map]);

  return null;
}

export default function Dashboard() {

  const [events, setEvents] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [mapView, setMapView] = useState("ai");
  const [showEvents, setShowEvents] = useState(false); // ✅ ADDED

  const navigate = useNavigate();
  const emergencyTriggered = useRef(false);

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
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onmessage = fetchEvents;

    return () => ws.close();
  }, []);

  return (
    <div className="dashboard">

      {/* HEADER */}
      <div className="dashboard-header">
        <h1>🛰️ AI Powered Satellite Monitoring System</h1>
      </div>

      {/* BUTTON CONTROLS */}
      <div className="map-toggle-buttons">
        <button
          className={mapView === "ai" ? "active-btn" : ""}
          onClick={() => setMapView("ai")}
        >
          🛰️ Global Fire Map
        </button>

        <button
          className={mapView === "district" ? "active-btn" : ""}
          onClick={() => setMapView("district")}
        >
          📍 District Info Map
        </button>

        <button
          className={mapView === "deforestation" ? "active-btn" : ""}
          onClick={() => setMapView("deforestation")}
        >
          🌳 Deforestation Analytics
        </button>

        

        {/* ✅ NEW EVENT LIST BUTTON */}
        <button
          className={showEvents ? "active-btn" : ""}
          onClick={() => setShowEvents(!showEvents)}
        >
          📟 Event Log
        </button>
      </div>

      {/* MAP SECTION */}
      <div className="map-section">

        {/* AI MAP */}
        {mapView === "ai" && (
          <>
            <StatusBar status={{ ml: "Active" }} wsConnected={wsConnected} />

            <MapContainer
              center={[20.5937, 78.9629]}
              zoom={5}
              style={{ height: "80vh" }}
            >
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              />

              <HeatmapLayer events={events} />

              {events.filter(e => e.lat != null && e.lon != null).map(e => (
                <Circle
                  key={e.id}
                  center={[e.lat, e.lon]}
                  radius={
                    e.severity === "HIGH" ? 6000 :
                      e.severity === "MEDIUM" ? 4000 : 2500
                  }
                  pathOptions={{
                    color:
                      e.severity === "HIGH" ? "red" :
                        e.severity === "MEDIUM" ? "orange" :
                          "yellow",
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
          </>
        )}

        {/* DISTRICT MAP */}
        {mapView === "district" && (
          <DistrictInfoPanel />
        )}

        {/* DEFORESTATION MAP */}
        {mapView === "deforestation" && (
          <DeforestationPanel />
        )}

      </div>

      {/* ✅ EVENT LIST SECTION (DOES NOT AFFECT MAP) */}
      {showEvents && (
        <div className="event-list-container">
          <EventList events={events} onRefresh={fetchEvents} />
        </div>
      )}

      {/* AI ASSISTANT ALWAYS VISIBLE */}
      <AIAssistant events={events} />

    </div>
  );
}