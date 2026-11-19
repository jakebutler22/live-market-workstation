import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'

// webServer cwd differs from the test runner. Resolve the approved local cache
// once so neither local checks nor CI look outside this repository.
process.env.PLAYWRIGHT_BROWSERS_PATH = fileURLToPath(new URL('../.cache/ms-playwright', import.meta.url))

export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, retries: 0,
  reporter: [['list']], timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:5174', viewport: { width: 1440, height: 900 }, trace: 'retain-on-failure' },
  webServer: [
    { command: '.venv/bin/python -m scripts.browser_server', cwd: '..', url: 'http://127.0.0.1:8123/api/health', reuseExistingServer: false, timeout: 30000 },
    { command: 'npm run dev -- --port 5174', url: 'http://127.0.0.1:5174', reuseExistingServer: false, env: {API_TARGET:'http://127.0.0.1:8123'}, timeout: 30000 },
  ],
})
