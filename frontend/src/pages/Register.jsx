import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import "./Auth.css";

const API = "http://127.0.0.1:8000";

export default function Register() {
    const navigate = useNavigate();

    const [mobileNo, setMobileNo] = useState("");
    const [password, setPassword] = useState("");
    const [otp, setOtp] = useState("");

    const [step, setStep] = useState(1);

    const [loading, setLoading] = useState(false);

    const [showPassword, setShowPassword] = useState(false);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    /* ================= SEND OTP ================= */

    const handleSendOtp = async (e) => {
        e.preventDefault();

        setLoading(true);
        setError("");
        setSuccess("");

        try {
            const res = await fetch(`${API}/auth/send-otp`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    mobile_no: mobileNo,
                }),
            });

            const data = await res.json();

            if (res.ok) {
                setSuccess("OTP sent successfully. Please check your mobile.");
                setStep(2);
            } else {
                setError(data.detail || "Failed to send OTP.");
            }
        } catch (err) {
            setError("Unable to connect to the server.");
        } finally {
            setLoading(false);
        }
    };

    /* ================= VERIFY OTP ================= */

    const handleVerifyOtp = async (e) => {
        e.preventDefault();

        setLoading(true);
        setError("");
        setSuccess("");

        try {
            const res = await fetch(`${API}/auth/verify-otp`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    mobile_no: mobileNo,
                    password,
                    otp,
                }),
            });

            const data = await res.json();

            if (res.ok) {
                setSuccess("Registration successful! Redirecting...");

                setTimeout(() => {
                    navigate("/login");
                }, 1800);
            } else {
                setError(data.detail || "Invalid OTP.");
            }
        } catch (err) {
            setError("Unable to connect to the server.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <motion.div
                className="auth-card"
                initial={{ opacity: 0, y: 35 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
            >
                {/* ================= HEADER ================= */}

                <div className="auth-header">
                    <div className="auth-logo">🛰️</div>

                    <h2>
                        <span>SatSen</span> Registration
                    </h2>

                    <p className="auth-subtitle">
                        Join the AI Forest Fire Monitoring Network
                    </p>
                </div>

                {/* ================= ALERTS ================= */}

                {error && <div className="auth-error">{error}</div>}

                {success && (
                    <div className="auth-success">
                        {success}
                    </div>
                )}

                <AnimatePresence mode="wait">

                    {/* =======================================================
                           STEP 1
          ======================================================== */}

                    {step === 1 ? (
                        <motion.form
                            key="step1"
                            initial={{ opacity: 0, x: -30 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 30 }}
                            transition={{ duration: 0.4 }}
                            onSubmit={handleSendOtp}
                        >
                            <div className="auth-input-group">
                                <label>📱 Mobile Number</label>

                                <input
                                    type="tel"
                                    placeholder="+91XXXXXXXXXX"
                                    value={mobileNo}
                                    onChange={(e) =>
                                        setMobileNo(e.target.value)
                                    }
                                    required
                                />
                            </div>

                            <button
                                className="auth-btn"
                                type="submit"
                                disabled={loading}
                            >
                                {loading
                                    ? "SENDING OTP..."
                                    : "📩 SEND OTP"}
                            </button>

                            <div className="auth-divider">
                                Secure Verification
                            </div>

                            <div className="auth-footer">
                                Already have an account?

                                <div className="auth-link">
                                    <Link to="/login">
                                        Login Here
                                    </Link>
                                </div>
                            </div>
                        </motion.form>
                    ) : (
                        /* =======================================================
                                         STEP 2
                        ======================================================== */

                        <motion.form
                            key="step2"
                            initial={{ opacity: 0, x: -30 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 30 }}
                            transition={{ duration: 0.4 }}
                            onSubmit={handleVerifyOtp}
                        >
                            <div className="auth-input-group">
                                <label>🔒 Create Password</label>

                                <div className="password-wrapper">
                                    <input
                                        type={
                                            showPassword
                                                ? "text"
                                                : "password"
                                        }
                                        placeholder="Create a strong password"
                                        value={password}
                                        onChange={(e) =>
                                            setPassword(e.target.value)
                                        }
                                        required
                                    />

                                    <span
                                        className="password-toggle"
                                        onClick={() =>
                                            setShowPassword(
                                                !showPassword
                                            )
                                        }
                                    >
                                        {showPassword ? "🙈" : "👁"}
                                    </span>
                                </div>
                            </div>

                            <div className="auth-input-group">
                                <label>🔢 OTP Verification</label>

                                <input
                                    type="text"
                                    maxLength={6}
                                    placeholder="Enter 6-digit OTP"
                                    value={otp}
                                    onChange={(e) =>
                                        setOtp(e.target.value)
                                    }
                                    required
                                />
                            </div>

                            <button
                                className="auth-btn"
                                type="submit"
                                disabled={loading}
                            >
                                {loading
                                    ? "VERIFYING..."
                                    : "🚀 COMPLETE REGISTRATION"}
                            </button>

                            <div className="auth-divider">
                                Account Setup
                            </div>

                            <div className="auth-footer">
                                <div className="auth-link">
                                    <Link to="/login">
                                        ← Back to Login
                                    </Link>
                                </div>
                            </div>
                        </motion.form>
                    )}

                </AnimatePresence>
            </motion.div>
        </div>
    );
}