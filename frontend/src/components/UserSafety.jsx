import { useEffect, useState } from "react";
import axios from "axios";
import "./UserSafety.css";

const API = "http://127.0.0.1:8000";

export default function UserSafety() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;

        await axios.post(`${API}/user/location`, { lat, lon });

        const res = await axios.post(`${API}/user/check-danger`, {
          lat,
          lon
        });

        setStatus(res.data);
      },
      () => alert("Location permission required")
    );
  }, []);

  if (!status) return <p>Checking safety status...</p>;

  return (
    <div className={`safety-box ${status.danger ? "danger" : "safe"}`}>
      {status.danger ? (
        <>
          <h2>🔥 DANGER ALERT</h2>
          <p>Forest fire detected near your location</p>
          <p><b>Severity:</b> {status.severity}</p>
          <p><b>District:</b> {status.district}</p>
          <p><b>Evacuate Towards:</b> {status.evacuation_direction}</p>
        </>
      ) : (
        <>
          <h2>✅ YOU ARE SAFE</h2>
          <p>No forest fire detected near you</p>
        </>
      )}
    </div>
  );
}
