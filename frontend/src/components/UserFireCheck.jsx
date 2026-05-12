import { useState } from "react";
import axios from "axios";
import "./UserFireCheck.css";

const API_URL = "http://127.0.0.1:8000";

export default function UserFireCheck() {
  const [image, setImage] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeImage = async () => {
    if (!image) {
      alert("Please upload an image");
      return;
    }

    const formData = new FormData();
    formData.append("image", image);

    try {
      setLoading(true);
      const res = await axios.post(
        `${API_URL}/user/fire-check`,
        formData
      );
      setResult(res.data);
    } catch (err) {
      alert("Analysis failed");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fire-check-container">
      <h2>🌍 Forest Fire Image Check</h2>

      <input
        type="file"
        accept="image/*"
        onChange={(e) => setImage(e.target.files[0])}
      />

      <button onClick={analyzeImage} disabled={loading}>
        {loading ? "Analyzing..." : "🔍 Check Image"}
      </button>

      {/* 🔥 RESULT UI */}
      {result && (
        <div
          className={
            result.fire_detected
              ? "alert-box fire"
              : "alert-box safe"
          }
        >
          {result.fire_detected ? (
            <>
              <h3>🔥 FOREST FIRE DETECTED</h3>
              <p>Severity: {result.severity}</p>
              <p>Confidence: {(result.confidence * 100).toFixed(1)}%</p>
            </>
          ) : (
            <>
              <h3>✅ NO FIRE DETECTED</h3>
              <p>Area appears safe</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
