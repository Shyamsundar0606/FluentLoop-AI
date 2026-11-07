import { expect, type Page } from '@playwright/test';

// Existing regression flows may resume a legacy snapshot or start a guided
// lesson. Follow the real UI; do not modify snapshot position from the test DB.
export async function enterExercises(page: Page) {
  const reading=page.getByRole('region',{name:'Lesson reading',exact:true});
  const exercise=page.getByRole('region',{name:'Exercise',exact:true});
  await expect(reading.or(exercise)).toBeVisible();
  for(let count=0;count<3 && await reading.isVisible();count++) {
    const step=await page.locator('[aria-label="Lesson steps"] [aria-current="step"]').innerText();
    const response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/position'));
    await reading.getByRole('button',{name:/^(Continue lesson|Start exercises)$/}).click();
    expect((await response).ok()).toBe(true);
    if(step.startsWith('1.'))await expect(reading.getByRole('heading',{name:'Explanation',exact:true})).toBeVisible();
    else if(step.startsWith('2.'))await expect(reading.getByRole('heading',{name:'French examples',exact:true})).toBeVisible();
    else await expect(exercise).toBeVisible();
  }
}
