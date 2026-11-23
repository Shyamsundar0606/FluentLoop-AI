// Use the pinned Next.js server and its own graceful signal cleanup in-process.
// No OS process kill is sent (Windows Node kill('SIGTERM') is not graceful).
const { existsSync } = require('node:fs');
const { resolve } = require('node:path');
const dir = resolve(__dirname, '../frontend');
// Match `next dev`'s default bundler before loading Next internals. The project
// uses the Turbopack Tailwind loader and Cache Components.
process.env.TURBOPACK = '1';
process.env.__NEXT_DEV_SERVER = '1';
const { startServer } = require(resolve(dir, 'node_modules/next/dist/server/lib/start-server'));
const stopFile = process.argv[3];
let requested = false;
startServer({ dir, port: Number(process.argv[2]), hostname: '127.0.0.1',
  isDev: true, allowRetry: false }).then(() => {
  setInterval(() => {
    if (!requested && existsSync(stopFile)) {
      requested = true;
      // Next 16.4.6 installs this handler after listen; fail closed if it changes.
      if (!process.listenerCount('SIGTERM')) {
        console.error('Next graceful handler unavailable; manual shutdown required.');
        return;
      }
      process.emit('SIGTERM', 'SIGTERM');
    }
  }, 250);
}).catch(() => { console.error('Local Next startup failed.'); process.exitCode = 1; });
