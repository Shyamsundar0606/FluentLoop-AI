'use client';
import { useEffect, useState, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiRequest } from '@/lib/api';
import { LessonActions } from '@/components/lesson-actions';

interface Topic {
  id:string;title:string;summary:string;lesson_ids:string[];publication_status:string;explanation_language:string;available_exercises:number;
  rules:{explanation:string;exceptions?:string|null;examples:{french:string;english:string}[]}[];
  teaching:{version?:string;when_to_use?:string;common_mistakes?:{incorrect:string;correct:string;explanation:string}[];recap?:string;source_license?:string;attribution?:string;situation?:string;forms?:[string,string][];preferred_lesson_slug?:string;vocabulary_examples?:Record<string,[string,string]>;noun_forms?:Record<string,[string,string]>};
  objectives:{title:string}[];vocabulary:{lemma:string;translation:string;part_of_speech?:string;grammatical_gender?:string;ipa?:string}[];
}
export function GrammarDetails({level,onEnhancedTopics}:{level:string;onEnhancedTopics?:(ids:string[])=>void}) {
  const router=useRouter();const query=useSearchParams();const busy=useRef(false);
  const [loaded,setLoaded]=useState<{level:string;items:Topic[];error?:string}|null>(null);
  const [pending,setPending]=useState(false);const [error,setError]=useState('');
  useEffect(()=>{let active=true;apiRequest<{items:Topic[]}>(`/learning/grammar?level=${level}`).then(result=>{if(active){setLoaded({level,items:result.items});onEnhancedTopics?.(result.items.map(t=>t.id));}}).catch(()=>{if(active){setLoaded({level,items:[],error:'Detailed grammar practice is temporarily unavailable.'});onEnhancedTopics?.([]);}});return()=>{active=false;};},[level,onEnhancedTopics]);
  const items=loaded?.level===level?loaded.items:[];
  const topic=items.find(t=>t.id===query.get('topic'))??items.find(t=>t.teaching.preferred_lesson_slug==='m08-etre-interactive-lesson')??items.find(t=>t.teaching.when_to_use)??items[0];
  async function practice(){if(!topic?.available_exercises||busy.current)return;busy.current=true;setPending(true);setError('');
    try{const saved=await apiRequest<{id:string}>('/learning/practice/sessions',{method:'POST',body:JSON.stringify({category:'grammar',grammar_topic_id:topic.id,level})});router.push(`/learning/sessions/${saved.id}`);}
    catch(reason){setError(reason instanceof Error?reason.message:'Practice unavailable.');setPending(false);busy.current=false;}}
  if(loaded?.level!==level)return <p role="status">Loading grammar practice…</p>;
  if(loaded.error)return <p role="status">{loaded.error}</p>;
  if(!topic)return null;
  const mistakes=topic.teaching.common_mistakes??[];
  const notes=topic.rules.map(r=>r.exceptions).filter(Boolean);
  return <section aria-label="Grammar practice" className="my-6">
    <label className="block font-medium">Grammar topic<select className="mt-2 block w-full rounded-xl border border-slate-300 bg-white p-3" value={topic.id} onChange={event=>{const next=new URLSearchParams(query.toString());next.set('level',level.toLowerCase());next.set('topic',event.target.value);router.replace(`/grammar?${next}`,{scroll:false});}}>{items.map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></label>
    <article className="mt-5 rounded-2xl border border-violet-100 bg-white p-5 sm:p-7">
      <p className="text-sm text-violet-700">{level} · {topic.teaching.situation ?? `${topic.explanation_language} explanations`}</p><h2 className="mt-2 text-2xl font-semibold">{topic.title}</h2>
      {topic.publication_status!=='published'&&<p className="mt-3 text-sm text-amber-800">Draft Preview · independent review pending</p>}
      <h3 className="mt-5 font-semibold">Explanation</h3>{topic.rules.map((rule,i)=><p className="mt-3 leading-7" key={i}>{rule.explanation}</p>)}
      {!!topic.teaching.forms?.length && <table className="mt-4 w-full text-left text-sm">
        <caption className="mb-2 text-left font-semibold">Present tense</caption>
        <thead><tr className="border-b border-violet-100"><th scope="col" className="p-2">Subject</th><th scope="col" className="p-2">Form</th></tr></thead>
        <tbody lang="fr">{topic.teaching.forms.map(([subject, form]) => <tr key={subject} className="border-b border-violet-100"><th scope="row" className="p-2 font-medium">{subject}</th><td className="p-2">{form}</td></tr>)}</tbody>
      </table>}
      <h3 className="mt-5 font-semibold">When to use it</h3><p className="mt-2 leading-7">{topic.teaching.when_to_use??topic.summary}</p>
      <h3 className="mt-5 font-semibold">French examples</h3><ul className="mt-3 space-y-3">{topic.rules.flatMap(r=>r.examples).map((e,i)=><li className="rounded-xl bg-violet-50 p-4" key={`${e.french}-${i}`}><strong lang="fr">{e.french}</strong><span className="mt-1 block text-slate-600">{e.english}</span></li>)}</ul>
      <h3 className="mt-5 font-semibold">Common mistakes</h3>{mistakes.length?mistakes.map(m=><div className="mt-3" key={m.incorrect}><p lang="fr">{m.incorrect} → <strong>{m.correct}</strong></p><p className="mt-1 text-sm text-slate-600">{m.explanation}</p></div>):notes.length?notes.map((note,i)=><p className="mt-2" key={i}>{note}</p>):<p className="mt-2 text-sm text-slate-500">Separate authored mistake notes are not available for this topic yet.</p>}
      <h3 className="mt-5 font-semibold">Remember</h3><p className="mt-2">{topic.teaching.recap??topic.summary}</p>
      <button type="button" className="button button-primary mt-6" disabled={!topic.available_exercises||pending} onClick={()=>void practice()}>{pending?'Opening…':'Practice this grammar'}</button>
      {!topic.available_exercises&&<p className="mt-2 text-sm text-slate-500">No explicitly linked authorized grammar exercises are available for this topic yet.</p>}
      {topic.lesson_ids[0]&&<LessonActions lessonId={topic.lesson_ids[0]}/>}
      <details className="mt-5 text-sm">
        <summary>Related vocabulary and source notes</summary>
        <ul className="mt-3 space-y-3">{topic.vocabulary.map(word => {
          const example = topic.teaching.vocabulary_examples?.[word.lemma];
          const nounForms = topic.teaching.noun_forms?.[word.lemma];
          const notes = [word.part_of_speech, word.grammatical_gender, word.ipa].filter(Boolean).join(', ');
          return <li key={word.lemma}>
            <strong lang="fr">{word.lemma}</strong> — {word.translation}{notes && <span className="text-slate-600"> ({notes})</span>}
            {nounForms && <p lang="fr">{nounForms.join(' / ')}</p>}
            {example && <p className="text-slate-600"><span lang="fr">{example[0]}</span> — {example[1]}</p>}
          </li>;
        })}</ul>
        <p className="mt-3">{topic.teaching.version && `Version ${topic.teaching.version}. `}{topic.teaching.source_license ?? 'Existing authorized curriculum; publication follows the independent review process.'}</p>
        {topic.teaching.attribution && <p className="mt-2">{topic.teaching.attribution}</p>}
        <p className="mt-2">Objectives: {[...new Set(topic.objectives.map(o=>o.title))].join('; ')}</p>
      </details>
    </article>{error&&<p role="alert" className="mt-4 text-rose-700">{error}</p>}
  </section>;
}
