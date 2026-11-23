"use client";
import Link from 'next/link';
import {useEffect,useRef,useState} from 'react';
import {useRouter} from 'next/navigation';
import {ProtectedPage} from '@/components/auth-provider';
import {apiRequest} from '@/lib/api';
import {assessments,type AssessmentDefinition} from '@/lib/assessments';

type Plan={id:string;title:string;stage:string;kind:string;available:boolean;objective_checks:AssessmentDefinition[];writing_tasks:AssessmentDefinition[];speaking_lesson:{href:string;title:string}|null;rubrics:{writing:string[];speaking:string[]};qualitative_rating_labels:string[];review:string;persistence:string};
type Response={plans:Plan[];notice:string;saved_level:string};
export default function Page(){return <ProtectedPage><Checkpoints/></ProtectedPage>;}
function Checkpoints(){
 const router=useRouter();const[stage,setStage]=useState('A0');const[data,setData]=useState<Response|null>(null);const[error,setError]=useState('');const[busy,setBusy]=useState(false);const lock=useRef(false);
 useEffect(()=>{let active=true;apiRequest<Response>(`/learning/checkpoints?stage=${stage}`).then(body=>{if(active)setData(body);}).catch(()=>{if(active)setError('Check plans could not load. Refresh to retry.');});return()=>{active=false;};},[stage]);
 async function start(item:AssessmentDefinition){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{const saved=await assessments.start(item);router.push(`/learning/sessions/${saved.id}`);}catch{setError('This check could not start. Your saved results remain available; retry when the service is ready.');}finally{lock.current=false;setBusy(false);}}
 return <main className="mx-auto max-w-5xl space-y-5 px-5 py-8"><Link className="text-violet-700 underline" href="/learning-path">Learning path</Link><h1 className="text-3xl font-bold">Module and level check plans</h1>
  <p>Review understanding, then transfer it to writing and speaking. A completed quiz is not a CEFR award.</p>
  <nav aria-label="Check stages" className="flex flex-wrap gap-2">{['A0','A1','A2','B1','B2','C1','C2'].map(code=><button type="button" key={code} aria-pressed={code===stage} onClick={()=>{if(code!==stage){setData(null);setError('');setStage(code);}}} className="rounded-lg border px-4 py-3">{code}</button>)}</nav>
  {error&&<p role="alert">{error}</p>}{!data&&!error&&<p role="status">Loading check plans…</p>}
  {data&&<><p>{data.notice} Your saved level remains {data.saved_level}.</p>{data.plans.map(plan=><article className="space-y-3 rounded-xl border bg-white p-5 text-slate-900" key={plan.id}>
   <h2 className="text-xl font-semibold">{plan.title}</h2><p>{plan.kind==='level_end'?'Sampled level-end review':'Module practice review'}</p>
   {!plan.available&&<p>Content for this check is not available to this account yet.</p>}
   <div className="flex flex-wrap gap-3">{plan.objective_checks.map(item=><button type="button" disabled={busy} key={item.id} onClick={()=>start(item)} className="rounded-lg border px-3 py-2 disabled:opacity-50">{item.skill} · {item.title} · {item.question_count} questions</button>)}</div>
   {plan.writing_tasks.map(item=><p key={item.id}><Link className="text-violet-700 underline" href={`/assessments/writing/${item.lesson_id}`}>Writing: {item.title}</Link></p>)}
   {plan.speaking_lesson&&<p><Link className="text-violet-700 underline" href={plan.speaking_lesson.href}>Open lesson for contextual speaking</Link>. Tutor/voice practice requires the matching level in Settings.</p>}
   <details><summary>Writing and speaking review criteria</summary>{(['writing','speaking'] as const).map(skill=><section key={skill}><h3 className="mt-3 font-semibold">{skill}</h3><ul className="list-disc pl-5">{plan.rubrics[skill].map(text=><li key={text}>{text}</li>)}</ul></section>)}<p className="mt-3">Qualitative labels: {plan.qualitative_rating_labels.join(' · ')}. A saved submission is not a human rating; these skills remain unassessed until reviewed.</p></details>
   <p>{plan.review}</p><p className="text-sm">{plan.persistence}</p>
  </article>)}<Link className="text-violet-700 underline" href="/assessments">Saved assessments, writing and revision recommendations</Link></>}
 </main>;
}
