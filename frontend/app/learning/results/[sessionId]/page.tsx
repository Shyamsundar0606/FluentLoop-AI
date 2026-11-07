'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ProtectedPage } from '@/components/auth-provider';
import { apiRequest } from '@/lib/api';
import { getLearningResults, getLearningSession, grammarPracticeTopic, learningReturnUrl, submittedAnswerText, type CompletionResult, type LearningSession } from '@/lib/learning';

interface ReviewItem {session_exercise_id:string;objective_title:string|null;practice_available:boolean}
export default function LearningResultsPage(){return <ProtectedPage><ResultsContent/></ProtectedPage>;}
function ResultsContent(){
  const {sessionId}=useParams<{sessionId:string}>();
  const [results,setResults]=useState<CompletionResult|null>(null);const [session,setSession]=useState<LearningSession|null>(null);
  const [review,setReview]=useState<ReviewItem[]|null>(null);const [error,setError]=useState('');
  useEffect(()=>{let active=true;
    Promise.all([getLearningResults(sessionId),getLearningSession(sessionId)]).then(([result,saved])=>{
      if(active){setResults(result);setSession(saved);}
      return apiRequest<{items:ReviewItem[]}>(`/learning/sessions/${encodeURIComponent(sessionId)}/review`).then(value=>{if(active)setReview(value.items??[]);}).catch(()=>{});
    }).catch(reason=>{if(active)setError(reason instanceof Error?reason.message:'Saved results could not be loaded.');});
    return()=>{active=false;};
  },[sessionId]);
  const practice=results?.activity_key?.startsWith('practice:');
  const topics=review?[...new Set(review.filter(item=>item.practice_available).map(item=>item.objective_title??'Lesson review'))]:[];
  const lessonUrl=results?`/courses?level=${results.cefr_level.toLowerCase()}&lesson=${encodeURIComponent(results.lesson_id)}`:'/courses';
  return <main className="mx-auto max-w-3xl px-5 py-8">
    <Link href="/dashboard" className="text-sm font-semibold text-violet-700">← Dashboard</Link>
    {!results&&!error&&<p role="status" className="mt-8">Loading saved results…</p>}{error&&<p role="alert" className="mt-6 text-rose-700">{error}</p>}
    {results&&session&&<>
      <section className="mt-6 rounded-2xl border border-violet-100 bg-white p-6 sm:p-8" aria-label="Saved results">
        <p className="text-sm font-semibold text-violet-700">{results.cefr_level} {practice?'practice complete':'lesson complete'}</p>
        <h1 className="mt-3 text-3xl font-bold">{results.lesson_title}</h1><p className="mt-5 text-4xl font-bold text-violet-700">{results.percentage}%</p>
        <p className="mt-3">{results.correct_answers} correct · {results.incorrect_answers} incorrect · {results.total_questions} questions</p>
        <p className="mt-3 text-sm text-slate-500">{results.total_questions} questions answered. {practice?'Focused practice · full lesson progress unchanged':`Completion ${results.completion_count}`} · Completed {new Date(results.completed_at).toLocaleString()}</p>
        <h2 className="mt-6 font-semibold">Topics needing review</h2>
        {review===null?<p className="mt-2 text-sm text-slate-500">Current mistake details are loading or temporarily unavailable. Saved grading below remains available.</p>:topics.length?<ul className="mt-2 list-disc pl-5">{topics.map(topic=><li key={topic}>{topic}</li>)}</ul>:<p className="mt-2 text-sm text-slate-600">No current unresolved mistakes from this attempt. Earlier errors may have been revisited, or their source version changed.</p>}
        <div className="mt-6 flex flex-wrap gap-3"><Link className="button button-primary" href={grammarPracticeTopic(session.activity_key) ? learningReturnUrl(session) : lessonUrl}>{grammarPracticeTopic(session.activity_key) ? 'Back to grammar topic' : 'Continue learning'}</Link>
          {review?.some(item=>item.practice_available)?<Link className="button button-secondary" href={`/practice?level=${results.cefr_level.toLowerCase()}&category=mistakes&lesson=${results.lesson_id}`}>Review mistakes</Link>:null}</div>
      </section>
      <p className="mt-4 text-sm text-slate-500">This exercise score records this activity. It is not a formal certification of French proficiency or a pronunciation score.</p>
      <section aria-label="Saved answers" className="mt-6 space-y-4"><h2 className="text-xl font-semibold">Your saved answers</h2>
        {session.exercises.filter(e=>e.answered).map(exercise=><article className="rounded-xl border border-slate-200 p-5" key={exercise.id}>
          <h3 className="font-semibold">{exercise.exercise_order}. {exercise.prompt}</h3><p className="mt-3">Your answer: <strong>{submittedAnswerText(exercise)}</strong></p>
          <p className={`mt-2 font-semibold ${exercise.feedback?.is_correct?'text-emerald-700':'text-rose-700'}`}>{exercise.feedback?.is_correct?'Correct':'Not quite'}</p>
          <p className="mt-2">Correct answer: <strong>{exercise.feedback?.correct_answer}</strong></p><p className="mt-2 text-sm text-slate-600">{exercise.feedback?.explanation}</p>
        </article>)}
      </section>
      <div className="mt-6 flex flex-wrap gap-4 text-sm font-semibold text-violet-700"><Link href={`/learn/${results.lesson_id}`}>Retake lesson</Link><Link href={lessonUrl}>Back to courses</Link><Link href="/progress">View progress</Link></div>
    </>}
  </main>;
}
