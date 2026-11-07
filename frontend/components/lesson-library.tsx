'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiRequest } from '@/lib/api';
import { useLearningContext } from '@/lib/use-learning-context';

interface Lesson { id: string; title: string; description: string; unit_id: string; unit_title:string; estimated_minutes: number; draft_preview: boolean; objectives: {id: string;title:string}[]; status: string; answered:number; total:number; session_id:string|null }
export function LessonLibrary({level}:{level:string}) {
  const {lessonId}=useLearningContext();
  const [loaded,setLoaded]=useState<{level:string;items:Lesson[];error?:string}|null>(null);
  useEffect(()=>{let active=true;apiRequest<{items:Lesson[]}>(`/learning/library?level=${level}`).then(r=>{if(active)setLoaded({level,items:r.items});}).catch(()=>{if(active)setLoaded({level,items:[],error:'Lesson progress is temporarily unavailable.'});});return()=>{active=false;};},[level]);
  if(loaded?.level!==level)return <p role="status">Loading lesson progress…</p>;
  if(loaded.error)return <p role="status">{loaded.error}</p>;
  if(!loaded.items.length)return null;
  return <section aria-label="Available lessons" className="my-6 space-y-4"><h2 className="text-xl font-semibold">Your {level} lessons</h2>
    {loaded.items.map((lesson,index)=><article key={lesson.id} id={`lesson-${lesson.id}`} aria-current={lessonId===lesson.id?'location':undefined} className={`rounded-2xl border bg-white p-5 ${lessonId===lesson.id?'border-violet-500 ring-1 ring-violet-100':'border-violet-100'}`}>
      {(index===0 || loaded.items[index-1].unit_id!==lesson.unit_id)&&<p className="mb-3 text-sm text-violet-700">{lesson.unit_title}</p>}
      <p className="text-sm text-slate-500">{lesson.estimated_minutes} minutes · {lesson.status.replaceAll('_',' ')}</p>
      <h3 className="mt-2 text-lg font-semibold">{lesson.title}</h3><p className="mt-2 text-slate-600">{lesson.description}</p>
      <ul className="my-3 list-disc pl-5 text-sm">{lesson.objectives.map(o=><li key={o.id}>{o.title}</li>)}</ul>
      {lesson.draft_preview&&<p className="mb-3 text-sm text-amber-800">Draft Preview · independent review pending</p>}
      <progress className="block w-full accent-violet-600" aria-label={`${lesson.title} progress`} max={lesson.total||1} value={lesson.status==='completed'?(lesson.total||1):lesson.answered}/>
      <Link className="mt-4 inline-block rounded-xl bg-violet-700 px-5 py-3 font-semibold text-white" href={lesson.session_id?`/learning/sessions/${lesson.session_id}`:`/learn/${lesson.id}`}>{lesson.session_id?'Continue':lesson.status==='completed'?'Practice again':'Start'}</Link>
    </article>)}
  </section>;
}
