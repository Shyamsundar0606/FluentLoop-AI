import {expect,test} from '@playwright/test';

const api=process.env.PLAYWRIGHT_API_BASE_URL??'http://127.0.0.1:8001/api/v1';
const headers={'access-control-allow-origin':new URL(process.env.PLAYWRIGHT_BASE_URL??'http://127.0.0.1:3001').origin,'access-control-allow-credentials':'true','access-control-allow-methods':'GET,POST,OPTIONS','access-control-allow-headers':'content-type,x-csrf-token'};
const lessonId='b2222222-2222-4222-8222-222222222222';
const user={id:'a1111111-1111-4111-8111-111111111111',email:'path@example.test',role:'learner',email_verified:true,
  display_name:'Path learner',preferred_name:null,native_language:'English',onboarding_completed:true,
  preferences:{current_level:'a1',explanation_language:'English',target_language:'French',daily_study_minutes:15,theme:'system',learning_focus:'balanced',audio_playback_speed:1}};

test('A0 to C2 navigation separates available activities from unfinished curriculum',async({page})=>{
  const stages=['A0','A1','A2','B1','B2','C1','C2'].map((code,index)=>({code,official_cefr:code!=='A0',introduction:code==='A0'?'Introductory preparation, not an official CEFR level.':'Practice target; calibration pending.',available_lessons:index?1:0,completed_activities:0,
    modules:[{id:`${code.toLowerCase()}-01`,title:`${code} first module`,objective:`Practise ${code} communication.`,outcomes:['Explain an idea.'],prerequisites:[],available_lessons:index?1:0,completed_activities:0,remaining_activities:index?1:0,revision:'Review saved mistakes.',assessment:'Use evidence across skills.',coverage:'partial',lessons:index?[{id:lessonId,title:`${code} available lesson`,status:'not_started',href:`/learn/${lessonId}`,draft_preview:true,kind:'lesson'}]:[]}]}));
  await page.route(`${api}/**`,async route=>{const path=new URL(route.request().url()).pathname;await route.fulfill({headers,json:path.endsWith('/auth/me')?{user}:path.endsWith('/learning/path')?{stages,saved_level:'A1',notice:'Completing activities does not certify a CEFR level.',next_activity:{stage:'A1',href:`/learn/${lessonId}`,reason:'practice_or_revision'}}:{}});});
  await page.goto('/learning-path');await expect(page.getByRole('heading',{name:'Your French learning path'})).toBeVisible();
  const navigation=page.getByRole('navigation',{name:'Learning stages'});await expect(navigation.getByRole('button')).toHaveCount(7);
  await expect(page.getByText('Introductory preparation, not an official CEFR level.')).toBeVisible();
  await expect(page.getByText('Lessons for this module are being prepared.')).toBeVisible();
  for(const level of ['A1','A2','B1','B2','C1','C2']){await navigation.getByRole('button',{name:level,exact:true}).click();await expect(page.getByRole('region',{name:`${level} learning path`})).toBeVisible();await expect(page.getByRole('link',{name:`${level} available lesson`,exact:true})).toBeVisible();}
  await expect(page.getByRole('link',{name:'Skills practice assessments'})).toHaveAttribute('href','/assessments?level=c2');
  await expect(page.getByText(/Your saved level is A1/)).toBeVisible();
  await expect(page.getByRole('link',{name:'Suggested next practice · A1'})).toHaveAttribute('href',`/learn/${lessonId}`);
});

test('a writing lesson opens the writing workspace instead of an empty quiz',async({page})=>{
  await page.route(`${api}/**`,async route=>{const path=new URL(route.request().url()).pathname;await route.fulfill({headers,json:path.endsWith('/auth/me')?{user}:path.endsWith(`/lessons/${lessonId}`)?{
    id:lessonId,unit_id:lessonId,slug:'draft-writing',title:'A clear French message',description:'Write a message for an invented situation.',level:'C2',estimated_minutes:15,sequence_order:1,content_status:'draft',draft_preview:true,sections:[],dialogues:[],objectives:[{code:'write-message',title:'Write a message',description:'State the purpose and a suitable closing.',skill_category:'writing'}]}:{}});});
  await page.goto(`/learn/${lessonId}`);await expect(page.getByRole('link',{name:'Open writing task'})).toHaveAttribute('href',`/assessments/writing/${lessonId}`);
  await expect(page.getByRole('button',{name:'Start or continue lesson'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Ask AI Tutor',exact:true})).toBeDisabled();
  await expect(page.getByRole('link',{name:'update your saved French level'})).toHaveAttribute('href','/settings');
});
