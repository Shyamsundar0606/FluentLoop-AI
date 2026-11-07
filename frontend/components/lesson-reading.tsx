'use client';
import type { LearningSession } from '@/lib/learning';

export function LessonReading({ lesson, stage }: { lesson: LearningSession['lesson']; stage: number }) {
  if (stage === 0) return <>
    <h2 className="text-2xl font-bold">Introduction</h2>
    <p className="mt-4 leading-7">{lesson.description}</p>
    {!!lesson.objectives.length && <><h3 className="mt-5 font-semibold">What you will learn</h3><ul className="mt-2 list-disc space-y-2 pl-5">{lesson.objectives.map(o => <li key={o.title}>{o.title}</li>)}</ul></>}
    <p className="mt-5 text-sm text-slate-500">Read a short explanation, look at examples, then try the exercises. Your submitted answers are saved.</p>
  </>;
  if (stage === 1) {
    const sections = lesson.sections.filter(s => ['grammar', 'explanation'].includes(s.type) && !/examples/i.test(s.title));
    return <><h2 className="text-2xl font-bold">Explanation</h2>
      {sections.length ? sections.map(s => <div key={s.sequence_order} className="mt-4">{s.title.toLowerCase()!=='explanation'&&<h3 className="font-semibold">{s.title}</h3>}<p className="mt-2 whitespace-pre-line leading-7">{s.content}</p></div>) : lesson.grammar.length ? lesson.grammar.map(t => <div key={t.title} className="mt-4"><h3 className="font-semibold">{t.title}</h3><p className="mt-2">{t.summary}</p>{t.rules.map((r,i) => <p className="mt-3 leading-7" key={i}>{r.explanation}</p>)}</div>) : <p className="mt-4 leading-7">{lesson.description}</p>}
    </>;
  }
  const examples = lesson.grammar.flatMap(t => t.rules.flatMap(r => r.examples));
  const unique = [...new Map(examples.map(e => [e.french, e])).values()];
  return <><h2 className="text-2xl font-bold">French examples</h2>
    {unique.length ? <ul className="mt-4 space-y-4">{unique.map(e => <li key={e.french} className="rounded-xl bg-violet-50 p-4"><p lang="fr" className="text-lg font-semibold">{e.french}</p><p className="mt-1 text-slate-600">{e.english}</p></li>)}</ul> : lesson.dialogues.length ? lesson.dialogues.map(d => <div key={d.title} className="mt-4"><h3 className="font-semibold">{d.title}</h3>{d.turns.map((t,i) => <p className="mt-3" key={i}><strong lang="fr">{t.french}</strong><span className="block text-slate-600">{t.english}</span></p>)}</div>) : <ul className="mt-4 space-y-3">{lesson.vocabulary.map(w => <li key={w.lemma}><strong lang="fr">{w.lemma}</strong><span className="ml-2 text-slate-600">{w.translation}</span></li>)}</ul>}
  </>;
}
