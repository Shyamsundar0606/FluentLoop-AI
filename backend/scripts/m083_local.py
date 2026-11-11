"""Build and exercise 08.3 against a new, disposable M08 test database."""
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

import m08_local as local

FRONTEND = "http://127.0.0.1:3012"
API = "http://127.0.0.1:8012/api/v1"
MANUAL_FIXTURE = local.PRIVATE / "m09-manual-fixture.json"


def wait_for(url, process):
    for _ in range(90):
        if process.poll() is not None:
            break
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            time.sleep(1)
    raise SystemExit("Disposable service failed to start. Check private runtime logs.")


def seed(database_url, settings):
    os.environ.update({**local.env, **settings})
    sys.path.insert(0, str(local.ROOT / "backend"))
    from sqlalchemy import select
    from app.content_import import CONTENT_PATH, _import_data, load_content
    from app.core.database import SessionLocal
    from app.curriculum_models import Lesson
    from app.grammar_content import import_supplement, load_supplement
    from app.interactive_content import import_pack, load_pack
    from app.models import User, UserPreferences, UserProfile, utcnow
    from app.security import hash_password

    assert local.make_url(database_url).database.startswith("fluentloop_m08_3_test_")
    password = secrets.token_urlsafe(24)
    accounts = {"M083_PASSWORD": password}
    local.secrets.append(password)
    with SessionLocal.begin() as db:
        canonical = load_content(CONTENT_PATH)
        print("Canonical import:", _import_data(db, canonical))
        print("Canonical repeat:", _import_data(db, canonical))
        import_pack(db, load_pack())
        pack = load_supplement()
        print("Supplement import:", json.dumps(import_supplement(db, pack)))
        print("Supplement repeat:", json.dumps(import_supplement(db, pack)))
        for identity in ("admin", "learner", "reviewer"):
            email = f"m083-{identity}-{uuid4().hex[:10]}@example.com"
            accounts[f"M083_{identity.upper()}_EMAIL"] = email
            local.secrets.append(email)
            user = User(email=email, role="admin" if identity == "admin" else "learner",
                        password_hash=hash_password(password), email_verified_at=utcnow())
            db.add(user)
            db.flush()
            db.add(UserProfile(user_id=user.id, display_name="Curriculum tester", onboarding_completed_at=utcnow()))
            db.add(UserPreferences(user_id=user.id))
            if identity == "reviewer":
                settings["CURRICULUM_REVIEWER_GRANTS"] = json.dumps({str(user.id): {
                    "categories": ["linguistic_accuracy"], "qualification": "Synthetic isolated browser fixture"
                }})
        accounts["M083_LESSON_ID"] = str(db.scalar(select(Lesson.id).where(Lesson.slug == "m083-introducing-yourself")))
        accounts["M083_INTERACTIVE_LESSON_ID"] = str(db.scalar(select(Lesson.id).where(Lesson.slug == "m08-etre-interactive-lesson")))
    return accounts


