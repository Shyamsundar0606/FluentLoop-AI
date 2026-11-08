'use client';
import { useEffect, useRef, useState } from 'react';
import { apiAudio } from '@/lib/api';
import type { ExerciseAnswer, SessionExercise } from '@/lib/learning';

export function ExerciseInput({ exercise, sessionId, disabled, value, onChange }: {
  exercise: SessionExercise; sessionId: string; disabled: boolean;
  value: ExerciseAnswer | null; onChange: (answer: ExerciseAnswer | null) => void;
}) {
  const [audio, setAudio] = useState('');
  const [audioError, setAudioError] = useState('');
  const [loading, setLoading] = useState(false);
  const url = useRef('');
  const writtenInput = useRef<HTMLInputElement>(null);
  const selection = useRef<number | null>(null);
  useEffect(() => () => { if (url.current) URL.revokeObjectURL(url.current); }, []);
  useEffect(() => {
    if (selection.current === null || !writtenInput.current) return;
    writtenInput.current.focus();
    writtenInput.current.setSelectionRange(selection.current, selection.current);
    selection.current = null;
  }, [value]);
  const kind = exercise.type;
  async function loadAudio() {
    setLoading(true); setAudioError('');
    try {
      const blob = await apiAudio(`/learning/sessions/${sessionId}/exercises/${exercise.id}/audio`);
      if (url.current) URL.revokeObjectURL(url.current);
      url.current = URL.createObjectURL(blob); setAudio(url.current);
    } catch (error) { setAudioError(error instanceof Error ? error.message : 'Audio unavailable.'); }
    finally { setLoading(false); }
  }
  if (kind === 'multiple_choice' || kind === 'listening') return <>
    {kind === 'listening' && <div className="mt-4 space-y-3">
      {!audio && <button type="button" className="btn-secondary" disabled={loading} onClick={() => void loadAudio()}>{loading ? 'Preparing audio…' : 'Load French audio'}</button>}
      {audio && <audio aria-label="French listening audio" className="max-w-full" controls src={audio} preload="auto" />}
      {audioError && <p role="alert">{audioError} <button type="button" onClick={() => void loadAudio()} disabled={loading}>Retry audio</button></p>}
    </div>}
    <fieldset className="mt-5 space-y-3" disabled={disabled}><legend className="sr-only">Choose an answer</legend>
      {exercise.options.map(option => <label key={option.id} className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 ${value && 'selected_option_id' in value && value.selected_option_id === option.id ? 'border-violet-500 bg-violet-50' : 'border-slate-200'}`}>
        <input type="radio" name="answer" value={option.id} checked={!!value && 'selected_option_id' in value && value.selected_option_id === option.id} onChange={() => onChange({ selected_option_id: option.id })} /><span>{option.text}</span>
      </label>)}
    </fieldset>
  </>;
  if (kind === 'fill_blank' || kind === 'short_answer' || kind === 'translation') return <>
    <label className="mt-5 block font-medium">Your answer
    <input ref={writtenInput} className="mt-2 block w-full rounded-xl border border-slate-300 p-4" lang="fr" autoComplete="off" spellCheck={false} maxLength={1000} disabled={disabled}
      value={value && 'text_answer' in value ? value.text_answer : ''} onChange={event => onChange(event.target.value.trim() ? { text_answer: event.target.value } : null)} />
    </label>
    <div role="group" aria-label="Insert a French character" className="mt-2 flex flex-wrap gap-2">
      {['à', 'â', 'æ', 'ç', 'é', 'è', 'ê', 'ë', 'î', 'ï', 'ô', 'œ', 'ù', 'û', 'ü', 'ÿ'].map(character =>
        <button key={character} type="button" disabled={disabled} aria-label={`Insert ${character}`}
          className="min-h-8 min-w-8 rounded border border-violet-200 px-2 text-violet-800"
          onClick={() => {
            const input = writtenInput.current;
            if (!input) return;
            const start = input.selectionStart ?? input.value.length;
            const end = input.selectionEnd ?? start;
            const next = input.value.slice(0, start) + character + input.value.slice(end);
            if (next.length > input.maxLength) return;
            selection.current = start + character.length;
            onChange({ text_answer: next });
          }}>{character}</button>)}
    </div>
  </>;
  if (kind === 'sentence_order') {
    const ids = value && 'tile_ids' in value ? value.tile_ids : [];
    const tiles = exercise.tiles ?? [];
    return <fieldset className="mt-5 space-y-4" disabled={disabled}><legend className="font-medium">Build your sentence</legend>
      <div className="min-h-16 rounded-xl border border-violet-200 p-3" aria-label="Selected words" aria-live="polite">
        {ids.map((id, index) => <button type="button" className="m-1 rounded-lg border bg-violet-50 px-4 py-3" key={id} aria-label={`Remove ${tiles.find(t => t.id === id)?.text}`} onClick={() => onChange({ tile_ids: ids.filter((_, i) => i !== index) })}>{tiles.find(t => t.id === id)?.text}</button>)}
      </div>
      <div aria-label="Available words">{tiles.filter(t => !ids.includes(t.id)).map(tile => <button type="button" key={tile.id} className="m-1 rounded-lg border px-4 py-3" onClick={() => onChange({ tile_ids: [...ids, tile.id] })}>{tile.text}</button>)}</div>
      <button type="button" className="mr-4 text-violet-700 underline" disabled={!ids.length} onClick={() => onChange({ tile_ids: ids.slice(0, -1) })}>Undo word</button>
      <button type="button" className="text-violet-700 underline" disabled={!ids.length} onClick={() => onChange(null)}>Reset sentence</button>
    </fieldset>;
  }
  if (kind === 'matching') {
    const matches = value && 'matches' in value ? value.matches : {};
    return <fieldset className="mt-5 space-y-4" disabled={disabled}><legend className="font-medium">Match the meanings</legend>
      {(exercise.left_items ?? []).map(left => <label className="grid gap-2 sm:grid-cols-2 sm:items-center" key={left.id}><span lang="fr">{left.text}</span>
        <select aria-label={left.text} className="min-w-0 w-full rounded-xl border border-slate-300 p-3" value={matches[left.id] ?? ''} onChange={event => {
          const next = { ...matches }; if (event.target.value) next[left.id] = event.target.value; else delete next[left.id]; onChange({ matches: next });
        }}><option value="">Choose meaning</option>{(exercise.right_items ?? []).map(right => <option key={right.id} value={right.id} disabled={Object.entries(matches).some(([id, v]) => id !== left.id && v === right.id)}>{right.text}</option>)}</select>
      </label>)}
    </fieldset>;
  }
  return <p role="status">This exercise format is unavailable.</p>;
}

export function answerReady(exercise: SessionExercise, answer: ExerciseAnswer | null) {
  if (!answer) return false;
  if ('text_answer' in answer) return !!answer.text_answer.trim();
  if ('tile_ids' in answer) return answer.tile_ids.length === exercise.tiles?.length;
  if ('matches' in answer) return Object.keys(answer.matches).length === exercise.left_items?.length;
  return !!answer.selected_option_id;
}
