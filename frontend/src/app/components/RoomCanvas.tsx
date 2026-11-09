"use client";

import { useEffect, useMemo } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { buildFurniture, buildRoomShell, roomSizeM } from "../lib/scene";
import type { LayoutResult } from "../lib/types";

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
        <Html
          key={p.item_id}
          position={[(p.y + p.h / 2) * cell, ((p.height_cm ?? 80) / 100) + 0.12, (p.x + p.w / 2) * cell]}
          center
          zIndexRange={[10, 0]}
          style={{ pointerEvents: "none" }}
        >
          <span className="whitespace-nowrap rounded-full bg-black/70 px-2 py-0.5 text-[11px] font-medium text-white">
            {p.name}
          </span>
        </Html>
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