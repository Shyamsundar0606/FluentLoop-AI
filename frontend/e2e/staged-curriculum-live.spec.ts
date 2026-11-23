import {expect,test} from '@playwright/test';
import {readFileSync} from 'node:fs';

test('all 52 mapped modules expose the 181 imported lessons and check plans in the disposable preview',async({page})=>{
  test.skip(process.env.STAGED_CURRICULUM_E2E!=='1','Requires the explicitly prepared disposable all-stage API.');
  const api=process.env.PLAYWRIGHT_API_BASE_URL!;
  const base=process.env.PLAYWRIGHT_BASE_URL!;
  expect(new URL(api).hostname).toBe('127.0.0.1');expect(new URL(api).port).toBe('8001');
  expect(new URL(base).port).toBe('3001');
  const fixture=JSON.parse(readFileSync(process.env.PLAYWRIGHT_LEARNING_FIXTURE!,'utf8')) as {admin:string;password:string;preview_uuid:string};
  await page.goto('/login');await page.getByLabel('Email').fill(fixture.admin);
  await page.locator('input[autocomplete="current-password"]').fill(fixture.password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page).toHaveURL(/\/dashboard$/);
  const me=await (await page.request.get(`${api}/auth/me`)).json();expect(me.user.id).toBe(fixture.preview_uuid);expect(me.user.role).toBe('learner');
  const response=await page.request.get(`${api}/learning/path`);expect(response.status()).toBe(200);
  const path=await response.json();expect(path.certification).toBe(false);
  expect(path.stages.map((s:{available_lessons:number})=>s.available_lessons)).toEqual([12,39,26,26,26,26,26]);
  const modules=path.stages.flatMap((s:{modules:unknown[]})=>s.modules);expect(modules).toHaveLength(52);
  const ids=new Set<string>();
  for(const learningModule of modules){expect(learningModule.available_lessons).toBeGreaterThan(0);expect(learningModule.formative_evidence.mastery_demonstrated).toBe(false);for(const lesson of learningModule.lessons)ids.add(lesson.id);}
  expect(ids.size).toBe(181);
  const checks=await page.request.get(`${api}/learning/checkpoints`);expect(checks.status()).toBe(200);
  const plans=(await checks.json()).plans;
  expect(plans).toHaveLength(59);
  expect(plans.filter((p:{kind:string})=>p.kind==='level_end')).toHaveLength(7);
  expect(plans.every((p:{overall_score:number|null;certification:boolean;available:boolean})=>p.available&&p.overall_score===null&&!p.certification)).toBe(true);
  await page.goto('/learning-path');await expect(page.getByRole('heading',{name:'Your French learning path'})).toBeVisible();
  for(const level of ['A0','A1','A2','B1','B2','C1','C2']){
    await page.getByRole('navigation',{name:'Learning stages'}).getByRole('button',{name:level,exact:true}).click();
    const region=page.getByRole('region',{name:`${level} learning path`});await expect(region).toBeVisible();
    await expect(region.getByText('Lessons for this module are being prepared.',{exact:true})).toHaveCount(0);
    await expect(region.getByRole('link').first()).toBeVisible();
  }
  await page.goto('/checkpoints');
  await expect(page.getByRole('heading',{name:'Module and level check plans'})).toBeVisible();
  await page.getByRole('navigation',{name:'Check stages'}).getByRole('button',{name:'C2',exact:true}).click();
  await expect(page.getByRole('heading',{level:2})).toHaveCount(9);
  expect((await (await page.request.get(`${api}/users/me/preferences`)).json()).current_level).toBe('a1');
});
