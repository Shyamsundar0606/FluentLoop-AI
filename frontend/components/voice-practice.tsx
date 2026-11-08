"use client";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ProtectedPage, useAuth } from "./auth-provider";
import { FormMessage, inputClass } from "./auth-shell";
import { VoiceRecorder, type VoiceRecorderHandle } from "./voice-recorder";
import { VoiceChat } from "./voice-chat";
import { Icon } from "./ui";
import {
  speech,
  Session,
  Target,
  Attempt,
  Audio,
  audioURL,
  Progress,
  Turn,
} from "@/lib/speech";

type Screen =
  | "home"
  | "conversations"
  | "conversation"
  | "pronunciation"
  | "target"
  | "history";
export function VoicePractice({ screen, id }: { screen: Screen; id?: string }) {
  return (
    <ProtectedPage>
      <Content screen={screen} id={id} />
    </ProtectedPage>
  );
}
function PrivateAudio({
  asset,
  label,
  onDelete,
}: {
  asset: string;
  label: string;
  onDelete?: () => void;
}) {
  const [error, setError] = useState("");
  const { user } = useAuth();
  const [speed, setSpeed] = useState(
    user?.preferences.audio_playback_speed ?? 1,
  );
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  return (
    <div className="my-3">
      <div className="audio-play">
        <button
          className="button button-secondary"
          onClick={async () => {
            if (!audioRef.current) return;
            try {
              if (playing) audioRef.current.pause();
              else await audioRef.current.play();
            } catch {
              setError(
                "Audio expired, unavailable, or access no longer permitted.",
              );
            }
          }}
        >
          <Icon name="play" />
          {playing
            ? "Pause audio"
            : label.includes("tutor")
              ? "Play tutor audio"
              : label.includes("reference")
                ? "Listen to sentence"
                : "Play your recording"}
        </button>
      </div>
      <details className="audio-options">
        <summary>Audio options &amp; privacy</summary>
        <audio
          ref={audioRef}
          onLoadedMetadata={(event) => {
            event.currentTarget.playbackRate = speed;
          }}
          aria-label={label}
          controls
          preload="metadata"
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => setPlaying(false)}
          crossOrigin="use-credentials"
          src={audioURL(asset)}
          className="mt-2 w-full"
          onError={() =>
            setError(
              "Audio expired, unavailable, or access no longer permitted.",
            )
          }
        />
        <label className="my-2 block text-sm">
          Playback speed
          <select
            className="ml-2 rounded border bg-transparent px-2 py-1"
            value={speed}
            onChange={(event) => {
              const value = Number(event.target.value);
              setSpeed(value);
              if (audioRef.current) audioRef.current.playbackRate = value;
            }}
          >
            {[0.5, 0.75, 1, 1.25, 1.5, 2].map((value) => (
              <option key={value} value={value}>
                {value}×
              </option>
            ))}
          </select>
        </label>
        <button
          className="mt-2 text-sm text-rose-700"
          onClick={async () => {
            try {
              await speech.deleteAudio(asset);
              onDelete?.();
            } catch (e) {
              setError(
                e instanceof Error ? e.message : "Could not delete audio.",
              );
            }
          }}
        >
          Delete this audio
        </button>
      </details>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
function Content({ screen, id }: { screen: Screen; id?: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [session, setSession] = useState<Session | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [target, setTarget] = useState<Target | null>(null);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [progress, setProgress] = useState<Progress[]>([]);
  const [reference, setReference] = useState<Audio | null>(null);
  const [scenarios, setScenarios] = useState<
    Awaited<ReturnType<typeof speech.scenarios>>
  >([]);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("Checking speech services…");
  const [speechUnavailable, setSpeechUnavailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");
  const [fallbackText, setFallbackText] = useState("");
  const recorderControl = useRef<VoiceRecorderHandle | null>(null);
  const activeReviewId = useRef<string | null>(null);
  const dismissedReviews = useRef(new Set<string>());
  const [reviewSource, setReviewSource] = useState<{
    id: string;
    text: string;
  } | null>(null);
  const reviewField = useRef<HTMLTextAreaElement | null>(null);
  useEffect(() => {
    if (reviewSource) { reviewField.current?.focus(); reviewField.current?.scrollIntoView({block: "center"}); }
  }, [reviewSource]);
  const textRequest = useRef<{
    message: string;
    id: string;
    reviewedTurnId?: string;
  } | null>(null);
  const lock = useRef(false);
  const applySession = useCallback((value: Session) => {
    setSession(value);
    const latest = value.turns[value.turns.length - 1];
    if (value.status === "active" && latest?.transcription_status === "uncertain" && latest.transcript.trim() && !dismissedReviews.current.has(latest.id)) {
      if (activeReviewId.current !== latest.id) {
        activeReviewId.current = latest.id;
        setReviewSource({id: latest.id, text: latest.transcript});
        setText(latest.transcript);
        textRequest.current = null;
      }
    } else if (activeReviewId.current) {
      activeReviewId.current = null;
      setReviewSource(null);
      setText("");
    }
  }, []);
  function reviewTurn(turn: Turn) {
    activeReviewId.current = turn.id;
    setReviewSource({id: turn.id, text: turn.transcript}); setText(turn.transcript); textRequest.current = null;
  }
  function recordAgain(sourceId: string) {
    dismissedReviews.current.add(sourceId);
    activeReviewId.current = null;
    setReviewSource(null); setText(""); textRequest.current = null;
    recorderControl.current?.recordAgain();
  }
  const level = user?.preferences.current_level.toUpperCase();
  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const health = await speech.health();
        if (active) {
          setStatus(
            `Recognition ${health.asr ? "available" : "unavailable"} · French voice ${health.tts ? "available" : "unavailable"} · acoustic scoring unavailable`,
          );
          setSpeechUnavailable(!health.asr || !health.tts);
        }
        if (screen === "conversation" && id) {
          const value = await speech.get(id);
          if (active) applySession(value);
        } else if (screen === "target" && id) {
          const [value, history] = await Promise.all([
            speech.target(id),
            speech.attempts(0, id),
          ]);
          if (active) {
            setTarget(value);
            setAttempts(history.filter((a) => a.target.id === id));
          }
        } else {
          const values = await speech.sessions();
          if (active) setSessions(values);
          if (screen === "home" || screen === "conversations") {
            const rows = await speech.scenarios();
            if (active) setScenarios(rows);
          }
          if (screen === "pronunciation") {
            const rows = await speech.targets();
            if (active) setTargets(rows);
          }
          if (screen === "history") {
            const [rows, stats] = await Promise.all([
              speech.attempts(),
              speech.progress(),
            ]);
            if (active) {
              setAttempts(rows);
              setProgress(stats);
            }
          }
        }
      } catch (e) {
        if (active)
          setError(
            e instanceof Error
              ? e.message
              : "Voice practice could not be loaded.",
          );
      }
    };
    void run();
    return () => {
      active = false;
    };
  }, [screen, id, level, applySession]);
  async function start(scenario?: string) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      const value = await speech.start(scenario);
      router.push(`/voice-practice/conversations/${value.id}`);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not start voice practice.",
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function recorded(
    blob: Blob,
    rid: string,
    retain: boolean,
    signal: AbortSignal,
  ) {
    if (!id) return;
    if (screen === "target") {
      const value = await speech.attempt(id, blob, rid, retain, signal);
      setAttempts((rows) => [value, ...rows.filter((a) => a.id !== value.id)]);
    } else {
      await speech.turn(id, blob, rid, retain, signal);
      applySession(await speech.get(id));
    }
  }
  async function sendText(e: FormEvent) {
    e.preventDefault();
    const confirming = e.currentTarget.getAttribute("data-review") === "true";
    const message = (confirming ? text : fallbackText).trim();
    if (!id || lock.current || !message || (confirming && !reviewSource)) return;
    lock.current = true;
    setBusy(true);
    setError("");
    const pending = textRequest.current ?? {
      message,
      id: crypto.randomUUID(),
      reviewedTurnId: confirming ? reviewSource?.id : undefined,
    };
    textRequest.current = pending;
    try {
      await speech.text(
        id,
        pending.message,
        pending.id,
        pending.reviewedTurnId,
      );
      textRequest.current = null;
      setText("");
      setReviewSource(null);
      activeReviewId.current = null;
      setFallbackText("");
      applySession(await speech.get(id));
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Text turn failed. Retry the same text.",
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const refresh = async () => {
    if (id && screen === "conversation") applySession(await speech.get(id));
    else setAttempts(await speech.attempts());
  };
  return (
    <main className="min-h-screen bg-slate-50 p-5 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="mx-auto max-w-4xl">
        <p className="text-sm text-violet-700">
          French · {session?.cefr_level ?? target?.level ?? level}
        </p>
        <h1 className="my-3 text-3xl font-bold">
          {screen === "conversation"
            ? (session?.title ?? "Voice conversation")
            : screen === "target"
              ? "Pronunciation practice"
              : screen === "pronunciation"
                ? "Choose a French phrase"
                : screen === "history"
                  ? "Speaking history"
                  : screen === "conversations"
                    ? "French voice conversations"
                    : "Practice Speaking French"}
        </h1>
        <details className="mb-5 text-sm text-slate-500">
          <summary>Speech availability</summary>
          <p aria-live="polite">{status}</p>
        </details>
        {speechUnavailable && (
          <p className="mb-4 text-sm text-amber-800 dark:text-amber-200">
            Some speech services are unavailable. Text practice remains
            available.
          </p>
        )}
        {error && <FormMessage error>{error}</FormMessage>}
        {(screen === "home" || screen === "conversations") && (
          <>
            <section className="panel voice-hero">
              <span className="mic-symbol">
                <Icon name="mic" />
              </span>
              <h2 className="text-xl font-semibold">
                A conversation starts with you.
              </h2>
              <p>
                Have a conversation with your AI French tutor. Practice at your
                saved level, or change it in{" "}
                <Link href="/settings" className="text-violet-700">
                  Settings
                </Link>{" "}
                . Text practice is always available.
              </p>
              <button
                disabled={busy}
                onClick={() => void start()}
                className="button button-primary"
              >
                Start Voice Conversation
              </button>
            </section>
            <details className="mt-6">
              <summary>Try a conversation scenario</summary>
              <h2 className="mt-4 text-lg font-bold">Practice scenarios</h2>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {scenarios.map((s) => (
                  <article
                    key={s.id}
                    className="rounded-2xl border bg-white p-5 dark:bg-slate-900"
                  >
                    <h3 className="font-bold">{s.title}</h3>
                    <p className="my-2 text-sm">{s.description}</p>
                    <p className="text-sm">
                      Tutor: {s.tutor_role} · You: {s.learner_role}
                    </p>
                    <button
                      disabled={busy}
                      className="mt-4 text-violet-700"
                      onClick={() => void start(s.id)}
                    >
                      Start scenario
                    </button>
                  </article>
                ))}
              </div>
            </details>
          </>
        )}
        {(screen === "home" ||
          screen === "conversations" ||
          screen === "history") && (
          <>
            <h2 className="mt-8 text-xl font-bold">Saved speaking sessions</h2>
            {screen !== "home" &&
              sessions.length > 0 &&
              sessions.length % 20 === 0 && (
                <button
                  onClick={async () => {
                    try {
                      const older = await speech.sessions(sessions.length);
                      setSessions((current) => [...current, ...older]);
                      if (!older.length)
                        setError("No older sessions on this page.");
                    } catch (e) {
                      setError(
                        e instanceof Error ? e.message : "History unavailable.",
                      );
                    }
                  }}
                >
                  Load older sessions
                </button>
              )}
            {sessions.length === 0 && (
              <p className="mt-3">No saved speaking sessions yet.</p>
            )}
            <ul className="mt-4 space-y-3">
              {(screen === "home" ? sessions.slice(0, 3) : sessions).map(
                (s) => (
                  <li
                    key={s.id}
                    className="rounded-xl border bg-white p-4 dark:bg-slate-900"
                  >
                    <Link
                      href={`/voice-practice/conversations/${s.id}`}
                      className="font-semibold text-violet-700"
                    >
                      {s.title} · {s.cefr_level}
                    </Link>
                    <p className="mt-1 text-xs">
                      {s.status} ·{" "}
                      {new Date(s.last_activity_at).toLocaleString()}
                    </p>
                  </li>
                ),
              )}
            </ul>
            {screen === "home" && sessions.length > 3 && (
              <Link
                href="/voice-practice/conversations"
                className="button button-quiet mt-3"
              >
                All speaking sessions →
              </Link>
            )}
          </>
        )}
        {screen === "conversation" && session && (
          <>
            {session.opening_french && <p lang="fr" className="rounded-xl bg-violet-50 p-4">{session.opening_french}</p>}
            <Link href={`/ai-tutor/${session.conversation_id}`} className="text-sm font-semibold text-violet-700">
              Open shared transcript and coach options
            </Link>
            {session.draft_preview && (
              <p className="rounded-xl bg-amber-100 p-4 text-amber-900">
                Draft preview · unreviewed curriculum context
              </p>
            )}
            <p className="text-sm muted">
              {session.status === "completed"
                ? "Session complete. Your conversation is saved."
                : "Your conversation is saved as you go. Tap the microphone when you’re ready."}
            </p>

            {session.has_more_turns && (
              <button
                className="my-3 text-violet-700"
                onClick={async () => {
                  try {
                    const older = await speech.get(
                      session.id,
                      session.turns.length,
                    );
                    setSession({
                      ...session,
                      turns: [...older.turns, ...session.turns],
                      has_more_turns: older.has_more_turns,
                    });
                  } catch (e) {
                    setError(
                      e instanceof Error ? e.message : "History unavailable.",
                    );
                  }
                }}
              >
                Load older voice turns
              </button>
            )}
            {session.status === "active" && <div className="voice-mic-dock"><VoiceRecorder controlRef={recorderControl} compact={session.turns.length > 0} onSubmit={recorded} /></div>}
            <VoiceChat session={session} busy={busy} reviewId={reviewSource?.id} text={text} fieldRef={reviewField}
              onText={value => {setText(value); textRequest.current = null;}} onConfirm={sendText} onRecordAgain={recordAgain} onReview={reviewTurn}
              renderInputAudio={turn => turn.input_audio_id ? <PrivateAudio asset={turn.input_audio_id} label="Your retained recording" onDelete={() => void refresh()} /> : null}
              renderAudio={turn => turn.tutor_audio.asset_id && turn.tutor_audio.status === "ready" ?
                <PrivateAudio asset={turn.tutor_audio.asset_id} label="Play or replay tutor voice" onDelete={() => void refresh()} /> :
                <div className="mt-3 text-xs muted">French audio unavailable. Your text response is saved.<button className="button button-quiet ml-2" disabled={busy} onClick={async () => {
                  setBusy(true); try {await speech.retryAudio(session.id, turn.id); applySession(await speech.get(session.id));}
                  catch (e) {setError(e instanceof Error ? e.message : "Voice unavailable.");} finally {setBusy(false);}
                }}>Retry tutor audio</button></div>} />
            {session.status === "active" && (
              <>
                <details
                  className="my-5"

                >
                  <summary>Text fallback &amp; conversation options</summary>
                  <form className="space-y-3" onSubmit={sendText}>
                    <label className="block">Text fallback<textarea className={inputClass} required maxLength={4000} value={fallbackText} disabled={busy} onChange={e => {setFallbackText(e.target.value); textRequest.current = null;}} /></label>
                    <button className="button button-primary" disabled={busy || !fallbackText.trim()}>{busy ? "Processing..." : "Send text instead"}</button>
                  </form>
                  <button
                    className="text-sm text-slate-500"
                    onClick={async () => {
                      try {
                        setSession(await speech.complete(session.id));
                      } catch (e) {
                        setError(
                          e instanceof Error
                            ? e.message
                            : "Could not complete.",
                        );
                      }
                    }}
                  >
                    Finish speaking session
                  </button>
                </details>
              </>
            )}
          </>
        )}
        {screen === "pronunciation" && (
          <>
            <p>
              Practice permitted curriculum examples. Recognition feedback
              compares words; acoustic pronunciation scoring is unavailable.
            </p>
            {targets.length === 0 && (
              <p className="mt-5">
                No accessible pronunciation targets at this level yet. Try an
                independent conversation scenario while curriculum is being
                reviewed.
              </p>
            )}
            <ul className="mt-5 space-y-3">
              {targets.map((t) => (
                <li
                  key={t.id}
                  className="rounded-xl border bg-white p-4 dark:bg-slate-900"
                >
                  <Link
                    href={`/voice-practice/pronunciation/${encodeURIComponent(t.id)}`}
                    className="font-semibold text-violet-700"
                  >
                    {t.text}
                  </Link>
                  <p className="mt-2 text-sm">
                    {t.english} · {t.level}
                    {t.draft_preview ? " · unreviewed draft" : ""}
                  </p>
                </li>
              ))}
            </ul>
          </>
        )}
        {screen === "target" && target && (
          <>
            <section className="rounded-2xl border bg-white p-5 dark:bg-slate-900">
              <h2 className="text-2xl font-bold" lang="fr">
                {target.text}
              </h2>
              <p className="my-3">{target.english}</p>
              {target.draft_preview && (
                <p className="my-2 text-amber-700">
                  Draft preview · unreviewed target
                </p>
              )}
              <p className="text-sm">{target.guidance}</p>
              <button
                disabled={busy}
                className="button button-secondary mt-4"
                onClick={async () => {
                  setBusy(true);
                  try {
                    setReference(
                      await speech.synthesize(target.text, target.id),
                    );
                  } catch (e) {
                    setError(
                      e instanceof Error ? e.message : "Reference unavailable.",
                    );
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Prepare French audio
              </button>
              {reference?.asset_id && (
                <PrivateAudio
                  asset={reference.asset_id}
                  label="French reference audio"
                  onDelete={() => setReference(null)}
                />
              )}
            </section>
            <VoiceRecorder onSubmit={recorded} />
            <p className="text-sm text-slate-500">
              Pronunciation assessment: not available. No percentage is
              calculated.
            </p>
          </>
        )}
        {(screen === "target" || screen === "history") && (
          <>
            <h2 className="mt-7 text-xl font-bold">
              Previous pronunciation attempts
            </h2>
            {attempts.length === 0 && <p className="mt-3">No attempts yet.</p>}
            {attempts.length > 0 && attempts.length % 20 === 0 && (
              <button
                onClick={async () => {
                  try {
                    const older = await speech.attempts(
                      attempts.length,
                      screen === "target" ? id : undefined,
                    );
                    setAttempts((current) => [...current, ...older]);
                    if (!older.length)
                      setError("No older attempts on this page.");
                  } catch (e) {
                    setError(
                      e instanceof Error ? e.message : "History unavailable.",
                    );
                  }
                }}
              >
                Load older attempts
              </button>
            )}
            <ul className="mt-4 space-y-4">
              {attempts.map((a) => (
                <li
                  key={a.id}
                  className="rounded-2xl border bg-white p-5 dark:bg-slate-900"
                >
                  <p className="font-semibold">Target: {a.target.text}</p>
                  <p className="my-2">
                    Recognized: {a.recognized_text || "No usable speech"}
                  </p>
                  <p className="text-sm">{a.recognition_feedback}</p>
                  <p className="mt-2 text-sm">
                    Acoustic assessment:{" "}
                    {a.assessment_status.replaceAll("_", " ")}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    {a.limitations} · {new Date(a.created_at).toLocaleString()}
                  </p>
                  {a.input_audio_id && (
                    <PrivateAudio
                      asset={a.input_audio_id}
                      label="Your retained pronunciation recording"
                      onDelete={() => void refresh()}
                    />
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
        {screen === "history" && (
          <>
            <h2 className="mt-7 text-xl font-bold">Practice activity</h2>
            <ul className="mt-3 space-y-2">
              {progress.map((p) => (
                <li key={p.target.id}>
                  {p.target.text} · {p.attempt_count} attempts · acoustic
                  scoring unavailable
                </li>
              ))}
            </ul>
          </>
        )}
        <details className="privacy-note">
          <summary>Speech privacy and limitations</summary>
          <p>
            Local speech processing uses the configured private speech service
            and Ollama. Raw microphone audio is discarded by default after
            processing; you can opt into private replay for up to 24 hours and
            delete retained audio. Generated French audio also expires after 24
            hours. Transcripts and practice metadata remain in your account.
            Speech recognition can make mistakes. Piper SIWIS French voice uses
            a CC-BY 4.0 dataset; synthetic speech is not a certified
            pronunciation assessment.
          </p>
        </details>
      </div>
    </main>
  );
}
