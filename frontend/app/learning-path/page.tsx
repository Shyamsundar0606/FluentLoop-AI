"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ProtectedPage } from "@/components/auth-provider";
import { apiRequest } from "@/lib/api";

type Lesson = {id:string;title:string;status:string;href:string;draft_preview:boolean;kind:string};
type Module = {id:string;title:string;objective:string;outcomes:string[];prerequisites:string[];lessons:Lesson[];available_lessons:number;completed_activities:number;remaining_activities:number;revision:string;assessment:string;coverage:string;formative_evidence?:{state:string;guidance:string;calibration:string}};
type Stage = {code:string;official_cefr:boolean;introduction:string;modules:Module[];available_lessons:number;completed_activities:number};
type Path = {stages:Stage[];saved_level:string;notice:string;next_activity?:{stage:string;href:string;reason:string}|null};

export default function Page(){return <ProtectedPage><LearningPath /></ProtectedPage>;}

function LearningPath(){
  const [path,setPath]=useState<Path|null>(null);const [selected,setSelected]=useState('A0');const [error,setError]=useState('');
  useEffect(()=>{let active=true;apiRequest<Path>('/learning/path').then(value=>{if(active)setPath(value);}).catch(()=>{if(active)setError('Your learning path could not load. Refresh to retry.');});return()=>{active=false;};},[]);
  const stage=path?.stages.find(value=>value.code===selected);
  const moduleNames=new Map(path?.stages.flatMap(value=>value.modules.map(module=>[module.id,module.title] as const))??[]);
  return <main className="mx-auto max-w-5xl space-y-6 px-5 py-8">
    <div className="flex flex-wrap gap-4"><Link href="/courses" className="text-violet-700 underline">Course library</Link><Link href="/checkpoints" className="text-violet-700 underline">Module and level check plans</Link></div>
    <header><h1 className="text-3xl font-bold">Your French learning path</h1><p className="mt-3">Start with no French and work progressively towards advanced communication.</p></header>
    {error&&<p role="alert">{error}</p>}{!path&&!error&&<p role="status">Loading your learning path…</p>}
    {path&&<><p className="text-sm text-slate-600">{path.notice} Your saved level is {path.saved_level}; browsing this path does not change it.</p>
      {path.next_activity&&<p><Link className="font-semibold text-violet-700 underline" href={path.next_activity.href}>Suggested next practice · {path.next_activity.stage}</Link><span className="ml-2 text-sm">A practice recommendation, not a level promotion.</span></p>}
      <nav aria-label="Learning stages" className="flex flex-wrap gap-2">{path.stages.map(value=><button type="button" key={value.code} aria-pressed={selected===value.code} onClick={()=>setSelected(value.code)} className={`rounded-xl border px-4 py-3 font-semibold ${selected===value.code?'bg-violet-700 text-white':'bg-white text-violet-700'}`}>{value.code}</button>)}</nav>
      {stage&&<section aria-label={`${stage.code} learning path`} className="space-y-5">
        <h2 className="text-2xl font-bold">{stage.code}{!stage.official_cefr?' · Absolute beginner preparation':''}</h2><p>{stage.introduction}</p>
        <p>{stage.available_lessons} available lessons · {stage.completed_activities} completed activities. Further curriculum coverage remains in development.</p>
        {stage.code!=='A0'&&<div className="flex flex-wrap gap-4 text-violet-700 underline"><Link href={`/courses?level=${stage.code.toLowerCase()}`}>All available lessons</Link><Link href={`/grammar?level=${stage.code.toLowerCase()}`}>Grammar</Link><Link href={`/practice?level=${stage.code.toLowerCase()}`}>Listening and revision</Link><Link href={`/assessments?level=${stage.code.toLowerCase()}`}>Skills practice assessments</Link></div>}
        {stage.modules.map(module=><article id={module.id} key={module.id} className="rounded-2xl border border-violet-100 bg-white p-6 text-slate-900">
          <h3 className="text-xl font-semibold">{module.title}</h3><p className="my-3">{module.objective}</p>
          <p className="text-sm text-slate-600">Recommended preparation: {module.prerequisites.length?module.prerequisites.map(id=>moduleNames.get(id)??id).join(', '):'None—start here.'}</p>
          <p className="my-3 text-sm">{module.completed_activities} completed · {module.remaining_activities} remaining available activities</p>
          {!module.lessons.length?<p>Lessons for this module are being prepared.</p>:<ul className="space-y-3">{module.lessons.map(lesson=><li key={lesson.id}><Link className="font-semibold text-violet-700 underline" href={lesson.href}>{lesson.title}</Link><span className="ml-2 text-sm">{lesson.status.replaceAll('_',' ')}{lesson.draft_preview?' · Personal draft':''}</span></li>)}</ul>}
          <details className="mt-4"><summary>Revision and assessment goals</summary><p className="mt-2">{module.revision}</p><p>{module.assessment}</p>{module.formative_evidence&&<><p className="mt-2">Practice evidence: {module.formative_evidence.state.replaceAll('_',' ')}.</p><p>{module.formative_evidence.guidance}</p></>}<p className="mt-2 text-sm">Module and level-end assessments are not yet independently calibrated. Saved writing still needs qualitative review.</p></details>
        </article>)}
        <div className="flex flex-wrap gap-4"><Link className="text-violet-700 underline" href="/ai-tutor">Ask your AI Tutor</Link><Link className="text-violet-700 underline" href="/voice-practice">Practise speaking</Link><Link className="text-violet-700 underline" href="/review">Review saved vocabulary</Link></div>
      </section>}
    </>}
  </main>;
}
