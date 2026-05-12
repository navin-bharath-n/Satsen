import { Canvas } from "@react-three/fiber";
import { OrbitControls, Sphere } from "@react-three/drei";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import * as THREE from "three";
import "./home.css";

function Globe() {
  return (
    <Sphere args={[2, 64, 64]}>
      <meshStandardMaterial
        map={new THREE.TextureLoader().load(
          "https://threejs.org/examples/textures/land_ocean_ice_cloud_2048.jpg"
        )}
      />
    </Sphere>
  );
}

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="home-container">

      {/* 🔥 Fire Background */}
      <div className="fire-bg"></div>

      {/* 🚁 Flying Plane */}
      <div className="plane">🚁</div>

      {/* 🌍 3D Globe */}
      <div className="globe">
        <Canvas>
          <ambientLight intensity={1} />
          <directionalLight position={[5, 5, 5]} />
          <Globe />
          <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={1} />
        </Canvas>
      </div>

      {/* 💎 Glass UI Card */}
      <motion.div
        className="glass-card"
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1 }}
      >


        <h1>🔥 AI Powered Satellite Monitoring System</h1>

        <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="fire-btn secondary"
            onClick={() => navigate("/login")}
            style={{ background: 'rgba(255, 77, 77, 0.2)', border: '2px solid #ff4d4d', color: '#fff', textShadow: '0 0 5px #ff4d4d' }}
          >
            Login / Send SMS
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="fire-btn"
            onClick={() => navigate("/dashboard")}
          >
            Normal Enter (Dashboard)
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}
