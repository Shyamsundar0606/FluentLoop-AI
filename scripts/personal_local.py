"""Opt-in Windows daily-use supervisor. Never migrates, imports or recreates data.

Start stays in the calling console. Stop writes a private per-run request; only
the supervisor holding the live Windows lock may act on its own child handles.
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import UUID, uuid4
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".publication-private" / "personal-local"
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
# Windows may take about two seconds to deliver a loopback connection refusal.
# A short timeout is inconclusive, never evidence that a port is free.
CLOSED_PORT_TIMEOUT_SECONDS = 3


class Refused(RuntimeError):
    pass


def command(args, *, timeout=60):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                            timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        # CLI stderr may contain local/private paths or config; do not echo it.
        raise Refused(f"{Path(str(args[0])).name} {args[1]} failed (exit {result.returncode}).")
    return result.stdout.replace("\x00", "")


def local_url(value):
    parsed = urlsplit(value)
    if parsed.hostname not in LOOPBACK or parsed.scheme not in {"http", "redis", "postgresql+psycopg"}:
        raise Refused("Only loopback HTTP, Redis and PostgreSQL endpoints are allowed.")
    return parsed


def load_config(path):
    if path is None or not path.is_file():
        raise Refused("Private config missing. Prepare .publication-private/personal-local/config.json from scripts/personal-local.example.json after identity review.")
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    for key in ("enable_personal_preview", "enable_ai", "enable_speech", "maintenance_reviewed"):
        if type(config.get(key)) is not bool:
            raise Refused(f"{key} must be an explicit JSON boolean.")
    if 'preserve_retained_audio' in config and type(config['preserve_retained_audio']) is not bool:
        raise Refused('preserve_retained_audio must be a JSON boolean.')
    if "REPLACE" in json.dumps(config):
        raise Refused("Configure the private example with confirmed existing identities first.")
    for name in ("database_url", "redis_url", "ollama_url"):
        local_url(config[name])
    expected_schemes = {"database_url": "postgresql+psycopg", "redis_url": "redis", "ollama_url": "http"}
    if any(urlsplit(config[key]).scheme != scheme for key, scheme in expected_schemes.items()):
        raise Refused("Use the expected loopback protocol for each service.")
    database = urlsplit(config["database_url"]).path.lstrip("/")
    if not database or database != config["expected_database"]:
        raise Refused("Database URL and independently confirmed expected_database must match.")
    roles = [item["role"] for item in config["containers"]]
    if sorted(roles) != ["db", "mailpit", "redis"]:
        raise Refused("Exactly db, redis and mailpit existing containers must be configured.")
    if len({item["id"] for item in config["containers"]}) != 3:
        raise Refused("Container IDs must be distinct.")
    for item in config["containers"]:
        if not re.fullmatch(r"[0-9a-f]{64}", item["id"]):
            raise Refused("Use full immutable existing container IDs, not names.")
        if item["role"] in {"db", "redis"} and not item.get("volume"):
            raise Refused("Confirm PostgreSQL and Redis persistent volume names.")
    config["containers"].sort(key=lambda item: ["db", "redis", "mailpit"].index(item["role"]))
    ports = [config[k] for k in ("frontend_port", "api_port", "speech_port")]
    if len(set(ports)) != 3 or any(type(p) is not int or not 1024 <= p <= 65535 for p in ports):
        raise Refused("Use three distinct unprivileged local ports.")
    if not config.get("ollama_model"):
        raise Refused("Select the already installed Ollama model; downloads are never automatic.")
    for user_id in config.get("personal_preview_user_ids", []):
        UUID(user_id)
    if config.get("enable_personal_preview") and not config.get("personal_preview_user_ids"):
        raise Refused("Preview requires a separately confirmed immutable learner UUID.")
    minimum_c, minimum_d = config.get("minimum_c_free_gib", 30), config.get("minimum_d_free_gib", 50)
    if any(type(value) not in (int, float) for value in (minimum_c, minimum_d)):
        raise Refused("Disk thresholds must be numeric GiB values.")
    if minimum_c < 30 or minimum_d < 50:
        raise Refused("Do not lower the recovery plan's 30 GiB C / 50 GiB D reserves.")
    return config


def json_http(url, headers=None):
    with urlopen(Request(url, headers=headers or {}), timeout=5) as response:
        return json.load(response)


def wait_for(check, *, seconds=90, children=()):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if any(p.poll() is not None for p in children):
            raise Refused("An owned application process exited; inspect its private log.")
        try:
            if check():
                return
        except (OSError, ValueError):
            pass
        time.sleep(.5)
    raise Refused("Readiness timed out. No migration, reset or forced shutdown will be attempted.")


def storage_check(config, *, announce=False):
    for drive, minimum in (("C:\\", config.get("minimum_c_free_gib", 30)),
                           ("D:\\", config.get("minimum_d_free_gib", 50))):
        free = shutil.disk_usage(drive).free
        if announce:
            print(f"{drive} free: {free / 1024**3:.2f} GiB (required {minimum} GiB)")
        if free < minimum * 1024**3:
            raise Refused("Storage reserve not met. Stop owned services gracefully; no cleanup is attempted.")


def initial_checks(config):
    if sys.platform != "win32":
        raise Refused("The personal launcher is Windows-only.")
    storage_check(config, announce=True)
    command(["wsl.exe", "--version"])
    docker = shutil.which("docker.exe")
    if not docker:
        candidate = Path(os.environ["LOCALAPPDATA"]) / "Programs/DockerDesktop/resources/bin/docker.exe"
        docker = str(candidate) if candidate.is_file() else None
    if not docker:
        raise Refused("Existing Docker CLI unavailable; no software will be installed.")
    command([docker, "--version"])
    for port in (config["frontend_port"], config["api_port"], config["speech_port"]):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                raise Refused(f"Port {port} is occupied; unrelated processes are left untouched.") from None
    node = shutil.which("node.exe")
    if not node or not (ROOT / "frontend/node_modules/next/dist/server/lib/start-server.js").is_file():
        raise Refused("Existing Node/Next dependencies missing; no install/build attempted.")
    for path in (ROOT / ".venv312/Scripts/python.exe", ROOT / ".venv-speech/Scripts/python.exe"):
        if not path.is_file():
            raise Refused("Existing Python environments are required; no reinstall attempted.")
    audio = Path(config["speech_storage_path"])
    if not audio.is_absolute() or audio.drive.lower() != "d:" or not audio.is_dir():
        raise Refused("Confirm the existing audio directory on D:; do not silently replace historical audio storage.")
    return docker, node


def database_check(config):
    """Read-only compatibility and identity checks, before API maintenance can run."""
    import psycopg
    from sqlalchemy.engine import make_url
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    # Historical revisions import app.core.database. Resolve them independently
    # of the caller's working directory, without executing any migration.
    backend_path = str(ROOT / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    url = make_url(config["database_url"])
    alembic = Config(str(ROOT / "backend/alembic.ini"))
    alembic.set_main_option("script_location", str(ROOT / "backend/alembic"))
    heads = set(ScriptDirectory.from_config(alembic).get_heads())
    with psycopg.connect(host=url.host, port=url.port or 5432, user=url.username,
                         password=url.password, dbname=url.database,
                         options="-c default_transaction_read_only=on", connect_timeout=5) as db:
        if db.execute("SELECT current_database()").fetchone()[0] != config["expected_database"]:
            raise Refused("Unexpected database identity.")
        if {row[0] for row in db.execute("SELECT version_num FROM alembic_version")} != heads:
            raise Refused("Schema differs from application head. Stop for separate migration review.")
        if config.get("enable_personal_preview"):
            for user_id in config["personal_preview_user_ids"]:
                row = db.execute("SELECT role,is_active,email_verified_at IS NOT NULL FROM users WHERE id=%s",
                                 (UUID(user_id),)).fetchone()
                if row != ("learner", True, True):
                    raise Refused("Confirmed preview UUID must identify an active verified learner.")


def environment(config):
    from dotenv import dotenv_values
    env = {**os.environ, **{k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}}
    origin = f"http://127.0.0.1:{config['frontend_port']}"
    env.update(APP_ENV="development", DATABASE_URL=config["database_url"], REDIS_URL=config["redis_url"],
               PYTHONPATH=str(ROOT / "backend"), PYTHONDONTWRITEBYTECODE="1",
               ENABLE_DRAFT_LEARNING_PREVIEW="false", CURRICULUM_REVIEWER_GRANTS="{}",
               ENABLE_PERSONAL_LEARNING_PREVIEW=str(config.get("enable_personal_preview", False)).lower(),
               PERSONAL_PREVIEW_USER_IDS=json.dumps(config.get("personal_preview_user_ids", [])),
               PERSONAL_PRESERVE_RETAINED_AUDIO=str(bool(config.get('enable_personal_preview') and config.get('preserve_retained_audio', True))).lower(),
               FRONTEND_ORIGIN=origin, CORS_ORIGINS=json.dumps([origin]),
               SESSION_COOKIE_NAME="fluentloop_personal_session", CSRF_COOKIE_NAME="fluentloop_personal_csrf",
               COOKIE_SECURE="false", COOKIE_SAMESITE="lax", SMTP_HOST="127.0.0.1", SMTP_PORT="1025",
               OLLAMA_BASE_URL=config["ollama_url"], OLLAMA_MODEL=config["ollama_model"],
               SPEECH_MODEL_PATH=str(ROOT / ".speech-models"),
               SPEECH_STORAGE_PATH=config["speech_storage_path"],
               SPEECH_WORKER_URL=f"http://127.0.0.1:{config['speech_port']}",
               NEXT_PUBLIC_API_BASE_URL=f"http://127.0.0.1:{config['api_port']}/api/v1",
               NEXT_PUBLIC_CSRF_COOKIE_NAME="fluentloop_personal_csrf", NODE_ENV="development",
               NEXT_TELEMETRY_DISABLED="1")
    env.pop("NEXT_MANUAL_SIG_HANDLE", None)
    if config.get("enable_speech", True) and not env.get("SPEECH_WORKER_TOKEN"):
        raise Refused("Existing private speech token missing. No token rotation attempted.")
    return env


class Supervisor:
    def __init__(self, config, docker, node, run_dir):
        self.config, self.docker, self.node, self.run_dir = config, docker, node, run_dir
        self.children = []
        self.started = []
        self.desktop_started = False
        self.handles = []

    def cli(self, *args):
        return command([self.docker, "--context", "desktop-linux", *args])

    def save(self, status):
        data = dict(status=status, run_dir=str(self.run_dir), supervisor_pid=os.getpid(),
                    started_containers=self.started, desktop_started=self.desktop_started,
                    children=[dict(name=n, pid=p.pid) for n, p, _ in self.children])
        (RUNTIME / "current.json").write_text(json.dumps(data), encoding="utf-8")

    def spawn(self, name, args, env, cwd):
        stop_file = self.run_dir / (name + ".stop")
        log = (self.run_dir / (name + ".log")).open("ab")
        self.handles.append(log)
        child = subprocess.Popen([str(a) for a in [*args, stop_file]], cwd=cwd, env=env,
                                 stdout=log, stderr=log,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.children.append((name, child, stop_file))
        self.save("starting")

    def start(self, *, infrastructure_only=False):
        try:
            self.cli("info", "--format", "{{.ServerVersion}}")
        except Refused:
            command([self.docker, "desktop", "start"], timeout=120)
            self.desktop_started = True
            self.save("starting")
        # Refuse other active FluentLoop writers; never stop them automatically.
        all_containers = json.loads(self.cli("inspect", *[c["id"] for c in self.config["containers"]]))
        for spec, item in zip(self.config["containers"], all_containers):
            if item["Id"] != spec["id"] or item["HostConfig"].get("AutoRemove"):
                raise Refused("Container identity/persistence mismatch.")
            expected = spec.get("volume")
            if expected and expected not in {m.get("Name") for m in item["Mounts"] if m["Type"] == "volume"}:
                raise Refused("Persistent volume differs from approved configuration.")
            destination = {"db": "/var/lib/postgresql/data", "redis": "/data"}.get(spec["role"])
            if destination and not any(m.get("Name") == expected and m["Destination"] == destination for m in item["Mounts"]):
                raise Refused("Expected data mount destination differs.")
        allowed = {c["id"] for c in self.config["containers"]}
        if set(self.cli("ps", "-q", "--no-trunc").split()) - allowed:
            raise Refused("Other containers are running. Review competing workloads before personal startup.")
        for spec, item in zip(self.config["containers"], all_containers):
            if not item["State"]["Running"]:
                self.cli("start", spec["id"])
                self.started.append(spec["id"])
                self.save("starting")
            elif self.desktop_started:
                # The daemon was absent at entry. These approved containers were
                # restarted by our Desktop launch, so this run owns their stop.
                self.started.append(spec["id"])
                self.save("starting")
            def healthy():
                state = json.loads(self.cli("inspect", "--format", "{{json .State}}", spec["id"]))
                return state.get("Health", {}).get("Status") == "healthy"
            wait_for(healthy)
        database_check(self.config)
        if infrastructure_only:
            self.save('ready_infrastructure')
            print('Approved infrastructure ready; application writers remain stopped. No migration or import was run.',flush=True)
            return
        env = environment(self.config)
        if self.config.get("enable_ai", True):
            models = json_http(self.config["ollama_url"].rstrip("/") + "/api/tags")
            if self.config["ollama_model"] not in {m["name"] for m in models["models"]}:
                raise Refused("Configured local model unavailable; no download attempted.")
        if self.config.get("enable_speech", True):
            self.spawn("speech", [ROOT / ".venv-speech/Scripts/python.exe", "-B", ROOT / "scripts/personal_uvicorn.py",
                                   "app.speech.worker:app", self.config["speech_port"]], env, ROOT / "backend")
            def speech_ready():
                result = json_http(env["SPEECH_WORKER_URL"] + "/health", {"X-Speech-Key": env["SPEECH_WORKER_TOKEN"]})
                return result.get("asr") is True and result.get("tts") is True
            wait_for(speech_ready, children=[p for _, p, _ in self.children])
        self.spawn("api", [ROOT / ".venv312/Scripts/python.exe", "-B", ROOT / "scripts/personal_uvicorn.py",
                           "app.main:app", self.config["api_port"]], env, ROOT / "backend")
        wait_for(lambda: json_http(env["NEXT_PUBLIC_API_BASE_URL"] + "/health/ready")["status"] == "ok",
                 children=[p for _, p, _ in self.children])
        self.spawn("frontend", [self.node, ROOT / "scripts/personal_next.cjs", self.config["frontend_port"]],
                   env, ROOT / "frontend")
        def page_ready():
            with urlopen(env["FRONTEND_ORIGIN"] + "/login", timeout=5) as response:
                return response.status == 200
        wait_for(page_ready, seconds=120, children=[p for _, p, _ in self.children])
        self.save("ready")
        print(f"Personal application: {env['FRONTEND_ORIGIN']}/login\nUse stop_personal_local.ps1 in another console, or Ctrl+C.", flush=True)

    def stop(self):
        self.save("stopping")
        # Never stop a dependent database if an owned writer cannot exit normally.
        for name, child, stop_file in reversed(self.children):
            stop_file.touch(exist_ok=True)
            try:
                child.wait(timeout=90)
            except subprocess.TimeoutExpired:
                self.save("manual_attention")
                raise Refused(f"{name} did not stop gracefully; databases left running.") from None
        if self.started:
            permitted = {c["id"] for c in self.config["containers"]}
            if set(self.cli("ps", "-q", "--no-trunc").split()) - permitted:
                self.save("manual_attention")
                raise Refused("Other container workloads appeared; dependent services left running for review.")
        for container_id in reversed(self.started):
            self.cli("stop", "--signal", "SIGTERM", "--timeout=-1", container_id)
            state = json.loads(self.cli("inspect", "--format", "{{json .State}}", container_id))
            if state["Running"] or state.get("OOMKilled") or state["ExitCode"] != 0:
                self.save("manual_attention")
                raise Refused("Container normal shutdown was not confirmed; no further stop attempted.")
        if self.desktop_started and not self.cli("ps", "-q").strip():
            command([self.docker, "desktop", "stop", "--timeout", "60"], timeout=90)
        self.save("stopped")
        for handle in self.handles:
            handle.close()


def request_stop():
    import msvcrt
    if not (RUNTIME / "supervisor.lock").exists():
        raise Refused("No supervisor lock exists; no process or service was touched.")
    with (RUNTIME / "supervisor.lock").open("r+b") as lock:
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            pass  # A live supervisor owns the lock, not an arbitrary saved PID.
        else:
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            raise Refused("Supervisor is not running. Review saved state; no PID kill attempted.")
    state = json.loads((RUNTIME / "current.json").read_text())
    run_dir = Path(state["run_dir"]).resolve()
    if run_dir.parent != RUNTIME.resolve() or not run_dir.name.startswith("run-"):
        raise Refused("Invalid private runtime state.")
    (run_dir / "stop.request").touch(exist_ok=True)
    wait_for(lambda: json.loads((RUNTIME / "current.json").read_text())["status"] == "stopped", seconds=300)
    print("Owned application and services stopped gracefully; data retained.")


def stopped_evidence(state, config):
    """No service control: refuse unless the saved runtime is demonstrably absent."""
    pids=[state['supervisor_pid']]+[child['pid'] for child in state.get('children',[])]
    if any(type(pid) is not int or pid<=0 for pid in pids):
        raise Refused('Invalid saved process identity; manual review required.')
    script="@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'docker' -or $_.ProcessId -in "+','.join(map(str,pids))+" } | Select-Object ProcessId,Name) | ConvertTo-Json -Compress"
    if command(['powershell.exe','-NoProfile','-Command',script],timeout=30).strip():
        raise Refused('A saved process or Docker process still exists; no state changed.')
    running=command(['wsl.exe','--list','--running','--quiet'],timeout=30).strip()
    if running:
        raise Refused('A WSL distribution is running; no state changed.')
    ports={config['frontend_port'],config['api_port'],config['speech_port'],
           urlsplit(config['database_url']).port or 5432,urlsplit(config['redis_url']).port or 6379,8025,1025}
    results={}
    for port in sorted(ports):
        with socket.socket() as client:
            client.settimeout(CLOSED_PORT_TIMEOUT_SECONDS)
            result=client.connect_ex(('127.0.0.1',port))
            if result==0:
                raise Refused(f'Port {port} is active; no state changed.')
            if result not in (errno.ECONNREFUSED,10061):
                raise Refused(f'Port {port} could not be confirmed closed; no state changed.')
            results[str(port)]=result
    return dict(saved_processes_absent=True,docker_processes_absent=True,wsl_running=False,ports_closed=True,
                port_results=results,probe_timeout_seconds=CLOSED_PORT_TIMEOUT_SECONDS)


def reconcile_stopped(config):
    import msvcrt
    if not RUNTIME.resolve().is_relative_to(ROOT.resolve()):
        raise Refused('Private runtime must remain inside the project.')
    state_file=RUNTIME/'current.json'
    if state_file.resolve().parent!=RUNTIME.resolve() or not state_file.is_file():
        raise Refused('Invalid or missing saved runtime state.')
    with (RUNTIME/'supervisor.lock').open('r+b') as lock:
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise Refused('A live supervisor owns the lock; no state changed.') from None
        try:
            state=json.loads(state_file.read_text())
            if state['status']=='stopped':
                print('Saved runtime is already confirmed stopped.');return
            evidence=stopped_evidence(state,config)
            record=RUNTIME/f'stopped-review-{uuid4().hex}.json'
            with record.open('x',encoding='utf-8') as output:
                json.dump(dict(original_state=state,evidence=evidence,at=datetime.now(timezone.utc).isoformat(),
                               graceful_shutdown_claimed=False),output,indent=2)
            state.update(status='stopped',reconciled_orphan=True,stopped_state_review=str(record))
            state_file.write_text(json.dumps(state),encoding='utf-8')
        finally:msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    print('Stopped-state bookkeeping reconciled; original state archived. No process, service or data was changed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "reconcile-stopped"])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--approve-protected-services", action="store_true")
    parser.add_argument("--recovery-prerequisites-satisfied", action="store_true")
    parser.add_argument('--confirm-stopped-review',action='store_true')
    parser.add_argument('--infrastructure-only',action='store_true',help='Explicit maintenance window: no API, frontend, AI or speech startup')
    args = parser.parse_args()
    if args.action == "stop":
        request_stop()
        return
    if args.action=='reconcile-stopped':
        if sys.platform!='win32' or not args.confirm_stopped_review:
            raise Refused('Stopped-state review requires Windows and --confirm-stopped-review; no service or state changed.')
        reconcile_stopped(load_config(args.config));return
    # Permission checks precede even loading a credential-bearing config.
    if not args.check_only and not (args.approve_protected_services and args.recovery_prerequisites_satisfied):
        raise Refused("Start requires explicit protected-runtime approval AND satisfied recovery prerequisites.")
    config = load_config(args.config)
    if not args.check_only and not config.get("maintenance_reviewed"):
        raise Refused("Review pending account-erasure jobs and audio retention before authorizing normal API maintenance.")
    docker, node = initial_checks(config)
    if args.check_only:
        print("Static preflight passed; no Docker/WSL startup or database access performed.")
        return
    import msvcrt
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / "supervisor.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise Refused("Another personal supervisor already owns the runtime.") from None
        state_file = RUNTIME / "current.json"
        if state_file.exists() and json.loads(state_file.read_text())["status"] != "stopped":
            raise Refused("Previous run was not confirmed stopped. Review private state before a new start.")
        run_dir = RUNTIME / ("run-" + uuid4().hex)
        run_dir.mkdir()
        supervisor = Supervisor(config, docker, node, run_dir)
        supervisor.save("starting")
        try:
            supervisor.start(infrastructure_only=args.infrastructure_only)
            next_storage_check = time.monotonic()
            while not (run_dir / "stop.request").exists():
                if any(p.poll() is not None for _, p, _ in supervisor.children):
                    raise Refused("Owned application exited unexpectedly; stopping owned dependents.")
                if time.monotonic() >= next_storage_check:
                    storage_check(config)
                    next_storage_check = time.monotonic() + 5
                time.sleep(.5)
        except KeyboardInterrupt:
            pass
        finally:
            supervisor.stop()


if __name__ == "__main__":
    try:
        main()
    except (Refused, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(str(exc) if isinstance(exc, Refused) else "Local setup failed; check private configuration/dependencies. No destructive fallback.", file=sys.stderr)
        sys.exit(1)
