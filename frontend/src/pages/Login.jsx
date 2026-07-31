import { useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import "./Auth.css";

const API = "http://127.0.0.1:8000";

export default function Login() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    mobile: "",
    password: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const login = async (e) => {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
      const res = await axios.post(`${API}/auth/login`, {
        mobile_no: form.mobile,
        password: form.password,
      });

      localStorage.setItem("token", res.data.access_token);

      navigate("/dashboard");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Invalid mobile number or password."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <motion.div
        className="auth-card"
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        {/* ================= HEADER ================= */}

        <div className="auth-header">
          <div className="auth-logo">🛰️</div>

          <h2>
            <span>SatSen</span> Login
          </h2>

          <p className="auth-subtitle">
            AI Powered Forest Fire Monitoring & Emergency Command System
          </p>
        </div>

        {/* ================= ERROR ================= */}

        {error && <div className="auth-error">{error}</div>}

        {/* ================= FORM ================= */}

        <form onSubmit={login}>
          {/* MOBILE */}

          <div className="auth-input-group">
            <label>📱 Mobile Number</label>

            <input
              name="mobile"
              type="tel"
              placeholder="+91XXXXXXXXXX"
              value={form.mobile}
              onChange={handleChange}
              autoComplete="tel"
              required
            />
          </div>

          {/* PASSWORD */}

          <div className="auth-input-group">
            <label>🔒 Password</label>

            <div className="password-wrapper">
              <input
                name="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={form.password}
                onChange={handleChange}
                autoComplete="current-password"
                required
              />

              <span
                className="password-toggle"
                onClick={() =>
                  setShowPassword(!showPassword)
                }
                title={
                  showPassword
                    ? "Hide Password"
                    : "Show Password"
                }
              >
                {showPassword ? "🙈" : "👁"}
              </span>
            </div>
          </div>

          {/* BUTTON */}

          <button
            type="submit"
            className="auth-btn"
            disabled={loading}
          >
            {loading ? (
              "AUTHENTICATING..."
            ) : (
              <>🚀 LOGIN TO COMMAND CENTER</>
            )}
          </button>
        </form>

        {/* DIVIDER */}

        <div className="auth-divider">
          Secure Authentication
        </div>

        {/* FOOTER */}

        <div className="auth-footer">
          Don't have an account?
          <div className="auth-link">
            <Link to="/register">
              Create New Account
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
}