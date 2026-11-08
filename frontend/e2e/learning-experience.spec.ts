import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {enterExercises} from './learning-navigation';
let fixture:{admin:string;learner:string;lesson_id:string;password:string};
const base=process.env.PLAYWRIGHT_API_BASE_URL??'';
test.beforeEach(()=>{test.skip(process.env.M08_E2E_REAL_API!=='1','Requires isolated real M08 PostgreSQL/API.');fixture=JSON.parse(readFileSync('../.speech-data/m08-browser-fixture.json','utf8'));});
async function login(page:Page,email:string){await page.goto('/login');await page.getByLabel('Email').fill(email);await page.locator('input[autocomplete="current-password"]').fill(fixture.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page).toHaveURL(/\/dashboard$/);}
async function fresh(page:Page){
  const csrf=(await page.context().cookies()).find(c=>c.name===(process.env.PLAYWRIGHT_CSRF_COOKIE_NAME??'fluentloop_csrf'))!.value;
  const active=await(await page.request.get(`${base}/learning/sessions?status=in_progress`)).json();
  for(const item of active.items)if(item.lesson_id===fixture.lesson_id&&item.activity_key==='lesson')expect((await page.request.post(`${base}/learning/sessions/${item.id}/abandon`,{headers:{Origin:new URL(page.url()).origin,'X-CSRF-Token':csrf}})).ok()).toBe(true);
  await page.goto(`/learn/${fixture.lesson_id}`);await page.getByRole('button',{name:'Start or continue lesson'}).click();await expect(page).toHaveURL(/\/learning\/sessions\//);
}

test('one reading step at a time, Back, refresh, saved context and grammar selection',async({page})=>{
  await login(page,fixture.admin);await fresh(page);
  const reading=page.getByRole('region',{name:'Lesson reading',exact:true});
  await expect(reading.getByRole('heading',{name:'Introduction',exact:true})).toBeVisible();
  await expect(page.getByRole('region',{name:'Exercise',exact:true})).toHaveCount(0);
  await reading.getByRole('button',{name:'Continue lesson'}).click();
  await expect(reading.getByRole('heading',{name:'Explanation',exact:true})).toBeVisible();
  await reading.getByRole('button',{name:'Continue lesson'}).click();
  await expect(reading.getByRole('heading',{name:'French examples',exact:true})).toBeVisible();
  await reading.getByRole('button',{name:'Back',exact:true}).click();
  await expect(reading.getByRole('heading',{name:'Explanation',exact:true})).toBeVisible();
  await page.reload();await expect(reading.getByRole('heading',{name:'Explanation',exact:true})).toBeVisible();
  await enterExercises(page);await page.getByRole('link',{name:/Save and exit/}).click();
  await expect(page).toHaveURL(new RegExp(`/courses\\?level=a1&lesson=${fixture.lesson_id}`));
  await page.getByRole('navigation',{name:'Learn sections'}).getByRole('link',{name:'Grammar',exact:true}).click();
  await expect(page.getByLabel('Grammar topic')).toBeVisible();
  await expect(page.getByRole('heading',{name:'When to use it',exact:true})).toBeVisible();
  for(const width of [390,320]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);}
  await page.getByRole('button',{name:'Practice this grammar',exact:true}).click();
  await expect(page.getByRole('region',{name:'Exercise',exact:true})).toBeVisible();
  await expect(page.getByText('Focused practice · does not complete the full lesson',{exact:true})).toBeVisible();
});

test('a lost answer response preserves input and reloads the one saved attempt',async({page})=>{
  await login(page,fixture.admin);await fresh(page);await enterExercises(page);const sid=page.url().split('/').at(-1);
  let posts=0;
  await page.route('**/learning/sessions/*/answers',async route=>{posts++;const response=await route.fetch();expect(response.ok()).toBe(true);await route.abort('failed');});
  await page.getByRole('radio',{name:'es',exact:true}).check();
  await page.getByRole('button',{name:'Submit answer',exact:true}).click({clickCount:2});
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('radio',{name:'es',exact:true})).toBeChecked();expect(posts).toBe(1);
  await page.getByRole('button',{name:'Reload saved progress',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Not quite.',exact:true})).toBeVisible();
  const saved=await(await page.request.get(`${base}/learning/sessions/${sid}`)).json();expect(saved.answered_exercises).toBe(1);expect(saved.exercises[0].submitted_answer.selected_option_id).toBeTruthy();
});

test('empty-level alternatives preserve selected context without changing account level',async({page})=>{
  await login(page,fixture.learner);await page.goto('/courses?level=c2');
  await expect(page.getByText('No published C2 courses yet',{exact:true})).toBeVisible();
  await expect(page.getByRole('region',{name:'Other ways to practice'}).getByRole('link',{name:'AI Tutor',exact:true})).toBeVisible();
  await page.getByRole('navigation',{name:'Learn sections'}).getByRole('link',{name:'Grammar',exact:true}).click();await expect(page).toHaveURL(/\/grammar\?level=c2$/);
  await expect(page.getByText('No published grammar topics are available at C2 yet.',{exact:true})).toBeVisible();
  await page.getByRole('navigation',{name:'Learn sections'}).getByRole('link',{name:'Practice',exact:true}).click();await expect(page).toHaveURL(/\/practice\?level=c2$/);
  await expect(page.getByRole('button',{name:'Start practice'}).first()).toBeDisabled();
  expect((await(await page.request.get(`${base}/users/me/preferences`)).json()).current_level).toBe('a1');
});
