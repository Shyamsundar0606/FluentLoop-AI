'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiRequest } from '@/lib/api';

export function LearningAlternatives() {
  const [due, setDue] = useState<{due_count:number;cefr_level:string} | null>(null);
  useEffect(() => { let active=true;
    apiRequest<{due_count:number;cefr_level:string}>('/review/due').then(value=>{if(active)setDue(value);}).catch(()=>{});
    return ()=>{active=false;};
  },[]);
  return <section aria-label="Other ways to practice" className="mt-5 rounded-xl border border-violet-100 bg-white p-5">
    <h2 className="font-semibold">Keep practicing</h2><p className="mt-2 text-sm text-slate-600">While lesson content is unavailable, you can use these existing activities. AI and speech availability depends on the local services.</p>
    <div className="mt-4 flex flex-wrap gap-3"><Link className="button button-secondary" href="/ai-tutor">AI Tutor</Link><Link className="button button-secondary" href="/voice-practice">Speaking practice</Link>
      {!!due?.due_count && <Link className="button button-secondary" href="/review">{due.due_count} due vocabulary reviews · {due.cefr_level}</Link>}</div>
  </section>;
}
