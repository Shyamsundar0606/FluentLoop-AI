import {expect,test} from '@playwright/test';
import {readFileSync,mkdirSync} from 'node:fs';

type Fixture={admin:string;learner:string;answers:Record<string,string>;options:string[]};
let fixture:Fixture;
test.beforeEach(()=>{
  test.skip(process.env.STUDY_E2E_REAL_API!=='1','Requires the isolated M07 PostgreSQL API and prepared test accounts.');
  fixture=JSON.parse(readFileSync('../.speech-data/m07-browser-fixture.json','utf8')) as Fixture;
});
async function login(page:import('@playwright/test').Page,email:string){
  await page.goto('/login');await page.getByLabel('Email').fill(email);
  await page.locator('input[autocomplete="current-password"]').fill('IsolatedStudyTest2026!');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test('live PostgreSQL daily plan, three reviews, lesson completion, persistence and level history',async({page})=>{
  test.setTimeout(120000);
  await login(page,fixture.admin);
  const plan=page.getByRole('region',{name:"Today's French Plan"});
  await plan.getByRole('button',{name:'Create today’s plan'}).click();
  await expect(plan.getByRole('button',{name:'Start next activity',exact:true})).toBeVisible();
  await expect(plan).toContainText('15-minute daily goal');
  await expect(plan).toContainText('Review vocabulary');
  if(process.env.UI_SCREENSHOTS==='1'){
    mkdirSync('../docs/verification/milestone-07',{recursive:true});
    for(const width of [390,1440]){await page.setViewportSize({width,height:1000});await plan.scrollIntoViewIfNeeded();await page.screenshot({path:`../docs/verification/milestone-07/plan-${width}.png`});}
  }
  const firstPlan=await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/study/today`);
  const identity=(await firstPlan.json()).id;
  await page.reload();await expect(plan).toContainText('Review vocabulary');
  await plan.getByRole('button',{name:'Start next activity',exact:true}).click();
  await expect(page).toHaveURL(/\/review\/sessions\/[0-9a-f-]+$/);
  let posts=0;page.on('request',r=>{if(r.method()==='POST' && /\/review\/sessions\/[^/]+\/answers$/.test(r.url()))posts++;});
  let intercepted=false;
  const refreshGate={release:()=>{},ready:false};
  await page.route('**/api/v1/review/sessions/*',async route=>{
    if(route.request().method()==='GET' && posts>0 && !intercepted){
      intercepted=true;const response=await route.fetch();
      await new Promise<void>(resolve=>{refreshGate.release=resolve;refreshGate.ready=true;});
      await route.fulfill({response});
    }else await route.continue();
  });
  for(let i=0;i<3;i++){
    const prompt=await page.getByRole('heading',{level:2,name:/Write in French:/}).innerText();
    const expected=fixture.answers[prompt];expect(expected).toBeTruthy();
    await expect(page.getByText('Draft preview — unreviewed vocabulary',{exact:true})).toBeVisible();
    if(i===0 && process.env.UI_SCREENSHOTS==='1'){
      for(const width of [320,390,1440]){await page.setViewportSize({width,height:1000});await page.getByLabel('Your French answer').focus();await expect(page.getByRole('button',{name:'Check answer',exact:true})).toBeInViewport();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`../docs/verification/milestone-07/card-${width}.png`});}
    }
    await expect(page.getByRole('region',{name:'Review feedback'})).toHaveCount(0);
    await page.getByLabel('Your French answer').fill(i===1?'a deliberately wrong answer':expected);
    await page.getByLabel('How did recall feel?').selectOption(i===1?'easy':'normal');
    await page.getByRole('button',{name:'Check answer',exact:true}).click({clickCount:2});
    const feedback=page.getByRole('region',{name:'Review feedback'});
    await expect(feedback.getByRole('heading',{name:i===1?'Not quite.':'Correct!',exact:true})).toBeVisible();
    await expect(feedback).toContainText('Correct answer:');
    await expect(feedback).toContainText('Next review:');
    if(i===0){await expect.poll(()=>refreshGate.ready).toBe(true);await expect(feedback.getByRole('button',{name:'Next card'})).toBeDisabled();refreshGate.release();}
    if(i<2)await feedback.getByRole('button',{name:'Next card'}).click();
    else await feedback.getByRole('button',{name:'Finish review'}).click();
  }
  expect(posts).toBe(3);
  await expect(page.getByRole('heading',{name:'Review complete',exact:true})).toBeVisible();
  await page.getByRole('link',{name:'Return to today’s plan'}).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(plan).toContainText('completed');
  const saved=await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/study/today`);
  expect((await saved.json()).id).toBe(identity);
  await plan.getByRole('button',{name:'Start next activity',exact:true}).click();
  await expect(page).toHaveURL(/\/learning\/sessions\/[0-9a-f-]+$/);
  for(let i=0;i<5;i++){
    await page.locator(`input[value="${fixture.options[i]}"]`).check();
    await page.getByRole('button',{name:'Submit answer',exact:true}).click();
    await expect(page.getByRole('heading',{name:'Correct!',exact:true})).toBeVisible();
    await page.getByRole('button',{name:i===4?'Continue to completion':'Continue',exact:true}).click();
  }
  await page.getByRole('button',{name:'Complete lesson',exact:true}).click();
  await expect(page).toHaveURL(/\/learning\/results\/[0-9a-f-]+$/);
  await page.goto('/dashboard');
  await expect(plan).toContainText('completed');
  const progress=await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/review/progress`);
  expect((await progress.json()).reviews_completed).toBe(3);
  await page.reload();await expect(plan).toContainText('completed');
  await page.locator('.signout-button:visible').click();
  await expect(page).toHaveURL(/\/login(?:\?|$)/);await login(page,fixture.admin);
  await expect(plan).toContainText('completed');
  await page.getByText('Learning preferences',{exact:true}).click();
  const level=page.getByRole('combobox',{name:'Change your French level',exact:true});
  await level.selectOption('a2');
  await page.getByRole('button',{name:'Save level',exact:true}).click();
  await expect(page.getByText('French level updated.',{exact:true})).toBeVisible();
  await page.getByRole('region',{name:"Today's French Plan"}).getByRole('button',{name:'Create today’s plan'}).click();
  await expect(plan).toContainText('A2');
  await page.goto('/review');
  await expect(page.getByRole('region',{name:'Review history'})).toContainText('A1');
  await expect(page.getByRole('region',{name:'Vocabulary review progress'})).toContainText('3 reviews completed');
  const history=await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/study/plans`);
  expect((await history.json()).items.map((p:{cefr_level:string})=>p.cefr_level)).toEqual(expect.arrayContaining(['A1','A2']));
  if(process.env.UI_SCREENSHOTS==='1'){
    mkdirSync('../docs/verification/milestone-07',{recursive:true});
    for(const width of [390,1440]){await page.setViewportSize({width,height:900});await page.screenshot({path:`../docs/verification/milestone-07/history-${width}.png`});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  }
});

