import { Canvas } from "@react-three/fiber";
import { OrbitControls, Sphere } from "@react-three/drei";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import * as THREE from "three";
import "./Home.css";

function Globe() {
  return (
    <Sphere args={[2.1, 64, 64]}>
      <meshStandardMaterial
        map={new THREE.TextureLoader().load(
          "https://threejs.org/examples/textures/land_ocean_ice_cloud_2048.jpg"
        )}
        roughness={0.4}
        metalness={0.1}
      />
    </Sphere>
  );
}

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="home-container">
      {/* Space grid overlay */}
      <div className="fire-bg"></div>

      {/* 🌍 Interactive 3D Globe */}
      <div className="globe">
        <Canvas camera={{ position: [0, 0, 5], fov: 60 }}>
          <ambientLight intensity={1.2} />
          <directionalLight position={[5, 3, 5]} intensity={1.5} />
          <pointLight position={[-5, -3, -5]} intensity={0.5} />
          <Globe />
          <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={1.5} />
        </Canvas>
      </div>

      {/* 💎 Glass Control deck */}
      <motion.div
        className="glass-card"
        initial={{ opacity: 0, x: -30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <h1 className="system-title">SATSEN COMMAND</h1>
        <p className="system-subtitle">
          Real-time AI-powered monitoring, processing, and prediction of forest fires using orbital satellite feeds.
        </p>

        <div className="actions-pod">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="cyber-btn primary"
            onClick={() => navigate("/dashboard")}
          >
            <span>📡 Enter Dashboard</span>
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="cyber-btn secondary"
            onClick={() => navigate("/login")}
          >
            <span>🔐 Alert Access</span>
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}
