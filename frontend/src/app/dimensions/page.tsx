/* Prompted by Hamim Choudhury - used Claude */

import { Suspense } from "react";
import DimensionsForm from "../components/DimensionsForm";

export const metadata = { title: "Enter room dimensions · SpaceSync" };

export default function DimensionsPage() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Tell us about your room</h1>
      <p className="mt-2 max-w-xl text-muted">We’ll build a 3D version of it and let the agents plan the furniture.</p>
      <div className="mt-8">
        {/* the form reads the URL, so it sits inside Suspense (required by Cache Components) */}
        <Suspense fallback={<div className="h-80 animate-pulse rounded-2xl bg-surface" />}>
          <DimensionsForm />
        </Suspense>
      </div>
    </div>
  );
}