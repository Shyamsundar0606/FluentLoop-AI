import {defineConfig,devices} from '@playwright/test';

// Private synthetic WAV evidence only: no application server or learner login.
export default defineConfig({
  testDir:'./e2e',testMatch:'roadmap-audio.spec.ts',workers:1,retries:0,
  timeout:60000,reporter:'list',
  use:{...devices['Desktop Chrome'],headless:true,trace:'off',
    launchOptions:{args:['--mute-audio']}},
});
