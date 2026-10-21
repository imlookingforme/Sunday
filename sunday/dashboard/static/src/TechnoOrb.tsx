import React, { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere } from '@react-three/drei';
import * as THREE from 'three';

export type PersonaType = 'senpai' | 'genz' | 'jarvis' | 'friday' | 'reflective' | 'sunday';

interface TechnoOrbProps {
  persona?: PersonaType;
  state?: 'idle' | 'listening' | 'thinking' | 'speaking' | 'coding';
  audioLevel?: number; // 0.0 to 1.0 (from WebAudio FFT)
  treeStage?: 'seed' | 'sprout' | 'sapling' | 'mature' | 'wilted';
}

// Persona Shader Palettes & Parameters
const PERSONA_CONFIGS = {
  senpai: {
    baseColor: new THREE.Color('#ffb7c5'), // Sakura Pink
    pulseColor: new THREE.Color('#ffffff'), // Bioluminescent White
    accentColor: new THREE.Color('#ff69b4'), // Deep Sakura Accent
    speed: 1.2,
    noiseScale: 2.2,
    wireframe: false,
    bloomIntensity: 1.4,
  },
  genz: {
    baseColor: new THREE.Color('#00ff88'), // Cyber Neon Green
    pulseColor: new THREE.Color('#ff0055'), // Electric Magenta
    accentColor: new THREE.Color('#00ffff'), // Matrix Cyan
    speed: 2.5,
    noiseScale: 3.5,
    wireframe: true,
    bloomIntensity: 2.0,
  },
  jarvis: {
    baseColor: new THREE.Color('#00d2ff'), // Holographic Cyan
    pulseColor: new THREE.Color('#0072ff'), // Stark Deep Blue
    accentColor: new THREE.Color('#ffffff'), // Arc White
    speed: 0.8,
    noiseScale: 1.5,
    wireframe: true,
    bloomIntensity: 1.6,
  },
  friday: {
    baseColor: new THREE.Color('#ff512f'), // Solar Amber
    pulseColor: new THREE.Color('#f09819'), // Flare Yellow
    accentColor: new THREE.Color('#ff0000'), // Ruby Spark
    speed: 2.0,
    noiseScale: 2.8,
    wireframe: false,
    bloomIntensity: 1.8,
  },
  reflective: {
    baseColor: new THREE.Color('#a18cd1'), // Lavender Twilight
    pulseColor: new THREE.Color('#fbc2eb'), // Ethereal Rose
    accentColor: new THREE.Color('#4a00e0'), // Indigo Dream
    speed: 0.6,
    noiseScale: 1.2,
    wireframe: false,
    bloomIntensity: 1.0,
  },
  sunday: {
    baseColor: new THREE.Color('#4a90e2'), // Stark Blue
    pulseColor: new THREE.Color('#50e3c2'), // Teal Surge
    accentColor: new THREE.Color('#f5a623'), // Gold Core
    speed: 1.4,
    noiseScale: 2.0,
    wireframe: false,
    bloomIntensity: 1.5,
  },
};

// GLSL Vertex Shader: Simplex noise vertex displacement influenced by audio FFT & time
const technoVertexShader = `
  uniform float uTime;
  uniform float uSpeed;
  uniform float uNoiseScale;
  uniform float uAudioLevel;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying float vDisplacement;

  // Simple 3D Perlin/Simplex Noise Generator
  vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;
    i = mod289(i);
    vec4 p = permute(permute(permute(
              i.z + vec4(0.0, i1.z, i2.z, 1.0))
            + i.y + vec4(0.0, i1.y, i2.y, 1.0))
            + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    vec4 j = p - 49.0 * floor(p * (1.0 / 49.0));
    vec4 x_ = floor(j * (1.0 / 7.0));
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ * (2.0 / 7.0) + 0.5 / 7.0 - 1.0;
    vec4 y = y_ * (2.0 / 7.0) + 0.5 / 7.0 - 1.0;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
  }

  void main() {
    vUv = uv;
    vNormal = normal;
    float time = uTime * uSpeed;
    float noise = snoise(normal * uNoiseScale + vec3(time * 0.2));

    // Audio FFT frequency displacement surge
    float surge = uAudioLevel * 0.45;
    float displacement = (noise * 0.25) + (noise * surge);
    vDisplacement = displacement;

    vec3 newPosition = position + normal * displacement;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
  }
`;

