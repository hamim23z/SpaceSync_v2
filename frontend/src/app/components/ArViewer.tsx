"use client";

import { createElement, useEffect, useState } from "react";
import { buildArGroup } from "../lib/scene";
import type { LayoutResult } from "../lib/types";

/**
 * "View in AR".
 *
 * Exports the layout to a .glb file in the browser and hands it to Google's
 * <model-viewer>, which adds the AR button:
 *   - Android: opens Scene Viewer (ARCore)
 *   - iPhone / iPad: opens AR Quick Look (model-viewer builds the USDZ file itself)
 *   - supported browsers: WebXR
 * The button only appears on devices that can do AR. On a laptop you still get a
 * rotatable 3D preview. AR needs HTTPS, so test it on a deployed URL, not http://<your-ip>.
 */
export default function ArViewer({ layout }: { layout: LayoutResult }) {
  const [viewerReady, setViewerReady] = useState(false);
  const [glb, setGlb] = useState<{ url: string; layout: LayoutResult } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // load the <model-viewer> web component (browser only)
  useEffect(() => {
    import("@google/model-viewer")
      .then(() => setViewerReady(true))
      .catch(() => setError("Could not load the AR viewer."));
  }, []);

  useEffect(() => {
    let cancelled = false;
    let url: string | null = null;
    (async () => {
      try {
        const { GLTFExporter } = await import("three/addons/exporters/GLTFExporter.js");
        const buffer = await new GLTFExporter().parseAsync(buildArGroup(layout), { binary: true });
        if (cancelled) return;
        url = URL.createObjectURL(new Blob([buffer as ArrayBuffer], { type: "model/gltf-binary" }));
        setGlb({ url, layout });
      } catch {
        if (!cancelled) setError("Could not build the 3D file for AR.");
      }
    })();
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [layout]);

  const ready = viewerReady && glb && glb.layout === layout;

  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">See it in your room</h3>
          <p className="mt-1 text-sm text-muted">
            On a phone or tablet, tap <strong>View in AR</strong> and place the layout on your floor at real size. Line
            the green footprint up with your room.
          </p>
        </div>
        {glb && (
          <a
            href={glb.url}
            download="spacesync-layout.glb"
            className="shrink-0 rounded-full border border-border px-3 py-1.5 text-xs font-medium hover:bg-background"
          >
            Download .glb
          </a>
        )}
      </div>

      <div className="mt-4 overflow-hidden rounded-xl bg-background">
        {error ? (
          <p className="p-6 text-sm text-red-600">{error}</p>
        ) : ready ? (
          createElement(
            "model-viewer",
            {
              src: glb.url,
              alt: "Your proposed furniture layout in 3D",
              ar: true,
              "ar-modes": "webxr scene-viewer quick-look",
              "ar-scale": "fixed",
              "camera-controls": true,
              "touch-action": "pan-y",
              "shadow-intensity": "1",
              style: { width: "100%", height: "300px", display: "block" },
            },
            createElement(
              "button",
              {
                slot: "ar-button",
                className:
                  "absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-accent-fg shadow-lg",
              },
              "View in AR"
            )
          )
        ) : (
          <div className="flex h-[300px] items-center justify-center text-sm text-muted">Preparing 3D model…</div>
        )}
      </div>
      <p className="mt-3 text-xs text-muted">
        No AR button? Your device or browser may not support it. Open this page on a recent iPhone or Android phone.
      </p>
    </div>
  );
}