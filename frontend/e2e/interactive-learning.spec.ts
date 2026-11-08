import { enterExercises } from './learning-navigation';
import {expect,test,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';

type Fixture={admin:string;learner:string;lesson_id:string;password:string};
let fixture:Fixture;
const csrfCookie=process.env.PLAYWRIGHT_CSRF_COOKIE_NAME ?? 'fluentloop_csrf';
test.beforeEach(()=>{
  test.skip(process.env.M08_E2E_REAL_API!=='1','Requires isolated M08 PostgreSQL API and prepared synthetic accounts.');
  fixture=JSON.parse(readFileSync('../.speech-data/m08-browser-fixture.json','utf8')) as Fixture;
});
async function login(page:Page,email:string){
  await page.goto('/login');await page.getByLabel('Email').fill(email);
  await page.locator('input[autocomplete="current-password"]').fill(fixture.password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}
async function next(page:Page){await expect(page.getByRole('heading',{name:'Correct!',exact:true})).toBeVisible();await page.getByRole('button',{name:'Continue',exact:true}).click();}

test('real PostgreSQL six formats, Piper audio, saved feedback, resume and completion',async({page})=>{
  test.setTimeout(180000);await login(page,fixture.admin);
  // A previous interrupted run may have a resumable synthetic test session.
  // Abandon it through the normal owned API; retain its history.
  const base=process.env.PLAYWRIGHT_API_BASE_URL!;
  const csrf=(await page.context().cookies()).find(c=>c.name===csrfCookie)!.value;
  const active=await (await page.request.get(`${base}/learning/sessions?status=in_progress`)).json();
  for(const item of active.items)if(item.lesson_id===fixture.lesson_id && item.activity_key==='lesson')
    expect((await page.request.post(`${base}/learning/sessions/${item.id}/abandon`,{headers:{Origin:'http://127.0.0.1:3008','X-CSRF-Token':csrf}})).status()).toBe(200);
  await page.goto('/courses');const tabs=page.getByRole('navigation',{name:'Learn sections'});
  await expect(tabs.getByRole('link')).toHaveCount(3);
  await tabs.getByRole('link',{name:'Grammar',exact:true}).click();
  await expect(page.getByRole('heading',{name:'When to use it'})).toBeVisible();
  await page.getByRole('navigation',{name:'Learn sections'}).getByRole('link',{name:'Practice',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Sentence building',exact:true})).toBeVisible();
  await page.goto(`/learn/${fixture.lesson_id}`);
  await page.getByRole('button',{name:'Start or continue lesson'}).click();
  await expect(page).toHaveURL(/\/learning\/sessions\//);await enterExercises(page);const sessionURL=page.url();
  await expect(page.getByText('Draft Preview:',{exact:false}).first()).toBeVisible();
  await page.getByRole('radio',{name:'suis',exact:true}).check();
  await page.getByRole('button',{name:'Submit answer',exact:true}).click();await next(page);
  await page.getByLabel('Your answer',{exact:true}).fill(' es ');
  await page.getByRole('button',{name:'Submit answer',exact:true}).click();await next(page);
  await page.getByRole('link',{name:/Save and exit/}).click();await page.goto(sessionURL);
  await expect(page.getByRole('heading',{name:'Correct!',exact:true})).toBeVisible();await page.getByRole('button',{name:'Continue',exact:true}).click();
  const words=page.getByLabel('Available words');
  for(const word of ['Je','suis','étudiant'])await words.getByRole('button',{name:word,exact:true}).click();
  await page.getByRole('button',{name:'Undo word'}).click();
  await words.getByRole('button',{name:'étudiant',exact:true}).click();
  await page.getByRole('button',{name:'Submit answer',exact:true}).click();await next(page);
  for(const [fr,en] of [['Je suis ici.','I am here.'],['Tu es ici.','You are here.'],['Elle est ici.','She is here.']])await page.getByLabel(fr,{exact:true}).selectOption({label:en});
  await page.getByRole('button',{name:'Submit answer',exact:true}).click();await next(page);
  await page.getByRole('button',{name:'Load French audio'}).click();
  const audio=page.getByLabel('French listening audio');await expect(audio).toBeVisible({timeout:60000});
  await expect.poll(()=>audio.evaluate((element:HTMLAudioElement)=>element.readyState),{timeout:60000}).toBeGreaterThanOrEqual(2);
  await audio.evaluate(async(element:HTMLAudioElement)=>{await element.play();element.pause();element.currentTime=0;await element.play();element.pause();});
  await page.getByRole('radio',{name:'She is here.',exact:true}).check();
  await page.getByRole('button',{name:'Submit answer',exact:true}).click();await next(page);
  await page.getByLabel('Your answer',{exact:true}).fill('Je suis étudiante.');
  await page.getByRole('button',{name:'Submit answer',exact:true}).click();
  await page.getByRole('button',{name:'Continue to completion'}).click();
  await page.getByRole('button',{name:'Complete lesson',exact:true}).click();
  await expect(page).toHaveURL(/\/learning\/results\//);await expect(page.getByText('100%',{exact:true})).toBeVisible();
  await page.reload();await expect(page.getByText('100%',{exact:true})).toBeVisible();
  const saved=await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/learning/sessions/${sessionURL.split('/').at(-1)}`);
  const result=await saved.json();expect(result.exercises[5].submitted_answer).toEqual({text_answer:'Je suis étudiante.'});expect(result.status).toBe('completed');
});

test('ordinary account cannot use draft library, grammar, practice, AI context or speech context',async({page})=>{
  await login(page,fixture.learner);await page.goto('/courses');
  await expect(page.getByText('No published A1 courses yet',{exact:false})).toBeVisible();
  const base=process.env.PLAYWRIGHT_API_BASE_URL!;
  for(const path of ['/learning/library','/learning/grammar'])expect((await (await page.request.get(base+path)).json()).items).toEqual([]);
  await page.goto('/practice');await expect(page.getByRole('button',{name:'Start practice'}).first()).toBeDisabled();
  const cookies=await page.context().cookies();const csrf=cookies.find(c=>c.name===csrfCookie)!.value;
  for(const action of ['tutor','speaking'])expect((await page.request.post(`${base}/learning/lessons/${fixture.lesson_id}/${action}`,{headers:{Origin:'http://127.0.0.1:3008','X-CSRF-Token':csrf}})).status()).toBe(404);
});

test('grammar AI and speaking actions reuse owned linked conversations',async({page})=>{
  await login(page,fixture.admin);await page.goto(`/learn/${fixture.lesson_id}`);
  await page.getByRole('button',{name:'Ask AI Tutor',exact:true}).click();await expect(page).toHaveURL(/\/ai-tutor\/[0-9a-f-]+$/);
  await page.goto(`/learn/${fixture.lesson_id}`);await page.getByRole('button',{name:'Practice speaking',exact:true}).click();
  await expect(page).toHaveURL(/\/voice-practice\/conversations\/[0-9a-f-]+$/);
  await expect(page.getByRole('button',{name:/Record/}).first()).toBeVisible();
});

test('mobile sentence controls support keyboard and reset without overflow',async({page})=>{
  await page.setViewportSize({width:390,height:844});await login(page,fixture.admin);await page.goto('/practice');
  const card=page.getByRole('article').filter({has:page.getByRole('heading',{name:'Sentence building',exact:true})});
  await card.getByRole('button',{name:'Start practice'}).click();await expect(page).toHaveURL(/\/learning\/sessions\//);
  await page.getByLabel('Available words').getByRole('button',{name:'Je',exact:true}).focus();await page.keyboard.press('Enter');
  await expect(page.getByRole('button',{name:'Remove Je',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Reset sentence'}).click();await expect(page.getByLabel('Available words').getByRole('button')).toHaveCount(3);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
