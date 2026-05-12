import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate, Link } from "react-router-dom";
import "./Auth.css";

const API = "http://127.0.0.1:8000";

export default function Register() {
    const [mobileNo, setMobileNo] = useState("");
    const [password, setPassword] = useState("");
    const [otp, setOtp] = useState("");
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const navigate = useNavigate();

    const handleSendOtp = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        setSuccess("");
        try {
            const res = await fetch(`${API}/auth/send-otp`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mobile_no: mobileNo })
            });
            const data = await res.json();
            if (res.ok) {
                setStep(2);
                setSuccess("OTP Sent Successfully! Please check your mobile.");
            } else {
                setError(data.detail || "Failed to send OTP");
            }
        } catch (err) {
            setError("Network error. Could not connect to the server.");
        }
        setLoading(false);
    };

    const handleVerifyOtp = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        setSuccess("");
        try {
            const res = await fetch(`${API}/auth/verify-otp`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mobile_no: mobileNo, password, otp })
            });
            const data = await res.json();
            if (res.ok) {
                setSuccess("Registered Successfully! Redirecting to Login...");
                setTimeout(() => navigate("/login"), 2000);
            } else {
                setError(data.detail || "Invalid OTP");
            }
        } catch (err) {
            setError("Network error. Could not connect to the server.");
        }
        setLoading(false);
    };

    return (
        <div className="auth-container">
            <motion.div
                className="auth-card"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <h2>🔥 <span>Global System</span></h2>

                {error && <div className="auth-error">{error}</div>}
                {success && <div className="auth-error" style={{ background: 'rgba(0, 255, 136, 0.1)', color: '#00ff88', borderColor: 'rgba(0, 255, 136, 0.2)' }}>{success}</div>}

                <AnimatePresence mode="wait">
                    {step === 1 ? (
                        <motion.form
                            key="step1"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            onSubmit={handleSendOtp}
                        >
                            <div className="auth-input-group">
                                <label>Mobile Number</label>
                                <input
                                    type="tel"
                                    required
                                    value={mobileNo}
                                    onChange={(e) => setMobileNo(e.target.value)}
                                    placeholder="+91..."
                                />
                            </div>
                            <button type="submit" disabled={loading} className="auth-btn">
                                {loading ? "SENDING..." : "GET OTP"}
                            </button>

                            <div className="auth-link">
                                Already have an account? <Link to="/login">Login here</Link>
                            </div>
                        </motion.form>
                    ) : (
                        <motion.form
                            key="step2"
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            onSubmit={handleVerifyOtp}
                        >
                            <div className="auth-input-group">
                                <label>Set Password</label>
                                <input
                                    type="password"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="Create your password"
                                />
                            </div>

                            <div className="auth-input-group">
                                <label>OTP Code</label>
                                <input
                                    type="text"
                                    required
                                    maxLength="6"
                                    value={otp}
                                    onChange={(e) => setOtp(e.target.value)}
                                    placeholder="Enter 6-digit OTP"
                                />
                            </div>

                            <button type="submit" disabled={loading} className="auth-btn">
                                {loading ? "VERIFYING..." : "COMPLETE REGISTRATION"}
                            </button>

                            <div className="auth-link">
                                <Link to="/login">Cancel</Link>
                            </div>
                        </motion.form>
                    )}
                </AnimatePresence>
            </motion.div>
        </div>
    );
}
