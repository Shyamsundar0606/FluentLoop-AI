"use client";
import { Suspense } from "react";
import { useParams } from "next/navigation";
import { VoicePractice } from "@/components/voice-practice";
function Route() {
  const { targetId } = useParams<{ targetId: string }>();
  const decodedId = targetId.replace(/%3a/gi, ":");
  return <VoicePractice key={decodedId} screen="target" id={decodedId} />;
}
export default function Page() {
  return (
    <Suspense fallback={<p>Loading pronunciation target…</p>}>
      <Route />
    </Suspense>
  );
}