def main():
    for port in (3012, 8012):
        with socket.socket() as connection:
            connection.bind(("127.0.0.1", port))
    folder = local.PRIVATE / "m08_3_runtime"
    folder.mkdir(parents=True, exist_ok=True)
    front = local.ROOT / "frontend"
    browser = {**os.environ, "NEXT_PUBLIC_API_BASE_URL": API,
               "NEXT_PUBLIC_CSRF_COOKIE_NAME": "fluentloop_m083_csrf"}
    subprocess.run(["node.exe", "node_modules/next/dist/bin/next", "build"], cwd=front, env=browser, check=True)

    database_url = local.database("fluentloop_m08_3_test_")
    isolated = json.loads(local.STATE.read_text(encoding="utf-8"))
    settings = {**isolated, "DATABASE_URL": database_url, "APP_ENV": "development",
                "FRONTEND_ORIGIN": FRONTEND, "CORS_ORIGINS": json.dumps([FRONTEND]),
                "SESSION_COOKIE_NAME": "fluentloop_m083_session", "CSRF_COOKIE_NAME": "fluentloop_m083_csrf",
                "REDIS_URL": "redis://127.0.0.1:6379/13", "SPEECH_STORAGE_PATH": str(folder / "audio")}
    local.run([sys.executable, "-m", "alembic", "upgrade", "head"], settings)
    accounts = seed(database_url, settings)

    with (folder / "api.log").open("w", encoding="utf-8") as api_log, (folder / "frontend.log").open("w", encoding="utf-8") as web_log:
        processes = []
        try:
            processes.append(subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--api"],
                cwd=local.ROOT / "backend", env={**os.environ, **settings}, stdout=api_log, stderr=subprocess.STDOUT))
            processes.append(subprocess.Popen(
                ["node.exe", "node_modules/next/dist/bin/next", "start", "--hostname", "127.0.0.1", "--port", "3012"],
                cwd=front, env=browser, stdout=web_log, stderr=subprocess.STDOUT))
            wait_for(API + "/health/ready", processes[0])
            wait_for(FRONTEND + "/login", processes[1])
            if "--serve-coach" in sys.argv:
                MANUAL_FIXTURE.write_text(json.dumps({
                    "email": accounts["M083_LEARNER_EMAIL"], "password": accounts["M083_PASSWORD"],
                }), encoding="utf-8")
                print(f"Disposable coach ready at {FRONTEND}/login. Press Ctrl+C to stop.")
                while all(process.poll() is None for process in processes):
                    time.sleep(1)
                raise SystemExit("A disposable service stopped. See private runtime logs.")
            test_env = {**browser, **accounts, "PLAYWRIGHT_BASE_URL": FRONTEND,
                        "PLAYWRIGHT_API_BASE_URL": API, "PLAYWRIGHT_CSRF_COOKIE_NAME": "fluentloop_m083_csrf",
                        "M083_E2E": "1", "M08_E2E_REAL_API": "1", "M08_E2E_SESSION_COOKIE_NAME": "fluentloop_m083_session"}
            specs = ["grammar-content.spec.ts", "authorized-preview.spec.ts"]
            if "--coach" in sys.argv:
                specs = ["ai-coach.spec.ts"]
                test_env["M09_E2E"] = "1"
            result = subprocess.run(
                ["node.exe", "node_modules/@playwright/test/cli.js", "test", *specs, "--workers=1",
                 "--trace", "off", "--output", str(folder / "browser")],
                cwd=front, env=test_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
            print(local.safe(result.stdout + result.stderr))
            return result.returncode
        finally:
            if "--serve-coach" in sys.argv:
                MANUAL_FIXTURE.unlink(missing_ok=True)
            for process in reversed(processes):
                process.terminate()
                process.wait(timeout=15)


def run_api():
    if not local.make_url(os.environ["DATABASE_URL"]).database.startswith("fluentloop_m08_3_test_"):
        raise SystemExit("Disposable API requires a dedicated test database.")
    sys.path.insert(0, str(local.ROOT / "backend"))
    from app.services import rate_limit
    import uvicorn

    class TestNamespace:
        def __init__(self, client):
            self.client = client
            self.prefix = f"m083-test:{uuid4().hex}:"

        def eval(self, script, count, key, *args):
            return self.client.eval(script, count, self.prefix + key, *args)

        def ttl(self, key):
            return self.client.ttl(self.prefix + key)

    rate_limit.redis_client = TestNamespace(rate_limit.redis_client)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8012)


def copy_coach(field):
    with urlopen(API + "/health/ready", timeout=5) as response:
        if json.load(response).get("status") != "ok":
            raise SystemExit("Start the disposable coach before copying credentials.")
    value = json.loads(MANUAL_FIXTURE.read_text(encoding="utf-8"))[field]
    subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                    "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
                   input=value, text=True, capture_output=True, check=True)
    print(f"Copied disposable learner {field}. Paste it into the matching field at {FRONTEND}/login.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--api"]:
        run_api()
    elif sys.argv[1:] in (["--copy-coach-email"], ["--copy-coach-password"]):
        copy_coach(sys.argv[1].rsplit("-", 1)[1])
    else:
        try:
            sys.exit(main())
        except KeyboardInterrupt:
            print("Disposable services stopped.")
