"use client";
import { Suspense } from "react";
import { useParams } from "next/navigation";
import { VoicePractice } from "@/components/voice-practice";
function Route() {
  const { sessionId } = useParams<{ sessionId: string }>();
  return <VoicePractice key={sessionId} screen="conversation" id={sessionId} />;
}
export default function Page() {
  return (
    <Suspense fallback={<p>Loading voice conversation…</p>}>
      <Route />
    </Suspense>
  );
}
