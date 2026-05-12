import { useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMapEvents
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./DistrictInfoPanel.css";

export default function DistrictInfoPanel() {

  const [position, setPosition] = useState(null);
  const [weather, setWeather] = useState(null);

  /* ================================
     FETCH WEATHER FROM OPEN-METEO
  ================================== */
  const fetchWeather = async (lat, lon) => {
    try {
      const res = await fetch(
        `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,wind_speed_10m,relative_humidity_2m,precipitation`
      );
      const data = await res.json();
      setWeather(data.current);
    } catch (err) {
      console.error("Weather fetch error:", err);
    }
  };

  /* ================================
     HANDLE MAP CLICK
  ================================== */
  function LocationMarker() {
    useMapEvents({
      click(e) {
        const { lat, lng } = e.latlng;
        setPosition([lat, lng]);
        fetchWeather(lat, lng);
      }
    });

    return position === null ? null : (
      <Marker position={position}>
        <Popup>
          📍 Selected Location
        </Popup>
      </Marker>
    );
  }

  return (
    <div className="district-map-container">

      <MapContainer
        center={[20.5, 78.9]}   // India center
        zoom={5}
        style={{ height: "60vh" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <LocationMarker />

      </MapContainer>

      {/* WEATHER PANEL */}
      {weather && position && (
        <div className="district-weather">
          <h2>📍 Weather Report</h2>
          <p>Latitude: {position[0].toFixed(4)}</p>
          <p>Longitude: {position[1].toFixed(4)}</p>
          <p>🌡 Temperature: {weather.temperature_2m}°C</p>
          <p>💨 Wind Speed: {weather.wind_speed_10m} km/h</p>
          <p>💧 Humidity: {weather.relative_humidity_2m}%</p>
          <p>🌧 Precipitation: {weather.precipitation} mm</p>
        </div>
      )}

    </div>
  );
}