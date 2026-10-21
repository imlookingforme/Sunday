import React, { useRef, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial } from '@react-three/drei';

interface OrbProps {
  state: string;
}

// Orb state animation profiles
const STATE_PROFILES = {
  idle: { color: '#4a90e2', speed: 0.5, distortion: 0.2, scale: 1 },
  listening: { color: '#50e3c2', speed: 1.0, distortion: 0.5, scale: 1.2 },
  thinking: { color: '#f5a623', speed: 2.0, distortion: 0.8, scale: 1.1 },
  speaking: { color: '#9013fe', speed: 1.5, distortion: 0.6, scale: 1.15 },
  searching: { color: '#7ed321', speed: 1.2, distortion: 0.4, scale: 1.05 },
  coding: { color: '#ff5252', speed: 1.8, distortion: 0.7, scale: 1.1 }
};

function AnimatedOrb({ state }: OrbProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [profile, setProfile] = useState(STATE_PROFILES.idle);
  
  // Update profile when state changes
  useEffect(() => {
    setProfile(STATE_PROFILES[state as keyof typeof STATE_PROFILES] || STATE_PROFILES.idle);
  }, [state]);
  
  // Animate orb
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += profile.speed * 0.01;
      meshRef.current.rotation.x += profile.speed * 0.005;
    }
  });
  
  return (
    <Sphere ref={meshRef} args={[1, 64, 64]} scale={profile.scale}>
      <MeshDistortMaterial
        color={profile.color}
        distort={profile.distortion}
        speed={profile.speed}
        roughness={0.2}
        metalness={0.8}
      />
    </Sphere>
  );
}

export default function Orb({ state = 'idle' }: OrbProps) {
  return (
    <div style={{ width: '100%', height: '400px' }}>
      <Canvas camera={{ position: [0, 0, 3] }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} />
        <AnimatedOrb state={state} />
      </Canvas>
    </div>
  );
}
