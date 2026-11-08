'use client';
import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiRequest } from '@/lib/api';
import { LearningAlternatives } from './learning-alternatives';

interface Mistake {attempt_id:string;lesson_id:string;lesson_title:string;prompt:string;explanation:string;learning_objective_id:string|null;objective_title:string|null}
export function MistakePractice({level,lessonId}:{level:string;lessonId?:string}) {
  const [loaded,setLoaded]=useState<{key:string;items:Mistake[];error?:string}|null>(null);
  const [pending,setPending]=useState('');const [error,setError]=useState('');const busy=useRef(false);const router=useRouter();
  const key=`${level}:${lessonId??''}`;
  useEffect(()=>{let active=true;apiRequest<{items:Mistake[]}>(`/learning/mistakes?level=${level}${lessonId?`&lesson_id=${encodeURIComponent(lessonId)}`:''}`)
    .then(result=>{if(active)setLoaded({key,items:result.items});}).catch(()=>{if(active)setLoaded({key,items:[],error:'Mistakes could not be loaded. Refresh to retry.'});});return()=>{active=false;};},[key,level,lessonId]);
  async function start(item:Mistake){if(busy.current)return;busy.current=true;setPending(item.attempt_id);setError('');
    try{const saved=await apiRequest<{id:string}>('/learning/practice/sessions',{method:'POST',body:JSON.stringify({category:'mistakes',level,lesson_id:item.lesson_id,attempt_id:item.attempt_id})});router.push(`/learning/sessions/${saved.id}`);}
    catch(reason){setError(reason instanceof Error?reason.message:'Practice is unavailable.');busy.current=false;setPending('');}}
  return <section aria-label="Mistake review" className="mt-6"><Link className="text-sm font-semibold text-violet-700" href={`/practice?level=${level.toLowerCase()}`}>← Back to practice</Link><h2 className="mt-4 text-2xl font-bold">Review mistakes</h2>
    <p className="mt-3 text-slate-600">These are recorded, unresolved exercise errors at the current content version. Practice uses the existing learning engine and does not change vocabulary due dates.</p>
    {loaded?.key!==key?<p className="mt-5" role="status">Loading saved mistakes…</p>:loaded.error?<p role="alert" className="mt-5">{loaded.error}</p>:loaded.items.length?<ul className="mt-5 space-y-4">{loaded.items.map(item=><li className="rounded-xl border border-violet-100 p-5" key={item.attempt_id}><p className="text-sm text-violet-700">{item.objective_title??'Lesson review'}</p><h3 className="mt-2 font-semibold">{item.prompt}</h3><p className="mt-2 text-sm text-slate-500">{item.lesson_title}</p><p className="mt-3">{item.explanation}</p><button type="button" disabled={!!pending} onClick={()=>void start(item)} className="button button-primary mt-4">{pending===item.attempt_id?'Opening…':'Practice this mistake'}</button></li>)}</ul>:<><p className="mt-5 rounded-xl bg-violet-50 p-5">No unresolved mistakes are available here. Correct answers or unavailable source content are not shown as weaknesses.</p><LearningAlternatives/></>}
    {error&&<p role="alert" className="mt-4 text-rose-700">{error}</p>}
  </section>;
}
