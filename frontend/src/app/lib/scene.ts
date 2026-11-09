import * as THREE from "three";
import { LayoutResult, StyleTag } from "./types";

/**
 * Builds three.js objects from a layout. Used twice:
 *   - on screen (RoomCanvas draws these in the 3D view)
 *   - for AR (ArViewer exports the same furniture to a .glb file)
 * so what you see in the browser is exactly what you get in AR.
 *
 * Units are meters. The room's top-left corner is the origin:
 *   +X runs along the room's width (grid columns), +Z along its depth (grid rows), +Y is up.
 */

export const STYLE_COLORS: Record<StyleTag, string> = {
  modern: "#3b82f6",
  cozy: "#d97706",
  minimal: "#64748b",
  classic: "#9f1239",
};

const DEFAULT_HEIGHT_CM = 80;

export const roomSizeM = (layout: LayoutResult) => ({
  width: (layout.room.cols * layout.room.cell_cm) / 100,
  depth: (layout.room.rows * layout.room.cell_cm) / 100,
});

export function buildFurniture(layout: LayoutResult, withEdges = true): THREE.Group {
  const group = new THREE.Group();
  group.name = "furniture";
  const cell = layout.room.cell_cm / 100;

  for (const p of layout.items) {
    const sizeX = p.h * cell;
    const sizeZ = p.w * cell;
    const sizeY = (p.height_cm ?? DEFAULT_HEIGHT_CM) / 100;
    const geo = new THREE.BoxGeometry(sizeX, sizeY, sizeZ);
    const mat = new THREE.MeshStandardMaterial({ color: STYLE_COLORS[p.style], roughness: 0.7, metalness: 0.05 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.name = p.name;
    mesh.position.set((p.y + p.h / 2) * cell, sizeY / 2, (p.x + p.w / 2) * cell);
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    if (withEdges) {
      mesh.add(
        new THREE.LineSegments(
          new THREE.EdgesGeometry(geo),
          new THREE.LineBasicMaterial({ color: "#0f172a", transparent: true, opacity: 0.35 })
        )
      );
    }
    group.add(mesh);
  }
  return group;
}

export function buildRoomShell(layout: LayoutResult): THREE.Group {
  const group = new THREE.Group();
  group.name = "room";
  const { width, depth } = roomSizeM(layout);
  const cell = layout.room.cell_cm / 100;

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(width, depth),
    new THREE.MeshStandardMaterial({ color: "#e7e2d8", roughness: 1 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(width / 2, 0, depth / 2);
  floor.receiveShadow = true;
  group.add(floor);

  const grid = new THREE.GridHelper(Math.max(width, depth), Math.round(Math.max(width, depth) / cell), "#b9b3a6", "#d3cec2");
  grid.position.set(width / 2, 0.002, depth / 2);
  group.add(grid);

  const wallMat = new THREE.MeshStandardMaterial({ color: "#f4f1ea", roughness: 1, transparent: true, opacity: 0.9 });
  const wallH = 0.6;
  const back = new THREE.Mesh(new THREE.BoxGeometry(width, wallH, 0.05), wallMat); // far wall, z = 0
  back.position.set(width / 2, wallH / 2, -0.025);
  const left = new THREE.Mesh(new THREE.BoxGeometry(0.05, wallH, depth), wallMat); // left wall, x = 0
  left.position.set(-0.025, wallH / 2, depth / 2);
  group.add(back, left);

  const doorCol = Math.floor(layout.room.cols / 2);
  const door = new THREE.Mesh(
    new THREE.BoxGeometry(cell * 1.6, 0.02, 0.06),
    new THREE.MeshStandardMaterial({ color: "#16a34a" })
  );
  door.name = "door";
  door.position.set((doorCol + 0.5) * cell, 0.011, depth + 0.03);
  group.add(door);

  return group;
}

export function buildArGroup(layout: LayoutResult): THREE.Group {
  const root = new THREE.Group();
  root.name = "spacesync-layout";
  const { width, depth } = roomSizeM(layout);

  const slab = new THREE.Mesh(
    new THREE.BoxGeometry(width, 0.01, depth),
    new THREE.MeshStandardMaterial({ color: "#0b6b63", transparent: true, opacity: 0.25 })
  );
  slab.position.set(width / 2, 0.005, depth / 2);
  root.add(slab, buildFurniture(layout, false));
  root.position.set(-width / 2, 0, -depth / 2);

  const wrapper = new THREE.Group();
  wrapper.add(root);
  return wrapper;
}