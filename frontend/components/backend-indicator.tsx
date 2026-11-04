'use client';

import { useEffect, useState } from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

type HealthState = {
  status: 'ok' | 'degraded' | 'unknown';
  service?: string;
  version?: string;
  environment?: string;
  timestamp?: string;
};

export function BackendIndicator() {
  const [health, setHealth] = useState<HealthState>({ status: 'unknown' });
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    const fetchHealth = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health/live`, {
          signal: controller.signal,
          headers: { Accept: 'application/json' },
        });

        if (!response.ok) {
          throw new Error(`Health check failed with status ${response.status}`);
        }

        const payload = (await response.json()) as HealthState;
        setHealth({ ...payload, status: payload.status ?? 'ok' });
      } catch {
        setHealth({ status: 'degraded' });
      } finally {
        setChecking(false);
      }
    };

    void fetchHealth();
    return () => controller.abort();
  }, []);

  const isHealthy = health.status === 'ok';

  return (
    <div className="inline-flex items-center gap-3 rounded-full border border-slate-200 bg-white/80 px-3 py-2 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
      <span
        className={`h-2.5 w-2.5 rounded-full ${isHealthy ? 'bg-emerald-500' : checking ? 'bg-amber-400' : 'bg-rose-500'}`}
        aria-hidden="true"
      />
      <div className="flex flex-col leading-tight">
        <span className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
          Backend status
        </span>
        <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
          {checking ? 'Checking...' : isHealthy ? 'Connected' : 'Unavailable'}
        </span>
      </div>
    </div>
  );
}
