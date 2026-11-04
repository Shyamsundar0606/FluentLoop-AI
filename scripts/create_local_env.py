"""Generate private development/ephemeral CI configuration without overwriting it."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.env')
    parser.add_argument('--ci', action='store_true')
    parser.add_argument('--database-host', default='db')
    args = parser.parse_args()
    if args.ci and not (os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('GITHUB_ENV')):
        raise SystemExit('CI mode requires a GitHub Actions environment.')
    values = dict(line.split('=', 1) for line in (ROOT / '.env.example').read_text().splitlines()
                  if line and not line.startswith('#') and '=' in line)
    password, preview_password = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
    user = 'fluentloop_ci' if args.ci else 'fluentloop'
    url = f'postgresql+psycopg://{user}:{password}@{args.database_host}:5432/{user}'
    values.update(POSTGRES_USER=user, POSTGRES_DB=user, POSTGRES_PASSWORD=password,
                  DATABASE_URL=url, PREVIEW_POSTGRES_PASSWORD=preview_password,
                  PREVIEW_DATABASE_URL=f'postgresql+psycopg://fluentloop_preview:{preview_password}@preview-db:5432/fluentloop_preview',
                  SPEECH_WORKER_TOKEN=secrets.token_urlsafe(48),
                  PREVIEW_SPEECH_WORKER_TOKEN=secrets.token_urlsafe(48))
    if args.ci:
        values.update(APP_ENV='test', REDIS_URL='redis://127.0.0.1:6379/0')
        # GitHub interprets these workflow commands and redacts their values
        # before subsequent steps display the environment in public logs.
        for value in (password, preview_password, values['SPEECH_WORKER_TOKEN'],
                      values['PREVIEW_SPEECH_WORKER_TOKEN']):
            print(f'::add-mask::{value}', flush=True)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    if os.name == 'nt':
        sid = subprocess.check_output(['powershell', '-NoProfile', '-Command',
            '[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'], text=True).strip()
        result = subprocess.run(['icacls', str(args.output), '/inheritance:r', '/grant:r',
            f'*{sid}:F', '*S-1-5-18:F', '*S-1-5-32-544:F'], capture_output=True)
        if result.returncode:
            os.close(fd)
            args.output.unlink()
            raise SystemExit('Could not restrict private configuration permissions.')
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(''.join(f'{key}={value}\n' for key, value in values.items()))
    if args.ci:
        # Only fresh disposable-runner credentials; never deployment credentials.
        exports = {key: values[key] for key in ('POSTGRES_USER', 'POSTGRES_DB', 'DATABASE_URL', 'REDIS_URL', 'APP_ENV')}
        exports['BROWSER_TEST_DATABASE_URL'] = f'postgresql+psycopg://{user}:{password}@db:5432/fluentloop_e2e'
        with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as stream:
            stream.write(''.join(f'{key}={value}\n' for key, value in exports.items()))
    print('Created private configuration with independent random credentials; values withheld.')


if __name__ == '__main__':
    main()
