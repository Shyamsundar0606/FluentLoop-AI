"use client";
import { useEffect, useImperativeHandle, useRef, useState, type Ref } from "react";
import { FormMessage } from "./auth-shell";
import { Icon } from "./ui";

type State =
  | "idle"
  | "requesting_permission"
  | "recording"
  | "paused"
  | "recorded"
  | "uploading"
  | "completed"
  | "failed";
export type VoiceRecorderHandle = { recordAgain: () => void };
export function VoiceRecorder({
  onSubmit,
  controlRef,
  compact = false,
}: {
  controlRef?: Ref<VoiceRecorderHandle>;
  compact?: boolean;
  onSubmit: (
    blob: Blob,
    id: string,
    retain: boolean,
    signal: AbortSignal,
  ) => Promise<void>;
}) {
  const [state, setState] = useState<State>("idle");
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState("");
  const [url, setURL] = useState("");
  const [retain, setRetain] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const parts = useRef<Blob[]>([]);
  const recording = useRef<Blob | null>(null);
  const requestId = useRef("");
  const controller = useRef<AbortController | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const alive = useRef(true);
  const lock = useRef(false);
  const playbackURL = useRef("");
  const cancelled = useRef(false);
  function release() {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      cancelled.current = true;
      controller.current?.abort();
      if (recorder.current && recorder.current.state !== "inactive")
        recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
      if (timer.current) clearInterval(timer.current);
      if (playbackURL.current) URL.revokeObjectURL(playbackURL.current);
    };
  }, []);
  function stop() {
    if (recorder.current?.state !== "inactive") recorder.current?.stop();
    release();
  }
  async function start() {
    if (lock.current) return;
    lock.current = true;
    setError("");
    setState("requesting_permission");
    setRetain(false);
    setURL("");
    cancelled.current = false;
    try {
      if (
        !window.isSecureContext ||
        !navigator.mediaDevices?.getUserMedia ||
        typeof MediaRecorder === "undefined"
      )
        throw new Error(
          "Microphone recording is unsupported. Use HTTPS or localhost, or continue with text.",
        );
      const media = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
        video: false,
      });
      if (!alive.current || cancelled.current) {
        media.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = media;
      parts.current = [];
      const mime = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ].find((t) => MediaRecorder.isTypeSupported(t));
      if (!mime) {
        release();
        throw new Error(
          "This browser has no supported recording format. Use text fallback.",
        );
      }
      const rec = new MediaRecorder(media, {
        mimeType: mime,
        audioBitsPerSecond: 64000,
      });
      recorder.current = rec;
      rec.ondataavailable = (e) => {
        if (recorder.current === rec && e.data.size) parts.current.push(e.data);
      };
      rec.onerror = () => {
        if (recorder.current !== rec) return;
        release();
        if (alive.current) {
          setError(
            "The microphone stopped unexpectedly. Record again or use text.",
          );
          setState("failed");
        }
      };
      rec.onstop = () => {
        media.getTracks().forEach((track) => track.stop());
        if (recorder.current !== rec) return;
        release();
        if (!alive.current || cancelled.current) return;
        const blob = new Blob(parts.current, { type: mime });
        if (!blob.size) {
          setError("Recording is empty.");
          setState("failed");
          return;
        }
        recording.current = blob;
        requestId.current = crypto.randomUUID();
        if (playbackURL.current) URL.revokeObjectURL(playbackURL.current);
        playbackURL.current = URL.createObjectURL(blob);
        setURL(playbackURL.current);
        setState("recorded");
      };
      media.getAudioTracks().forEach((t) => {
        t.onended = () => {
          if (rec.state !== "inactive") stop();
          if (alive.current)
            setError(
              "Microphone access ended. Review what was captured or record again.",
            );
        };
      });
      rec.start(250);
      setSeconds(0);
      setState("recording");
      const began = Date.now();
      timer.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - began) / 1000);
        if (alive.current) setSeconds(elapsed);
        if (elapsed >= 29) stop();
      }, 250);
    } catch (e) {
      release();
      if (alive.current) {
        setError(
          e instanceof DOMException && e.name === "NotAllowedError"
            ? "Microphone permission denied. Allow it explicitly in browser settings, or use text."
            : e instanceof Error
              ? e.message
              : "Microphone unavailable.",
        );
        setState("failed");
      }
    } finally {
      lock.current = false;
    }
  }
  function cancel() {
    cancelled.current = true;
    if (recorder.current?.state !== "inactive") recorder.current?.stop();
    recorder.current = null;
    release();
    recording.current = null;
    if (playbackURL.current) URL.revokeObjectURL(playbackURL.current);
    playbackURL.current = "";
    setURL("");
    setState("idle");
  }
  async function submit() {
    if (lock.current || !recording.current) return;
    lock.current = true;
    setState("uploading");
    setError("");
    controller.current = new AbortController();
    try {
      await onSubmit(
        recording.current,
        requestId.current,
        retain,
        controller.current.signal,
      );
      if (alive.current) setState("completed");
    } catch (e) {
      if (alive.current) {
        setError(
          e instanceof Error
            ? e.message
            : "Upload failed. Retry the same recording.",
        );
        setState("recorded");
      }
    } finally {
      lock.current = false;
    }
  }
  useImperativeHandle(controlRef, () => ({recordAgain: () => {cancel(); void start();}}));
  const capturing = state === "recording" || state === "paused";
  return (
    <section className={`recorder-panel ${compact ? "recorder-compact" : ""}`} aria-label="Microphone recording">
      <p role="status" className="recorder-status">
        {state === "recording" ? (
          <>
            <span className="recording-dot" />
            Recording · {seconds}s / 30s
          </>
        ) : state === "paused" ? (
          `Recording paused · ${seconds}s`
        ) : state === "uploading" ? (
          "Understanding your French…"
        ) : state === "requesting_permission" ? (
          "Waiting for microphone permission…"
        ) : state === "recorded" ? (
          "Microphone off · review your recording"
        ) : state === "completed" ? (
          "Microphone off · attempt saved"
        ) : (
          "Microphone off"
        )}
      </p>
      <div className="recorder-action-area">{!capturing &&
        state !== "uploading" &&
        state !== "requesting_permission" &&
        state !== "recorded" && (
          <>
            <button
              aria-label="Record French"
              title="Record French"
              onClick={() => void start()}
              className="mic-button"
            >
              <Icon name="mic" />
            </button>
            <p className="text-sm font-semibold">
              {state === "completed" ? "Speak again" : "Tap to speak"}
            </p>
          </>
        )}
      {capturing && (
        <>
          <button
            onClick={stop}
            className="mic-button is-recording"
            aria-label="Stop recording"
          >
            <Icon name="stop" />
          </button>
          <p className="text-sm font-semibold">Stop recording</p>
        </>
      )}
      </div>
      {state === "requesting_permission" && (
        <p className="my-5 text-sm muted">
          Allow microphone access in your browser to start.
        </p>
      )}
      {url && (
        <audio
          className="mx-auto mt-5 w-full max-w-lg"
          aria-label="Review your recording"
          controls
          src={url}
        />
      )}
      <div className="recorder-controls">
        {state === "recorded" && (
          <>
            <button
              onClick={() => void start()}
              className="button button-secondary"
            >
              Record again
            </button>
            <button
              onClick={() => void submit()}
              className="button button-primary"
            >
              Send recording
            </button>
          </>
        )}
        {(capturing ||
          state === "recorded" ||
          state === "requesting_permission") && (
          <button onClick={cancel} className="button button-quiet">
            Cancel recording
          </button>
        )}
      </div>
      <p className="mt-4 text-[11px] muted">
        Record only when you choose. Up to 30 seconds. Audio is discarded after
        processing unless you choose private replay.
      </p>
      <details className="recorder-options">
        <summary>Recording options &amp; privacy</summary>
        {capturing && (
          <button
            className="button button-secondary mb-3"
            onClick={() => {
              const r = recorder.current;
              if (r?.state === "recording") {
                r.pause();
                setState("paused");
              } else if (r?.state === "paused") {
                r.resume();
                setState("recording");
              }
            }}
          >
            {state === "paused" ? "Resume recording" : "Pause recording"}
          </button>
        )}
        {state === "recorded" && (
          <label className="my-3 flex items-start gap-3 text-xs leading-6">
            <input
              type="checkbox"
              checked={retain}
              onChange={(e) => setRetain(e.target.checked)}
            />
            Keep this recording privately for up to 24 hours for replay.
            Otherwise it is discarded after processing.
          </label>
        )}
        <p className="text-xs muted">
          Recording starts only after you press the microphone. Stop or cancel
          at any time. Microphone access ends when you stop recording or leave
          this page.
        </p>
      </details>
      {error && (
        <div className="mt-4">
          <FormMessage error>{error}</FormMessage>
        </div>
      )}
    </section>
  );
}
