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
  const teaching = lesson.grammar.map(topic => topic.teaching).filter(Boolean);
  return <><h2 className="text-2xl font-bold">French examples</h2>
    {unique.length ? <ul className="mt-4 space-y-4">{unique.map(e => <li key={e.french} className="rounded-xl bg-violet-50 p-4"><p lang="fr" className="text-lg font-semibold">{e.french}</p><p className="mt-1 text-slate-600">{e.english}</p></li>)}</ul> : lesson.dialogues.length ? lesson.dialogues.map(d => <div key={d.title} className="mt-4"><h3 className="font-semibold">{d.title}</h3>{d.turns.map((t,i) => <p className="mt-3" key={i}><strong lang="fr">{t.french}</strong><span className="block text-slate-600">{t.english}</span></p>)}</div>) : <ul className="mt-4 space-y-3">{lesson.vocabulary.map(w => <li key={w.lemma}><strong lang="fr">{w.lemma}</strong><span className="ml-2 text-slate-600">{w.translation}</span></li>)}</ul>}
    {teaching.map((topic, index) => <div key={index} className="mt-4 space-y-3">
      {!!topic?.forms?.length && <table className="w-full text-left">
        <caption className="text-left font-semibold">Present tense</caption>
        <thead><tr><th scope="col">Subject</th><th scope="col">Form</th></tr></thead>
        <tbody lang="fr">{topic.forms.map(([subject, form]) => <tr key={subject} className="border-b border-slate-200">
          <th scope="row" className="py-1 font-medium">{subject}</th><td>{form}</td>
        </tr>)}</tbody>
      </table>}
      {!!topic?.common_mistakes?.length && <details><summary>Common mistakes</summary>
        <ul className="list-disc pl-5">{topic.common_mistakes.map(mistake => <li key={mistake.incorrect}>
          <span lang="fr">{mistake.incorrect} → {mistake.correct}</span> · {mistake.explanation}
        </li>)}</ul>
      </details>}
      {topic?.vocabulary_examples && <details><summary>Vocabulary in context</summary>
        <ul className="list-disc pl-5">{Object.entries(topic.vocabulary_examples).map(([word, [french, english]]) =>
          <li key={word}><strong lang="fr">{word}</strong> · <span lang="fr">{french}</span> · {english}</li>)}</ul>
      </details>}
      {topic?.recap && <p><strong>Remember</strong> · {topic.recap}</p>}
    </div>)}
  </>;
}
