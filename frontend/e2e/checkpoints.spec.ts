import {expect,test} from '@playwright/test';
const api=process.env.PLAYWRIGHT_API_BASE_URL??'http://127.0.0.1:8001/api/v1';
const id='c2222222-2222-4222-8222-222222222222';
const headers={'access-control-allow-origin':new URL(process.env.PLAYWRIGHT_BASE_URL??'http://127.0.0.1:3001').origin,'access-control-allow-credentials':'true','access-control-allow-methods':'GET,POST,OPTIONS','access-control-allow-headers':'content-type,x-csrf-token'};
const user={id:'a1111111-1111-4111-8111-111111111111',email:'checks@example.test',role:'learner',email_verified:true,display_name:'Checks',onboarding_completed:true,preferences:{current_level:'a1',explanation_language:'English',target_language:'French',daily_study_minutes:15,theme:'system',learning_focus:'balanced',audio_playback_speed:1}};

test('module plans expose separate scored practice and unassessed productive rubrics',async({page})=>{
 await page.route(`${api}/**`,async route=>{
  const path=new URL(route.request().url()).pathname;
  await route.fulfill({headers,json:path.endsWith('/auth/me')?{user}:path.endsWith('/learning/checkpoints')?{saved_level:'A1',notice:'Formative checks; not a calibrated exam.',plans:[{id:'a0-01',title:'Sounds and letters',kind:'module',stage:'A0',available:true,objective_checks:[],writing_tasks:[{id:'writing:'+id,lesson_id:id,title:'A short model'}],speaking_lesson:{href:'/learn/'+id,title:'Sounds'},rubrics:{writing:['Keep accents.'],speaking:['Ask for a slow repeat.']},qualitative_rating_labels:['Needs support','Developing for this task','Consistent for this task'],review:'Retrieve on a later day.',persistence:'Saved in component histories.'}]}:{}});
 });
 await page.goto('/checkpoints');await expect(page.getByRole('heading',{name:'Module and level check plans'})).toBeVisible();
 await expect(page.getByRole('link',{name:'Writing: A short model'})).toHaveAttribute('href','/assessments/writing/'+id);
 await page.getByText('Writing and speaking review criteria',{exact:true}).click();
 await expect(page.getByText('Keep accents.',{exact:true})).toBeVisible();await expect(page.getByText(/these skills remain unassessed until reviewed/)).toBeVisible();
 await expect(page.getByText(/Your saved level remains A1/)).toBeVisible();
 await expect(page.getByRole('navigation',{name:'Check stages'}).getByRole('button')).toHaveCount(7);
});
