"use client";
import Link from "next/link";
import type { FormEvent, ReactNode, RefObject } from "react";
import type { Session, Turn } from "@/lib/speech";
import { inputClass } from "./auth-shell";
import { ChatText } from "./ui";

export function VoiceChat({session, busy, reviewId, text, fieldRef, onText, onConfirm, onRecordAgain, onReview, renderAudio, renderInputAudio}: {
  session: Session; busy: boolean; reviewId?: string; text: string;
  fieldRef: RefObject<HTMLTextAreaElement | null>;
  onText: (value: string) => void; onConfirm: (event: FormEvent) => void;
  onRecordAgain: (id: string) => void; onReview: (turn: Turn) => void;
  renderAudio: (turn: Turn) => ReactNode; renderInputAudio: (turn: Turn) => ReactNode;
}) {
  const confirmed = new Set(session.turns.flatMap(turn => turn.review ? [turn.review.source_turn_id] : []));
  return <ol className="voice-thread" aria-label="Voice conversation turns" aria-live="polite" aria-relevant="additions">
    {session.turns.filter(turn => !confirmed.has(turn.id)).map(turn => {
      const reviewing = turn.id === reviewId;
      const recording = turn.review ? session.turns.find(source => source.id === turn.review?.source_turn_id) : turn;
      const edited = turn.review && (turn.review.edited ?? turn.review.original_text !== turn.review.confirmed_text);
      return <li key={turn.id} className="voice-chat-turn" data-turn-id={turn.id}>
        <div className={`chat-bubble chat-bubble-user ${reviewing ? "voice-review-bubble" : ""}`}>
          <p className="chat-speaker">You {edited && <span className="edited-indicator">Edited transcript</span>}</p>
          {reviewing ? <form className="voice-review" data-review="true" aria-label="Review uncertain recognition" onSubmit={onConfirm}>
            <p className="mb-3 text-sm">Check what we heard and correct any mistakes.</p>
            <label className="block text-sm">Corrected sentence<textarea ref={fieldRef} className={inputClass} required maxLength={4000} value={text} disabled={busy} onChange={e => onText(e.target.value)} /></label>
            <div className="mt-3 flex flex-wrap gap-3"><button className="button button-primary" disabled={busy || !text.trim()}>{busy ? "Sending…" : "Confirm and send"}</button><button type="button" className="button button-secondary" disabled={busy} onClick={() => onRecordAgain(turn.id)}>Record again</button></div>
          </form> : <p className="chat-text">{turn.review?.confirmed_text ?? (turn.transcription_status === "uncertain" ? "Unconfirmed recording" : turn.transcript || "No usable French speech recognized.")}</p>}
          {reviewing && <p className="mt-3 text-xs muted"><strong>Original recognized text:</strong> {turn.transcript}</p>}
          {(turn.transcription || turn.review) && !reviewing && <details className="mt-2 recognition-details"><summary>Recognition details</summary>
            <p className="text-xs"><strong>Original recognized text:</strong> {turn.review?.original_text ?? (turn.transcript || "No words recognized.")}</p>
            <p className="mt-1 text-xs muted">{turn.transcription_status} · {turn.status}</p>
            {turn.review && <p className="mt-1 text-xs muted">Confirmed by you · {new Date(turn.review.confirmed_at).toLocaleString()}</p>}
            {turn.transcription_status === "uncertain" && turn.transcript && session.status === "active" && <button className="button button-quiet" disabled={busy} onClick={() => onReview(turn)}>Review this recording</button>}
            {recording && renderInputAudio(recording)}
          </details>}
        </div>
        {turn.tutor && <article className="chat-bubble chat-bubble-tutor" aria-label="Tutor reply">
          <p className="chat-speaker">Tutor</p><ChatText text={turn.tutor.answer} />
          {renderAudio(turn)}
          <details className="mt-2"><summary>Learning context{turn.tutor.grounding_status === "draft_preview" ? " · unreviewed draft" : ""}</summary>
            <p className="text-xs muted">{turn.tutor.grounding_status === "draft_preview" ? "Unreviewed draft context" : turn.tutor.sources.length ? "Curriculum context supplied; AI explanations may contain mistakes." : "General model knowledge"}</p>
            {turn.tutor.sources.map(source => <Link key={source.lesson_id} href={source.url} className="mt-2 block text-xs text-violet-700">{source.title}</Link>)}
          </details>
        </article>}
      </li>;
    })}
  </ol>;
}
