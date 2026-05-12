import { Canvas } from "@react-three/fiber";
import { Sphere, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

export default function GlobePage() {
  return (
    <Canvas style={{ height: "100vh" }}>
      <ambientLight intensity={1}/>
      <directionalLight position={[5,5,5]}/>
      <Sphere args={[2,64,64]}>
        <meshStandardMaterial
          map={new THREE.TextureLoader().load(
            "https://threejs.org/examples/textures/land_ocean_ice_cloud_2048.jpg"
          )}
        />
      </Sphere>
      <OrbitControls autoRotate/>
    </Canvas>
  );
}