test('ordinary learner receives practice alternatives and cannot read draft cards or another plan',async({page})=>{
  await login(page,fixture.learner);
  const plan=page.getByRole('region',{name:"Today's French Plan"});
  await plan.getByRole('button',{name:'Create today’s plan'}).click();
  await expect(plan).toContainText('French conversation');
  await expect(plan).not.toContainText('Draft preview');
  const due=await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/review/due`);
  expect((await due.json()).available_vocabulary_count).toBe(0);
  await page.goto('/review');await expect(page.getByText(/No permitted vocabulary is due/)).toBeVisible();
  const courses=await page.request.get(`${process.env.PLAYWRIGHT_API_BASE_URL}/courses?level=A1`);
  expect((await courses.json()).items).toHaveLength(0);
});

test('a simulated plan-network outage leaves existing practice navigation available',async({page})=>{
  await page.route('**/api/v1/study/today',route=>route.abort('failed'));
  await login(page,fixture.admin);
  await expect(page.getByRole('region',{name:"Today's French Plan"}).getByRole('alert')).toContainText('Your other practice activities remain available.');
  await expect(page.getByRole('navigation',{name:'Main navigation'}).getByRole('link')).toHaveCount(5);
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'AI Tutor',exact:true}).click();
  await expect(page).toHaveURL(/\/ai-tutor$/);
});
