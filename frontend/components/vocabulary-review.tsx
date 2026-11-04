"use client";
import { useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from './auth-provider';
import { PageHeader } from './ui';
import { inputClass } from './auth-shell';
import { getApiErrorMessage } from '@/lib/api';
import { study, type Due, type ReviewSession, type Feedback, type ReviewProgress, type ReviewHistory } from '@/lib/study';

export function ReviewMetrics() {
  const {user}=useAuth();
  const [metrics,setMetrics]=useState<ReviewProgress|null>(null);
  const [error,setError]=useState('');
  useEffect(() => {let active=true;study.progress().then(v=>{if(active)setMetrics(v);}).catch(()=>{if(active)setError('Vocabulary review progress is unavailable.');});return()=>{active=false;};},[user?.id,user?.preferences.current_level]);
  return <section className="review-metrics" aria-label="Vocabulary review progress"><h2 className="panel-title">Vocabulary review</h2>
    {error && <p role="alert">{error}</p>}{metrics && <p className="mt-2 text-sm">{metrics.reviews_completed} reviews completed · {metrics.cards_due} cards due at your saved level · {metrics.vocabulary_items_studied} vocabulary items studied</p>}
    <Link href="/review" className="text-sm text-violet-700">Review vocabulary and history →</Link></section>;
}

export function ReviewHome() {
  const {user}=useAuth();
  const router=useRouter();
  const [due,setDue]=useState<Due|null>(null);
  const [history,setHistory]=useState<ReviewHistory[]>([]);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const lock=useRef(false);
  const request=useRef<string|null>(null);
  useEffect(()=>{let active=true;Promise.all([study.due(),study.history()]).then(([d,h])=>{if(active){setDue(d);setHistory(h.items);}}).catch(e=>{if(active)setError(getApiErrorMessage(e,'Vocabulary review is unavailable.'));});return()=>{active=false;};},[user?.id,user?.preferences.current_level]);
  async function start() {
    if(lock.current)return;lock.current=true;setBusy(true);setError('');
    try {request.current ??= crypto.randomUUID();const saved=await study.startReview(request.current);request.current=null;router.push('/review/sessions/'+saved.id);}
    catch(e){setError(getApiErrorMessage(e,'Could not start a review.'));}finally{lock.current=false;setBusy(false);}
  }
  return <main><PageHeader title="Review vocabulary" description="A few words at a time, with reviews scheduled from your answers." />
    {error && <p role="alert" className="my-4">{error}</p>}
    {!due && !error && <p role="status">Loading reviews…</p>}
    {due && <section className="review-focus"><p className="eyebrow">{due.cefr_level}</p><h2 className="text-xl font-semibold">{due.due_count} cards due</h2>
      {due.due_count===0 && due.new_vocabulary_count===0 ? <p className="mt-3">No permitted vocabulary is due or available to learn right now. Tutor and speaking practice remain available.</p> : <><p className="my-3">Review up to three permitted words. About 2 minutes.</p><button className="button button-primary" disabled={busy} onClick={()=>void start()}>{busy?'Starting…':'Start vocabulary review'}</button></>}
      {due.next_due_at && <p className="mt-3 text-sm muted">Next scheduled review: {new Date(due.next_due_at).toLocaleString()}</p>}
    </section>}
    <ReviewMetrics />
    <section className="mt-7" aria-label="Review history"><h2 className="panel-title">Review history</h2>
      {history.length===0 && <p className="mt-3 text-sm muted">No reviews recorded yet.</p>}
      <ul className="review-history">{history.map(item=><li key={item.id}><span>{item.cefr_level} · {item.is_correct?'Correct':'Needs another look'}</span><p className="text-xs muted">Reviewed {new Date(item.reviewed_at).toLocaleString()} · Next review {new Date(item.next_due_at).toLocaleString()}</p></li>)}</ul>
      {history.length>0 && history.length%20===0 && <button className="button button-quiet" onClick={async()=>{try{const page=await study.history(history.length);setHistory(old=>[...old,...page.items]);}catch(e){setError(getApiErrorMessage(e,'History unavailable.'));}}}>Load older reviews</button>}
    </section><Link href="/courses" className="button button-quiet mt-5">Back to Learn</Link></main>;
}

export function ReviewSessionPage({id}:{id:string}) {
  const [session,setSession]=useState<ReviewSession|null>(null);
  const [answer,setAnswer]=useState('');
  const [rating,setRating]=useState('normal');
  const [feedback,setFeedback]=useState<Feedback|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const lock=useRef(false);
  const pending=useRef<{id:string;answer:string;rating:string;item:string}|null>(null);
  const field=useRef<HTMLInputElement|null>(null);
  useEffect(()=>{let active=true;study.session(id).then(s=>{if(active)setSession(s);}).catch(e=>{if(active)setError(getApiErrorMessage(e,'Review unavailable.'));});return()=>{active=false;};},[id]);
  const question=session?.current_question;
  useEffect(()=>{if(question && !feedback)field.current?.focus();},[question?.item_id,feedback,question]);
  async function submit(e:FormEvent) {
    e.preventDefault();if(lock.current || !question)return;lock.current=true;setBusy(true);setError('');
    try {
      if(!pending.current || pending.current.answer!==answer || pending.current.rating!==rating || pending.current.item!==question.item_id)pending.current={id:crypto.randomUUID(),answer,rating,item:question.item_id};
      const result=await study.answer(id,question.item_id,answer,pending.current.id,rating);
      setFeedback(result);pending.current=null;setSession(await study.session(id));
    }catch(e){setError(getApiErrorMessage(e,'Your answer could not be saved. Retry to use the same request.'));}finally{lock.current=false;setBusy(false);}
  }
  async function finish() {
    if(lock.current)return;lock.current=true;setBusy(true);setError('');
    try{setSession(await study.complete(id));setFeedback(null);}catch(e){setError(getApiErrorMessage(e,'Review could not be completed.'));}finally{lock.current=false;setBusy(false);}
  }
  return <main><PageHeader title="Vocabulary review" description="Recall the French word. Your answer is checked securely before feedback appears." />
    {error && <p role="alert" className="my-4">{error}</p>}
    {error && session && <button className="button button-secondary" disabled={busy} onClick={async()=>{setBusy(true);try{setSession(await study.session(id));setError('');}catch(e){setError(getApiErrorMessage(e,'Review is still unavailable.'));}finally{setBusy(false);}}}>Reload saved review</button>}
    {!session && !error && <p role="status">Loading your review…</p>}
    {session && <><p className="text-sm muted">{session.cefr_level} · {session.answered_cards} / {session.total_cards} reviewed</p>
      {session.unavailable_cards>0 && <p className="my-3 text-sm">Some saved cards are no longer available. Their history is preserved.</p>}
      {feedback ? <section className="review-focus" aria-label="Review feedback"><h2 className="text-xl font-semibold">{feedback.is_correct?'Correct!':'Not quite.'}</h2>
        <p className="my-3">Correct answer: <strong lang="fr">{feedback.correct_answer}</strong></p><p>{feedback.explanation}</p>
        <p className="mt-3 text-sm muted">Next review: {new Date(feedback.next_due_at).toLocaleString()}</p>
        {question ? <button className="button button-primary mt-5" disabled={busy || question.item_id===feedback.item_id} onClick={()=>{setAnswer('');setRating('normal');setFeedback(null);}}>Next card</button> : <button className="button button-primary mt-5" disabled={busy} onClick={()=>void finish()}>Finish review</button>}
      </section> : session.status==='completed' ? <section className="review-focus"><h2 className="text-xl font-semibold">Review complete</h2><p className="my-3">Your answers and next review dates are saved.</p><Link href="/dashboard" className="button button-primary">Return to today’s plan</Link></section> : question ? <form className="review-focus" onSubmit={submit}>
        {question.draft_preview && <p className="mb-3 text-sm text-amber-800">Draft preview — unreviewed vocabulary</p>}
        <h2 className="text-xl font-semibold">{question.prompt}</h2><label className="mt-5 block text-sm">Your French answer<input ref={field} className={inputClass} value={answer} onChange={e=>{setAnswer(e.target.value);pending.current=null;}} required maxLength={300} disabled={busy} autoComplete="off" spellCheck={false} /></label>
        <p className="mt-2 text-xs muted">Use the word or expression, including its accents. Punctuation and letter case do not matter.</p>
        <label className="mt-4 block text-sm">How did recall feel?<select className={inputClass} value={rating} onChange={e=>{setRating(e.target.value);pending.current=null;}} disabled={busy}><option value="normal">Normal</option><option value="difficult">Difficult</option><option value="easy">Easy</option></select></label>
        <button className="button button-primary mt-5" disabled={busy || !answer.trim()}>{busy?'Saving…':'Check answer'}</button>
      </form> : <section className="review-focus"><p>All available cards have been answered.</p><button className="button button-primary mt-5" disabled={busy} onClick={()=>void finish()}>Finish review</button></section>}
    </>}<div className="mt-6 flex flex-wrap gap-4"><Link href="/review" className="text-sm text-violet-700">Review history</Link><Link href="/dashboard" className="text-sm text-violet-700">Back to Home</Link></div>
  </main>;
}
