"use client";
import { Suspense } from 'react';
import { useParams } from 'next/navigation';
import { ProtectedPage } from '@/components/auth-provider';
import { ReviewSessionPage } from '@/components/vocabulary-review';
function Route() {
  const {sessionId}=useParams<{sessionId:string}>();
  return <ProtectedPage><ReviewSessionPage key={sessionId} id={sessionId} /></ProtectedPage>;
}
export default function Page() {
  return <Suspense fallback={<p>Loading vocabulary review…</p>}><Route /></Suspense>;
}
