import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import "./ManualFireUpload.css";

const CNN_API = "http://localhost:8001";
const MAIN_API = "http://localhost:8000";

export default function ManualFireUpload() {
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const navigate = useNavigate();

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
      setResult(null); // Clear previous results
    }
  };

  const handleUpload = () => {
    if (!image) {
      alert("Select image first");
      return;
    }

    navigator.geolocation.getCurrentPosition(async (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;

      const formData = new FormData();
      formData.append("image", image);
      formData.append("lat", lat);
      formData.append("lon", lon);

      try {
        setLoading(true);

        // 1️⃣ CNN Backend
        const cnnRes = await axios.post(
          `${CNN_API}/admin/upload`,
          formData,
          { headers: { "Content-Type": "multipart/form-data" } }
        );

        setResult(cnnRes.data);

        // 3️⃣ Call new LSTM prediction endpoint for escape route and spread map
        if (cnnRes.data.fire_detected) {
          const mainRes = await axios.post(
            `${MAIN_API}/fire/manual-trigger`,
            {
              lat,
              lon,
              severity: cnnRes.data.confidence > 0.85 ? "HIGH" : "MEDIUM",
              spread_direction: cnnRes.data.spread_direction,
              confidence: cnnRes.data.confidence
            }
          );

          // Now fetch real time LSTM predictions for escape routes
          const lstmRes = await axios.post(`${MAIN_API}/fire/predict-spread`, {
            lat,
            lon,
            severity: cnnRes.data.confidence > 0.85 ? "HIGH" : "MEDIUM"
          });

          // Combine basic trigger payload with the advanced map data
          const combinedData = {
            ...mainRes.data,
            lstmPolygon: lstmRes.data.fire_polygon,
            escapeRoute: lstmRes.data.escape_route,
            safeZone: lstmRes.data.safe_zone,
            advancedWeather: {
              windSpeed: lstmRes.data.wind_speed,
              windDir: lstmRes.data.wind_direction,
              humidity: lstmRes.data.humidity,
              lstmSpreadRisk: lstmRes.data.lstm_spread_risk
            }
          };

          localStorage.setItem(
            "alertData",
            JSON.stringify(combinedData)
          );

          navigate("/Emergency");
        }

      } catch (err) {
        console.error(err);
        alert("Upload failed");
      } finally {
        setLoading(false);
      }
    });
  };

  return (
    <div className="upload-container">
      <button className="back-btn" onClick={() => navigate("/dashboard")}>
        ← BACK TO DASHBOARD
      </button>
      <motion.div
        className="upload-panel"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <div className="upload-header">
          <motion.h2
            className="upload-title"
            animate={{ textShadow: ["0 0 10px #00ffff", "0 0 20px #00ffff", "0 0 10px #00ffff"] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            🌍 TACTICAL SCANNER
          </motion.h2>
          <p className="upload-subtitle">SATELLITE IMAGE UPLOAD & ANALYSIS</p>
        </div>

        <div className="file-upload-wrapper">
          <input
            type="file"
            accept="image/*"
            onChange={handleImageChange}
            className="file-upload-input"
          />
          {!preview ? (
            <div className="file-upload-text">
              <svg viewBox="0 0 24 24">
                <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
              </svg>
              <span>DRAG AND DROP OR CLICK TO UPLOAD IMAGE</span>
            </div>
          ) : (
            <div className="image-preview-container">
              {loading && <div className="scanner-line"></div>}
              <img src={preview} alt="Space/Satellite Preview" className="image-preview" />
            </div>
          )}
        </div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleUpload}
          className="analyze-btn"
          disabled={loading || !image}
        >
          {loading ? "IN PROGRESS..." : "🔥 INITIATE SCAN"}
        </motion.button>

        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="status-indicator status-scanning"
            >
              Analyzing thermal anomalies...
            </motion.div>
          )}

          {result && !result.fire_detected && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="status-indicator status-safe"
            >
              <h3 className="status-safe-title">🟢 SECTOR CLEAR</h3>
              <p className="status-safe-subtitle">NO THERMAL ANOMALIES DETECTED IN QUADRANT</p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
