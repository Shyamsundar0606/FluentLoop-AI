import {readFileSync} from 'node:fs';

export type AdminFixture={admin:string;learner:string;lesson_id:string;password:string};

/** A dedicated admin stack must never silently use the personal learner fixture. */
export function adminFixture():AdminFixture{
  const path=process.env.PLAYWRIGHT_ADMIN_FIXTURE??'../.speech-data/m08-browser-fixture.json';
  const value=JSON.parse(readFileSync(path,'utf8')) as AdminFixture;
  if(!value.admin||!value.learner||!value.password||!value.lesson_id||value.admin===value.learner)
    throw new Error('Admin browser fixture is incomplete. Prepare the disposable admin browser harness.');
  return value;
}
