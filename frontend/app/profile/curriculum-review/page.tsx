'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { ProtectedPage } from '@/components/auth-provider';
import { apiAudio, apiRequest, getApiErrorMessage } from '@/lib/api';

type QueueItem = { slug: string; title: string; version: string; outstanding: string[] };
type Exercise = { id: string; type: string; prompt: string };
type Packet = {
  digest: string;
  categories: string[];
  technical_issues: string[];
  readiness: { outstanding: string[]; independent_licensing: boolean; complete: boolean };
  content: { version: string; title: string; lessons: { slug: string; title: string; exercises: Exercise[] }[] };
  history: { category: string; status: string; reviewer_id: string; reviewed_at: string; version: string; digest: string;
    qualification: string; findings: string; required_corrections: string; evidence: string }[];
};

function Listening({ slug, exercise }: { slug: string; exercise: Exercise }) {
  const [audio, setAudio] = useState('');
  const [status, setStatus] = useState('');
  const [pending, setPending] = useState(false);
  useEffect(() => () => { if (audio) URL.revokeObjectURL(audio); }, [audio]);
  async function load() {
    setPending(true);
    setStatus('');
    try {
      const blob = await apiAudio(`/content-review/${encodeURIComponent(slug)}/listening?exercise_id=${exercise.id}`);
      setAudio(URL.createObjectURL(blob));
    } catch (error) {
      setStatus(getApiErrorMessage(error, 'Audio unavailable. Try again.'));
    } finally {
      setPending(false);
    }
  }
  return <div className="my-3">
    <button type="button" className="button button-secondary" disabled={pending} onClick={() => void load()}>
      {pending ? 'Loading audio…' : 'Load review audio'}
    </button>
    {status && <p role="alert">{status}</p>}
    {audio && <audio className="mt-2 max-w-full" controls src={audio} aria-label={exercise.prompt} />}
  </div>;
}

export default function CurriculumReviewPage() {
  return <ProtectedPage><ReviewWorkspace /></ProtectedPage>;
}

function ReviewWorkspace() {
  const [items, setItems] = useState<QueueItem[] | null>(null);
  const [slug, setSlug] = useState('');
  const [packet, setPacket] = useState<Packet | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    apiRequest<{ items: QueueItem[] }>('/content-review/queue')
      .then(result => setItems(result.items))
      .catch(reason => setError(getApiErrorMessage(reason, 'Review queue unavailable.')));
  }, []);
  const path = (key: string) => `/content-review/${encodeURIComponent(key)}`;
  async function open(key: string) {
    setSlug(key); setPacket(null); setError(''); setMessage(''); setBusy(true);
    try { setPacket(await apiRequest<Packet>(path(key))); }
    catch (reason) { setError(getApiErrorMessage(reason, 'Review packet unavailable.')); }
    finally { setBusy(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!packet || busy) return;
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    setBusy(true); setError(''); setMessage('');
    try {
      await apiRequest(`${path(slug)}/decisions`, { method: 'POST', body: JSON.stringify({
        ...values, digest: packet.digest, version: packet.content.version,
      }) });
      form.reset();
      setMessage('Review decision saved.');
      setPacket(await apiRequest<Packet>(path(slug)));
    } catch (reason) { setError(getApiErrorMessage(reason, 'Could not save the review.')); }
    finally { setBusy(false); }
  }
  return <main className="mx-auto max-w-4xl space-y-5 px-5 py-8">
    <h1 className="text-3xl font-bold">Curriculum review</h1>
    <p>Inspect draft packets and record independent decisions for an exact version.</p>
    {error && <p role="alert" className="text-rose-700">{error}</p>}
    {message && <p role="status">{message}</p>}
    {!items && !error && <p role="status">Loading review queue…</p>}
    {items?.length === 0 && <p>No draft packets are available.</p>}
    {items && <ul className="space-y-2">{items.map(item => <li key={item.slug}>
      <button type="button" className="button button-secondary" disabled={busy} onClick={() => void open(item.slug)}>
        {item.title} · {item.version}
      </button>
    </li>)}</ul>}
    {busy && !packet && <p role="status">Loading review packet…</p>}
    {packet && <section className="space-y-4 rounded-xl border border-violet-100 bg-white p-5">
      <h2 className="text-xl font-semibold">{packet.content.title}</h2>
      <p>Version {packet.content.version} · <code className="break-all">{packet.digest}</code></p>
      <p>{packet.readiness.outstanding.length ? `Outstanding reviews: ${packet.readiness.outstanding.join(', ')}` : 'All categories have a decision.'}</p>
      {!packet.readiness.independent_licensing && <p>Independent licensing evidence is outstanding.</p>}
      {packet.technical_issues.length > 0 && <ul className="list-disc pl-5">{packet.technical_issues.map((issue, index) => <li key={index}>{issue}</li>)}</ul>}
      {packet.content.lessons.map(lesson => <details key={lesson.slug}>
        <summary>{lesson.title}</summary>
        <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 text-sm">{JSON.stringify(lesson, null, 2)}</pre>
        {lesson.exercises.filter(exercise => exercise.type === 'listening').map(exercise => <Listening key={exercise.id} slug={slug} exercise={exercise} />)}
      </details>)}
      <details><summary>Decision history</summary>
        {packet.history.length ? <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words text-sm">{JSON.stringify(packet.history, null, 2)}</pre> : <p>No independent decisions recorded.</p>}
      </details>
      {packet.categories.length > 0 && <form className="space-y-3" onSubmit={submit}>
        <fieldset className="space-y-3" disabled={busy}>
          <legend className="font-semibold">Record a review decision</legend>
          <label className="block">Category <select name="category" className="ml-2 border p-2">{packet.categories.map(category => <option key={category}>{category}</option>)}</select></label>
          <label className="block">Decision <select name="status" className="ml-2 border p-2"><option value="changes_requested">Request changes</option><option value="approved">Approve</option></select></label>
          <label className="block">Findings <textarea name="findings" required minLength={8} maxLength={4000} className="block w-full rounded border p-2" /></label>
          <label className="block">Required corrections <textarea name="required_corrections" maxLength={4000} className="block w-full rounded border p-2" /></label>
          <label className="block">Supporting evidence <textarea name="evidence" maxLength={2000} className="block w-full rounded border p-2" /></label>
          <button type="submit" className="button button-primary">Save review decision</button>
        </fieldset>
      </form>}
    </section>}
  </main>;
}
