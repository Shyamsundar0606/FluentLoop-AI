import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3001';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL,
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: {
    command: `npm run dev -- --hostname 127.0.0.1 --port ${new URL(baseURL).port || '3001'}`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      NEXT_PUBLIC_API_BASE_URL: process.env.PLAYWRIGHT_API_BASE_URL ?? 'http://127.0.0.1:8001/api/v1',
      NEXT_PUBLIC_CSRF_COOKIE_NAME: process.env.PLAYWRIGHT_CSRF_COOKIE_NAME ?? 'fluentloop_csrf',
    },
  },
});
