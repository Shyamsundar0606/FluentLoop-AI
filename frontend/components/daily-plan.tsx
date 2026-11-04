"use client";
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from './auth-provider';
import { study, type DailyPlan } from '@/lib/study';
import { getApiErrorMessage } from '@/lib/api';

export function DailyPlanPanel() {
  const {user} = useAuth();
  const router = useRouter();
  const level = user?.preferences.current_level;
  const [state,setState] = useState<{level?:string;plan:DailyPlan|null;error?:string}|null>(null);
  const [busy,setBusy] = useState(false);
  const request = useRef<string|null>(null);
  const lock = useRef(false);
  useEffect(() => {
    let active=true;
    study.today().then(plan => {if(active)setState({level,plan});})
      .catch(e => {if(active)setState({level,plan:null,error:getApiErrorMessage(e,'Your daily plan is unavailable. Try again.')});});
    return () => {active=false;};
  },[level,user?.id]);
  const current = state?.level === level ? state : null;
  const plan = current?.plan;
  const next = plan?.activities.find(activity => activity.status !== 'completed');
  async function act(regenerate=false) {
    if(lock.current)return;
    lock.current=true;setBusy(true);
    try {
      if(!plan || regenerate) {
        request.current ??= crypto.randomUUID();
        const saved=await study.generate(request.current,regenerate);
        request.current=null;setState({level,plan:saved});
      } else if(next) {
        const started=await study.start(next.id);
        if(started.url)router.push(started.url);
      }
    } catch(e) {
      setState({level,plan:plan??null,error:getApiErrorMessage(e,'Your daily plan is unavailable. Try again.')});
    } finally {lock.current=false;setBusy(false);}
  }
  return <section className="panel daily-plan" aria-label="Today's French Plan">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="panel-title">Today&apos;s French Plan</h2>
      <p className="mt-1 text-sm muted">{plan?.target_minutes ?? user?.preferences.daily_study_minutes ?? 15}-minute daily goal · {plan?.cefr_level ?? level?.toUpperCase()}</p></div>
      <Link href="/review" className="text-sm text-violet-700">Review vocabulary</Link></div>
    {!current && <p role="status" className="mt-4">Loading your plan…</p>}
    {current?.error && <p role="alert" className="mt-3">{current.error} Your other practice activities remain available.</p>}
    {plan && <>
      <ol className="daily-activities">{plan.activities.map(activity => <li key={activity.id}>
        <div><span className="font-semibold">{activity.title}</span><p className="text-xs muted">About {activity.estimated_minutes} min · {activity.status.replace('_',' ')}{activity.draft_preview ? ' · Draft preview — unreviewed' : ''}</p>
        <details><summary className="text-xs">Why this activity?</summary><p className="text-sm muted">{activity.reason}</p></details></div>
        <span aria-label={activity.status==='completed'?'Completed':'Pending'}>{activity.status==='completed'?'✓':'·'}</span>
      </li>)}</ol>
      <p className="text-xs muted">{plan.planned_minutes} minutes planned, estimated. Planned time is not recorded study time.{plan.due_review_count>0 ? ` ${plan.due_review_count} cards due.` : ''}</p>
      {plan.unavailable_activity_count>0 && <p className="mt-2 text-sm">Some saved activities are no longer authorized. Their history is preserved.</p>}
      {plan.status==='completed' && <p role="status" className="mt-4">Today&apos;s activities are complete.</p>}
    </>}
    {current && (!plan || next) && <button className="button button-primary mt-4" disabled={busy} onClick={() => void act()}>{busy?'Please wait…':!plan?'Create today’s plan':next?.status==='in_progress'?'Continue next activity':'Start next activity'}</button>}
    {plan?.status==='ready' && <details className="mt-3 text-xs"><summary>Plan options</summary><p className="my-2 muted">Refresh an unstarted plan using current preferences and available activities. A started plan stays saved.</p><button className="button button-quiet" disabled={busy} onClick={() => void act(true)}>Regenerate unstarted plan</button></details>}
  </section>;
}
