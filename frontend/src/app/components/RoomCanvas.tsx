"use client";
import { useEffect, useMemo } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { buildFurniture, buildRoomShell, roomSizeM } from "../lib/scene";
import type { LayoutResult } from "../lib/types";

/**
 * Name label drawn inside the 3D scene (a textured sprite). It replaces drei's <Html>, which
 * opens a separate React root per label and logs "Attempted to synchronously unmount a root
 * while React was already rendering" with React 19.
 */
function Label({ text, position }: { text: string; position: [number, number, number] }) {
  const { texture, aspect } = useMemo(() => {
    const font = "600 26px system-ui, -apple-system, Segoe UI, sans-serif";
    const measure = document.createElement("canvas").getContext("2d")!;
    measure.font = font;
    const w = Math.ceil(measure.measureText(text).width) + 36;
    const h = 44;
    const canvas = document.createElement("canvas");
    canvas.width = w * 2; // 2x for sharp text
    canvas.height = h * 2;
    const ctx = canvas.getContext("2d")!;
    ctx.scale(2, 2);
    ctx.fillStyle = "rgba(0,0,0,0.72)";
    ctx.beginPath();
    ctx.roundRect(0, 0, w, h, h / 2);
    ctx.fill();
    ctx.font = font;
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, w / 2, h / 2 + 1);
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    return { texture: tex, aspect: w / h };
  }, [text]);

  useEffect(() => () => texture.dispose(), [texture]);

  const height = 0.2; // metres
  return (
    <sprite position={position} scale={[height * aspect, height, 1]} renderOrder={10}>
      <spriteMaterial map={texture} transparent depthTest={false} toneMapped={false} />
    </sprite>
  );
}

/** Places the camera so the whole room fits, backing off on tall, narrow (phone) screens. */
function CameraRig({ width, depth }: { width: number; depth: number }) {
  const camera = useThree((s) => s.camera);
  const aspect = useThree((s) => s.size.width / Math.max(1, s.size.height));

  useEffect(() => {
    const reach = Math.max(width, depth);
    const back = Math.max(1, 1.2 / aspect);
    camera.position.set(
      width / 2 + reach * 0.55 * back,
      reach * 0.95 * back,
      depth / 2 + (depth / 2 + reach * 0.95) * back
    );
    camera.lookAt(width / 2, 0, depth / 2);
  }, [camera, aspect, width, depth]);

  return null;
}

export default function RoomCanvas({ layout }: { layout: LayoutResult }) {
  const shell = useMemo(() => buildRoomShell(layout), [layout]);
  const furniture = useMemo(() => buildFurniture(layout), [layout]);
  const { width, depth } = roomSizeM(layout);
  const reach = Math.max(width, depth);
  const cell = layout.room.cell_cm / 100;

  return (
    <Canvas shadows camera={{ fov: 40 }} aria-label="3D view of your room with the proposed furniture layout">
      <CameraRig width={width} depth={depth} />
      <color attach="background" args={["#eef0ee"]} />
      <ambientLight intensity={0.9} />
      <directionalLight
        position={[width, reach * 1.5, -depth * 0.2]}
        intensity={1.4}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <primitive object={shell} />
      <primitive object={furniture} />
      {layout.items.map((p) => (
        <Label
          key={p.item_id}
          text={p.name}
          position={[(p.y + p.h / 2) * cell, ((p.height_cm ?? 80) / 100) + 0.12, (p.x + p.w / 2) * cell]}
        />
      ))}
      <OrbitControls
        target={[width / 2, 0, depth / 2]}
        enablePan={false}
        minDistance={reach * 0.6}
        maxDistance={reach * 4}
        maxPolarAngle={Math.PI / 2.05}
      />
    </Canvas>
  );
}