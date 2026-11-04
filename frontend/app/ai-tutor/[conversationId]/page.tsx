"use client";
import Link from "next/link";
import { FormEvent, Suspense, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { TutorShell } from "@/components/tutor-shell";
import { buttonClass, FormMessage, inputClass } from "@/components/auth-shell";
import { ai, Conversation } from "@/lib/ai";
import { ChatText } from "@/components/ui";

export default function ChatPage() {
  return (
    <Suspense fallback={<p role="status">Loading conversation…</p>}>
      <ChatRoute />
    </Suspense>
  );
}
function ChatRoute() {
  const { conversationId } = useParams<{ conversationId: string }>();
  return (
    <TutorShell>
      <Chat key={conversationId} id={conversationId} />
    </TutorShell>
  );
}
function Chat({ id }: { id: string }) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);
  const pending = useRef<{ message: string; requestId: string } | null>(null);
  useEffect(() => {
    let active = true;
    ai.get(id)
      .then((c) => {
        if (active) {
          setConversation(c);
          setTitle(c.title);
          const failed = [...c.messages]
            .reverse()
            .find((m) => m.role === "user" && m.response_status !== "success");
          const stored = sessionStorage.getItem(`tutor-pending-${id}`);
          if (stored) {
            try {
              pending.current = JSON.parse(stored);
              setText(pending.current?.message ?? "");
              setRetrying(true);
            } catch {
              sessionStorage.removeItem(`tutor-pending-${id}`);
            }
          } else if (failed?.request_id) {
            pending.current = {
              message: failed.content,
              requestId: failed.request_id,
            };
            setText(failed.content);
            setRetrying(true);
          } else {
            setText(sessionStorage.getItem(`tutor-draft-${id}`) ?? "");
          }
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [id]);
  async function send(event: FormEvent) {
    event.preventDefault();
    if (lock.current || !text.trim()) return;
    lock.current = true;
    setBusy(true);
    setError("");
    const turn = pending.current ?? {
      message: text.trim(),
      requestId: crypto.randomUUID(),
    };
    pending.current = turn;
    setRetrying(true);
    sessionStorage.setItem(`tutor-pending-${id}`, JSON.stringify(turn));
    try {
      await ai.send(id, turn.message, turn.requestId);
      pending.current = null;
      setRetrying(false);
      sessionStorage.removeItem(`tutor-pending-${id}`);
      sessionStorage.removeItem(`tutor-draft-${id}`);
      setText("");
      setConversation(await ai.get(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send message.");
      try {
        setConversation(await ai.get(id));
      } catch {}
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function older() {
    if (!conversation?.messages.length) return;
    try {
      const previous = await ai.get(id, conversation.messages[0].id);
      setConversation({
        ...conversation,
        messages: [...previous.messages, ...conversation.messages],
        has_more_messages: previous.has_more_messages,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "History unavailable.");
    }
  }
  return (
    <>
      {error && <FormMessage error>{error}</FormMessage>}
      {conversation && (
        <>
          <header className="chat-header mb-6">
            <p className="text-sm text-violet-700">
              {conversation.cefr_level} · {conversation.mode} ·{" "}
              {conversation.status}
            </p>
            <h1 className="mt-2 text-xl font-semibold">{conversation.title}</h1>
            <p className="mt-2 text-sm text-slate-500">
              This conversation keeps its starting level. Start a new
              conversation to use a newly selected level.
            </p>
            <details className="mt-3">
              <summary>Conversation options</summary>
              <form
                className="mt-4 flex gap-2"
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    await ai.rename(id, title);
                    setConversation(await ai.get(id));
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Rename failed.");
                  }
                }}
              >
                <input
                  aria-label="Conversation title"
                  className={inputClass}
                  maxLength={120}
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
                <button className="px-3 text-sm font-semibold">Rename</button>
              </form>
            </details>
          </header>
          {conversation.preview_mode && (
            <p className="mb-4 rounded-xl bg-amber-100 p-4 text-amber-900">
              Draft preview: this conversation may use unreviewed curriculum.
            </p>
          )}
          {conversation.has_more_messages && (
            <button
              onClick={() => void older()}
              className="mb-4 text-violet-700"
            >
              Load older messages
            </button>
          )}
          <ol
            aria-label="Conversation messages"
            aria-live="polite"
            aria-relevant="additions"
            className="space-y-4"
          >
            {conversation.messages.map((m) => (
              <li
                key={m.id}
                className={`chat-bubble ${m.role === "user" ? "chat-bubble-user" : "chat-bubble-tutor"}`}
              >
                <p className="chat-speaker">
                  {m.role === "user" ? "You" : "Tutor"}
                </p>
                {m.role === "assistant" && (
                  <details className="mb-2">
                    <summary>
                      Learning context
                      {m.grounding_status === "draft_preview"
                        ? " · unreviewed draft"
                        : ""}
                    </summary>
                    <p className="text-xs text-slate-500">
                      {m.grounding_status === "general_knowledge"
                        ? "General model knowledge · no curriculum sources"
                        : m.grounding_status === "draft_preview"
                          ? "Unreviewed draft context"
                          : "Curriculum context supplied · AI explanation is not verified"}
                    </p>
                  </details>
                )}
                <ChatText text={m.content} />
                {m.correction && (
                  <div className="mt-3 text-sm">
                    <p>Original: {m.correction.original_text}</p>
                    <p>
                      {m.correction.has_errors
                        ? "Errors identified"
                        : "No errors identified"}
                    </p>
                    {m.correction.alternative_expressions.map((a, i) => (
                      <p key={i}>Stylistic alternative: {a}</p>
                    ))}
                  </div>
                )}
                {m.response_status !== "success" && (
                  <p className="mt-2 text-sm text-amber-700">
                    {m.response_status === "failed"
                      ? "Response failed; retry the saved message."
                      : "Response pending; retry after the current generation finishes."}
                  </p>
                )}
                {m.sources?.length > 0 && (
                  <ul className="mt-3 space-y-2">
                    {m.sources.map((s) => (
                      <li key={s.lesson_id}>
                        <Link
                          href={s.url}
                          className="text-sm font-semibold text-violet-700 dark:text-violet-300"
                        >
                          {s.title}
                          {s.draft_preview ? " · draft preview" : ""}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ol>
          {busy && (
            <p role="status" className="my-4">
              The tutor is thinking…
            </p>
          )}
          {conversation.status === "active" ? (
            <form onSubmit={send} className="chat-composer space-y-3">
              <label className="block">
                {conversation.mode === "correction"
                  ? "French sentence"
                  : "Message"}
                <textarea
                  aria-label={
                    conversation.mode === "correction"
                      ? "French sentence"
                      : "Message"
                  }
                  className={inputClass}
                  required
                  maxLength={4000}
                  disabled={busy || retrying}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => {
                    if (
                      e.key === "Enter" &&
                      !e.shiftKey &&
                      !e.nativeEvent.isComposing
                    ) {
                      e.preventDefault();
                      e.currentTarget.form?.requestSubmit();
                    }
                  }}
                />
              </label>
              <p className="text-xs text-slate-500">
                Enter to send · Shift+Enter for a new line. Ask for a hint, a
                simpler explanation, or a practice summary.
              </p>
              <button className={buttonClass} disabled={busy || !text.trim()}>
                {busy
                  ? "Generating…"
                  : retrying
                    ? "Retry saved message"
                    : "Send message"}
              </button>
            </form>
          ) : (
            <p className="mt-5">
              Archived conversation.{" "}
              <Link href="/ai-tutor" className="text-violet-700">
                Start another practice
              </Link>
            </p>
          )}
        </>
      )}
    </>
  );
}
