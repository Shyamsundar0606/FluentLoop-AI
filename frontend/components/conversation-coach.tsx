"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ai, type CoachSession, type Conversation } from "@/lib/ai";
import { audioURL, speech } from "@/lib/speech";

export function ConversationCoach({ conversation }: { conversation: Conversation }) {
  const [coach, setCoach] = useState<CoachSession | null>(null);
  const [error, setError] = useState("");
  const [audio, setAudio] = useState<string | null>(null);
  const [loadingWord, setLoadingWord] = useState(false);
  const { id, completed_at } = conversation;
  useEffect(() => {
    let active = true;
    ai.coach(id).then(data => { if (active) setCoach(data); })
      .catch(() => { if (active) setError("Coach details could not load. Refresh to retry."); });
    return () => { active = false; };
  }, [id, completed_at]);

  async function play(word: string) {
    setError(""); setLoadingWord(true);
    try {
      const result = await speech.synthesize(word);
      if (!result.asset_id) throw new Error("Audio unavailable.");
      setAudio(audioURL(result.asset_id));
    } catch {
      setError("French audio is unavailable. You can still read the example.");
    } finally {
      setLoadingWord(false);
    }
  }
  return <section aria-label="Conversation coach" className="my-5 space-y-3 rounded-xl border border-violet-100 p-4">
    {error && <p role="alert" className="text-rose-700">{error}</p>}
    {coach?.scenario && <p>{coach.scenario.opening_situation} You are the {coach.scenario.learner_role}.</p>}
    {coach?.summary && <section aria-labelledby="coach-summary" className="space-y-2">
      <h2 id="coach-summary" className="text-lg font-semibold">Conversation summary</h2>
      <p>{coach.summary.messages_exchanged} saved messages · {coach.summary.learner_turns} learner turns</p>
      {!!coach.summary.scenario_goals.length && <p>Scenario goal · {coach.summary.scenario_goals.join(" ")}</p>}
      {!!coach.summary.used_vocabulary.length && <p>Words used in your messages · <span lang="fr">{coach.summary.used_vocabulary.join(", ")}</span></p>}
      <h3 className="font-semibold">Review feedback</h3>
      {coach.summary.correction_count > coach.summary.corrections.length && <p>Showing the 30 most recent feedback items.</p>}
      {coach.summary.corrections.length ? <ul className="space-y-2">{coach.summary.corrections.map((item, index) =>
        <li key={index}>
          <p>{item.has_errors ? "Suggested correction" : "Style suggestion"} · <span lang="fr">{item.original_text}</span></p>
          {item.has_errors && <p lang="fr">{item.corrected_text}</p>}
          {item.explanations.map((explanation, i) => <p key={i}>{explanation}</p>)}
          {item.alternative_expressions.map((alternative, i) => <p key={i} lang="fr">{alternative}</p>)}
        </li>)}</ul> : <p>No corrections were recorded.</p>}
    </section>}
    {!!coach && <details>
      <summary className="font-medium">Vocabulary and next practice</summary>
      <ul className="mt-2 space-y-2">{coach.scenario_vocabulary.map(word => <li key={word.french}>
        <strong lang="fr">{word.french}</strong> · {word.english}
        <p lang="fr">{word.example}</p>
        <button type="button" className="text-violet-700 underline" disabled={loadingWord}
          onClick={() => void play(word.french)}>Load audio for {word.french}</button>
      </li>)}</ul>
      {audio && <audio controls src={audio} className="mt-2 max-w-full" aria-label="Vocabulary audio" />}
      {coach.studied_vocabulary.length > 0 && <p className="mt-2">From your completed lessons · {coach.studied_vocabulary.map(word => word.french).join(", ")}</p>}
      {coach.due_vocabulary.length > 0 && <>
        <ul className="mt-2">{coach.due_vocabulary.map(word => <li key={word.french}>
          <span lang="fr">{word.french}</span> · {word.english}{word.recently_missed ? " · recently missed" : ""}
        </li>)}</ul>
        <Link href="/review" className="text-violet-700 underline">Review due vocabulary</Link>
      </>}
      {coach.studied_grammar.length > 0 && <p>
        <Link href={`/grammar?level=${conversation.cefr_level.toLowerCase()}`} className="text-violet-700 underline">Review studied grammar</Link>
        {" · "}{coach.studied_grammar.join(", ")}
      </p>}
    </details>}
  </section>;
}
