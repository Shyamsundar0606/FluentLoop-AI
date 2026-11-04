export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly retryAfterSeconds?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function csrfToken(): string | undefined {
  if (typeof document === 'undefined') return undefined;
  const cookieName = process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME ?? 'fluentloop_csrf';
  const prefix = `${cookieName}=`;
  const item = document.cookie.split('; ').find((cookie) => cookie.startsWith(prefix));
  return item ? decodeURIComponent(item.slice(prefix.length)) : undefined;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  headers.set('Accept', 'application/json');

  const method = (options.method ?? 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = csrfToken();
    if (token) headers.set('X-CSRF-Token', token);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    method,
    headers,
    credentials: 'include',
    cache: 'no-store',
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body && typeof body.detail === 'string'
      ? body.detail
      : response.status === 422
        ? 'Please check the information you entered and try again.'
        : 'The request could not be completed.';
    const retryAfter = response.headers.get('Retry-After');
    const retryAfterSeconds = retryAfter && /^\d+$/.test(retryAfter) ? Number(retryAfter) : undefined;
    throw new ApiError(detail, response.status, retryAfterSeconds);
  }
  return body as T;
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError && error.status === 429) {
    const seconds = error.retryAfterSeconds;
    if (seconds === undefined) {
      return 'Too many attempts. Please wait a little while before trying again.';
    }
    if (seconds < 60) {
      return `Too many attempts. Please try again in ${seconds} ${seconds === 1 ? 'second' : 'seconds'}.`;
    }
    const minutes = Math.ceil(seconds / 60);
    return `Too many attempts. Please try again in about ${minutes} ${minutes === 1 ? 'minute' : 'minutes'}.`;
  }
  return error instanceof Error ? error.message : fallback;
}
