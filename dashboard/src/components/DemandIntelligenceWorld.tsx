import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Sparkles, EyeOff } from "lucide-react";

interface DemandIntelligenceWorldProps {
  interactive?: boolean;
  reducedMotion?: boolean;
  className?: string;
}

export const DemandIntelligenceWorld: React.FC<DemandIntelligenceWorldProps> = ({
  interactive = true,
  reducedMotion = false,
  className = "",
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [isLowPower, setIsLowPower] = useState(reducedMotion);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  useEffect(() => {
    if (!mountRef.current || isLowPower) return;

    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xf6f8fc, 0.035);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 10, 18);
    camera.lookAt(0, 1, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    mountRef.current.appendChild(renderer.domElement);

    // Ambient & Directional Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x2563eb, 1.4);
    dirLight.position.set(12, 18, 10);
    dirLight.castShadow = true;
    scene.add(dirLight);

    const secondaryLight = new THREE.DirectionalLight(0x635bff, 0.8);
    secondaryLight.position.set(-10, 12, -8);
    scene.add(secondaryLight);

    const cyanPoint = new THREE.PointLight(0x22c7e8, 1.5, 20);
    cyanPoint.position.set(0, 3, 0);
    scene.add(cyanPoint);

    // Root Group
    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // 1. Isometric Grid Base
    const gridHelper = new THREE.GridHelper(24, 24, 0x93c5fd, 0xe2e8f0);
    gridHelper.position.y = -0.05;
    worldGroup.add(gridHelper);

    // 2. Central DemandIQ Intelligence Core
    const coreGroup = new THREE.Group();
    coreGroup.position.set(0, 2.5, 0);

    const coreGeo = new THREE.IcosahedronGeometry(1.2, 0);
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0x2563eb,
      metalness: 0.3,
      roughness: 0.2,
      wireframe: false,
      flatShading: true,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    coreMesh.castShadow = true;
    coreGroup.add(coreMesh);

    // Wireframe Outer Lattice
    const coreWireGeo = new THREE.IcosahedronGeometry(1.65, 1);
    const coreWireMat = new THREE.MeshBasicMaterial({
      color: 0x635bff,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const coreWireMesh = new THREE.Mesh(coreWireGeo, coreWireMat);
    coreGroup.add(coreWireMesh);

    // Floating Forecast Horizon Rings
    const ringGeo1 = new THREE.TorusGeometry(3.2, 0.03, 16, 64);
    const ringMat1 = new THREE.MeshBasicMaterial({ color: 0x22c7e8, transparent: true, opacity: 0.5 });
    const horizonRing1 = new THREE.Mesh(ringGeo1, ringMat1);
    horizonRing1.rotation.x = Math.PI / 2.3;
    coreGroup.add(horizonRing1);

    const ringGeo2 = new THREE.TorusGeometry(4.4, 0.025, 16, 64);
    const ringMat2 = new THREE.MeshBasicMaterial({ color: 0x2563eb, transparent: true, opacity: 0.35 });
    const horizonRing2 = new THREE.Mesh(ringGeo2, ringMat2);
    horizonRing2.rotation.x = Math.PI / 1.8;
    horizonRing2.rotation.y = Math.PI / 4;
    coreGroup.add(horizonRing2);

    worldGroup.add(coreGroup);

    // 3. Orbiting Product Nodes
    const productNodes: { mesh: THREE.Mesh; angle: number; radius: number; speed: number; name: string }[] = [];
    const productsData = [
      { name: "P001 Wireless Earbuds", color: 0xef4444, radius: 4.8, speed: 0.008, y: 1.8 },
      { name: "P002 Laptop Stand", color: 0xf59e0b, radius: 5.6, speed: -0.006, y: 2.3 },
      { name: "P003 Stepper Motor", color: 0x10b981, radius: 6.4, speed: 0.005, y: 1.4 },
      { name: "P004 Servo Actuator", color: 0x2563eb, radius: 7.2, speed: -0.004, y: 2.8 },
      { name: "P005 Workwear Gloves", color: 0x635bff, radius: 8.0, speed: 0.007, y: 2.0 },
    ];

    productsData.forEach((pd, idx) => {
      const nodeGeo = new THREE.SphereGeometry(0.38, 24, 24);
      const nodeMat = new THREE.MeshStandardMaterial({
        color: pd.color,
        roughness: 0.2,
        metalness: 0.4,
      });
      const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);
      nodeMesh.castShadow = true;

      // Glow halo ring
      const haloGeo = new THREE.RingGeometry(0.5, 0.6, 24);
      const haloMat = new THREE.MeshBasicMaterial({
        color: pd.color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.4,
      });
      const haloMesh = new THREE.Mesh(haloGeo, haloMat);
      haloMesh.rotation.x = Math.PI / 2;
      nodeMesh.add(haloMesh);

      worldGroup.add(nodeMesh);
      productNodes.push({
        mesh: nodeMesh,
        angle: (idx * (Math.PI * 2)) / productsData.length,
        radius: pd.radius,
        speed: pd.speed,
        name: pd.name,
      });
    });

    // 4. Stepped Inventory & Reorder Towers
    const towerCoords = [
      { x: -5, z: -4, h: 2.2, color: 0x10b981 }, // Healthy
      { x: -3.5, z: 4.5, h: 1.2, color: 0xef4444 }, // Critical
      { x: 5.2, z: -3.8, h: 3.8, color: 0x635bff }, // Overstock
      { x: 4.5, z: 4.2, h: 1.8, color: 0xf59e0b }, // Reorder Soon
      { x: -6.5, z: 1.5, h: 2.6, color: 0x2563eb }, // In transit
    ];

    towerCoords.forEach((tc) => {
      const towerGeo = new THREE.BoxGeometry(0.9, tc.h, 0.9);
      const towerMat = new THREE.MeshStandardMaterial({
        color: tc.color,
        roughness: 0.3,
        metalness: 0.2,
        transparent: true,
        opacity: 0.9,
      });
      const tower = new THREE.Mesh(towerGeo, towerMat);
      tower.position.set(tc.x, tc.h / 2, tc.z);
      tower.castShadow = true;
      tower.receiveShadow = true;
      worldGroup.add(tower);

      // Pulse beacon beacon atop critical & high risk towers
      if (tc.color === 0xef4444 || tc.color === 0xf59e0b) {
        const beaconGeo = new THREE.ConeGeometry(0.2, 0.6, 16);
        const beaconMat = new THREE.MeshBasicMaterial({ color: tc.color });
        const beacon = new THREE.Mesh(beaconGeo, beaconMat);
        beacon.position.set(tc.x, tc.h + 0.35, tc.z);
        beacon.rotation.x = Math.PI;
        worldGroup.add(beacon);
      }
    });

    // Mouse Interaction
    let mouseX = 0;
    let mouseY = 0;
    const handleMouseMove = (e: MouseEvent) => {
      if (!interactive) return;
      const rect = mountRef.current?.getBoundingClientRect();
      if (!rect) return;
      mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseY = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
    };

    window.addEventListener("mousemove", handleMouseMove);

    // Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Core rotation & gentle breathing float
      coreMesh.rotation.y += 0.005;
      coreMesh.rotation.x = Math.sin(elapsedTime * 0.8) * 0.1;
      coreWireMesh.rotation.y -= 0.003;
      coreWireMesh.rotation.z += 0.002;
      coreGroup.position.y = 2.5 + Math.sin(elapsedTime * 1.2) * 0.15;

      horizonRing1.rotation.z += 0.004;
      horizonRing2.rotation.z -= 0.003;

      // Orbiting product nodes
      productNodes.forEach((pn) => {
        pn.angle += pn.speed;
        pn.mesh.position.x = Math.cos(pn.angle) * pn.radius;
        pn.mesh.position.z = Math.sin(pn.angle) * pn.radius;
        pn.mesh.position.y = 2.0 + Math.sin(elapsedTime * 2 + pn.radius) * 0.2;
      });

      // Smooth camera pan based on mouse
      if (interactive) {
        camera.position.x += (mouseX * 4 - camera.position.x) * 0.03;
        camera.position.y += (10 + mouseY * 2 - camera.position.y) * 0.03;
        camera.lookAt(0, 1.8, 0);
      }

      worldGroup.rotation.y = elapsedTime * 0.03;

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!mountRef.current) return;
      const newWidth = mountRef.current.clientWidth;
      const newHeight = mountRef.current.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [interactive, isLowPower]);

  return (
    <div className={`relative w-full h-full overflow-hidden select-none ${className}`}>
      {/* 3D Canvas Container */}
      {!isLowPower ? (
        <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />
      ) : (
        /* Reduced Motion Fallback */
        <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-blue-50/50 to-indigo-50/30 p-8 border border-slate-200 rounded-3xl">
          <div className="w-20 h-20 rounded-2xl bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-600 mb-4 shadow-sm">
            <Sparkles className="w-10 h-10 animate-pulse text-blue-600" />
          </div>
          <p className="text-sm font-bold text-slate-800">Demand Intelligence World (Performance Mode)</p>
          <p className="text-xs text-slate-500 mt-1 max-w-sm text-center">
            3D rendering is paused to conserve GPU and battery resources. All analytics remain fully active.
          </p>
        </div>
      )}

      {/* Control Overlay */}
      <div className="absolute bottom-3 right-4 flex items-center gap-2">
        <button
          onClick={() => setIsLowPower(!isLowPower)}
          className="px-2.5 py-1 text-[11px] font-semibold text-slate-600 bg-white/80 hover:bg-white backdrop-blur-md border border-slate-200/90 rounded-lg shadow-sm transition-all flex items-center gap-1.5"
          title={isLowPower ? "Enable 3D animation" : "Enable low-power mode"}
        >
          {isLowPower ? (
            <>
              <Sparkles className="w-3 h-3 text-blue-600" />
              <span>3D World</span>
            </>
          ) : (
            <>
              <EyeOff className="w-3 h-3 text-slate-400" />
              <span>Reduced Motion</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
