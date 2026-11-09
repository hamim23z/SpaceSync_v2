/* Prompted by Hamim Choudhury - used Claude */

import { Suspense } from "react";
import RoomView from "../components/RoomView";

export const metadata = { title: "Your room · SpaceSync" };

export default function RoomPage() {
  return (
    // RoomView reads the room settings from the URL, so it sits inside Suspense
    <Suspense fallback={<div className="mx-auto h-96 w-full max-w-6xl animate-pulse px-4 py-6" />}>
      <RoomView />
    </Suspense>
  );
}