// GLSL Fragment Shader: Fresnel glow, chromatic aberration pulse, persona color blending
const technoFragmentShader = `
  uniform vec3 uBaseColor;
  uniform vec3 uPulseColor;
  uniform vec3 uAccentColor;
  uniform float uTime;
  uniform float uAudioLevel;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying float vDisplacement;

  void main() {
    // Fresnel Rim Glow
    vec3 viewDirection = normalize(vec3(0.0, 0.0, 1.0));
    float fresnel = dot(viewDirection, vNormal);
    fresnel = clamp(1.0 - fresnel, 0.0, 1.0);
    fresnel = pow(fresnel, 2.5);

    // Color interpolation across base, pulse, and accent
    vec3 coreColor = mix(uBaseColor, uPulseColor, abs(sin(uTime * 1.5 + vDisplacement * 4.0)));
    vec3 finalColor = mix(coreColor, uAccentColor, fresnel + (uAudioLevel * 0.5));

    // Dynamic Alpha with glowing rim
    float alpha = 0.85 + fresnel * 0.15;
    gl_FragColor = vec4(finalColor, alpha);
  }
`;

function ShaderOrb({
  persona = 'senpai',
  audioLevel = 0.0,
  wireframe = false,
}: {
  persona: PersonaType;
  audioLevel: number;
  wireframe: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const cfg = PERSONA_CONFIGS[persona] || PERSONA_CONFIGS.senpai;

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uSpeed: { value: cfg.speed },
      uNoiseScale: { value: cfg.noiseScale },
      uAudioLevel: { value: audioLevel },
      uBaseColor: { value: cfg.baseColor },
      uPulseColor: { value: cfg.pulseColor },
      uAccentColor: { value: cfg.accentColor },
    }),
    [cfg]
  );

  useEffect(() => {
    uniforms.uBaseColor.value = cfg.baseColor;
    uniforms.uPulseColor.value = cfg.pulseColor;
    uniforms.uAccentColor.value = cfg.accentColor;
    uniforms.uSpeed.value = cfg.speed;
    uniforms.uNoiseScale.value = cfg.noiseScale;
  }, [cfg, uniforms]);

  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime();
    uniforms.uTime.value = elapsed;
    uniforms.uAudioLevel.value = THREE.MathUtils.lerp(uniforms.uAudioLevel.value, audioLevel, 0.15);

    if (meshRef.current) {
      meshRef.current.rotation.y = elapsed * 0.2;
      meshRef.current.rotation.x = elapsed * 0.1;
    }
  });

  return (
    <Sphere ref={meshRef} args={[1.1, 128, 128]}>
      <shaderMaterial
        vertexShader={technoVertexShader}
        fragmentShader={technoFragmentShader}
        uniforms={uniforms}
        wireframe={wireframe || cfg.wireframe}
        transparent={true}
      />
    </Sphere>
  );
}

export default function TechnoOrb({
  persona = 'senpai',
  state = 'idle',
  audioLevel = 0.0,
}: TechnoOrbProps) {
  return (
    <div style={{ width: '100%', height: '100%', minHeight: '380px', position: 'relative' }}>
      <Canvas camera={{ position: [0, 0, 2.8] }}>
        <ambientLight intensity={0.6} />
        <pointLight position={[5, 5, 5]} intensity={1.5} />
        <ShaderOrb persona={persona} audioLevel={audioLevel} wireframe={false} />
      </Canvas>
    </div>
  );
}
