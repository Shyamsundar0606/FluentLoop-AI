"""Fail-closed launcher tests: fake Docker plus a disposable loopback ASGI server."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("personal_local", ROOT / "scripts/personal_local.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)


def configuration():
    c = json.loads((ROOT / "scripts/personal-local.example.json").read_text())
    c.update(database_url="postgresql+psycopg://test:test@127.0.0.1:1/disposable",
             expected_database="disposable", speech_storage_path=str(ROOT / ".speech-data"))
    for n, item in enumerate(c["containers"], 1):
        item["id"] = str(n) * 64
        if item["role"] == "redis":
            item["volume"] = "test_redis"
    return c


def load(tmp_path, config):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(config))
    return local.load_config(p)


def test_approval_refused_before_config_or_services(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["personal_local.py", "start"])
    monkeypatch.setattr(local, "load_config", lambda *_: pytest.fail("Must not load credentials"))
    with pytest.raises(local.Refused, match="explicit"):
        local.main()


def test_stopped_state_review_requires_explicit_flag(monkeypatch):
    monkeypatch.setattr(sys,'argv',['personal_local.py','reconcile-stopped'])
    monkeypatch.setattr(local,'load_config',lambda *_:pytest.fail('Must not load config without review intent'))
    with pytest.raises(local.Refused,match='confirm-stopped-review'):local.main()


@pytest.mark.skipif(os.name!='nt',reason='Windows runtime lock and stopped-state bookkeeping')
def test_stopped_review_archives_original_and_changes_only_private_state(tmp_path,monkeypatch):
    runtime=tmp_path/'.publication-private/personal-local';runtime.mkdir(parents=True)
    original={'status':'ready','supervisor_pid':123,'children':[]}
    (runtime/'current.json').write_text(json.dumps(original));(runtime/'supervisor.lock').write_bytes(b'0')
    monkeypatch.setattr(local,'ROOT',tmp_path);monkeypatch.setattr(local,'RUNTIME',runtime)
    monkeypatch.setattr(local,'stopped_evidence',lambda *_:dict(ports_closed=True,saved_processes_absent=True))
    local.reconcile_stopped(configuration())
    state=json.loads((runtime/'current.json').read_text())
    assert state['status']=='stopped' and state['reconciled_orphan']
    record=json.loads(Path(state['stopped_state_review']).read_text())
    assert record['original_state']==original and record['graceful_shutdown_claimed'] is False


@pytest.mark.parametrize('processes,running,port_result,passes',[
    ('','',10061,True), ('[{"ProcessId":123,"Name":"Docker Desktop.exe"}]','',10061,False),
    ('','Ubuntu-24.04',10061,False), ('','',0,False), ('','',10013,False),
    ('','',10035,False), ('','',10060,False),
])
def test_stopped_review_requires_absent_processes_wsl_and_confirmed_closed_ports(monkeypatch,processes,running,port_result,passes):
    def fake_command(args,**kwargs):return processes if args[0]=='powershell.exe' else running
    class ClosedSocket:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def settimeout(self,*args):pass
        def connect_ex(self,*args):return port_result
    monkeypatch.setattr(local,'command',fake_command)
    monkeypatch.setattr(local.socket,'socket',lambda:ClosedSocket())
    state={'supervisor_pid':123,'children':[{'pid':456}]}
    if passes:assert local.stopped_evidence(state,configuration())['ports_closed']
    else:
        with pytest.raises(local.Refused,match='no state changed'):local.stopped_evidence(state,configuration())


def test_windows_delayed_refusal_is_waited_for_not_assumed(monkeypatch):
    monkeypatch.setattr(local,'command',lambda *_a,**_k:'')
    timeouts=[]
    class DelayedRefusal:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def settimeout(self,value):self.timeout=value;timeouts.append(value)
        def connect_ex(self,*args):return 10061 if self.timeout>=2 else 10035
    monkeypatch.setattr(local.socket,'socket',DelayedRefusal)
    body=local.stopped_evidence({'supervisor_pid':123,'children':[]},configuration())
    assert body['ports_closed'] and set(body['port_results'].values())=={10061}
    assert timeouts and all(2<=value<=5 for value in timeouts)


def test_port_inspection_error_still_refuses(monkeypatch):
    monkeypatch.setattr(local,'command',lambda *_a,**_k:(_ for _ in ()).throw(local.Refused('inspection unavailable')))
    with pytest.raises(local.Refused,match='inspection unavailable'):
        local.stopped_evidence({'supervisor_pid':123,'children':[]},configuration())


@pytest.mark.parametrize('launch_daemon',[True,False])
@pytest.mark.parametrize('infrastructure_only',[True,False])
def test_only_containers_started_with_this_daemon_are_owned(tmp_path,monkeypatch,launch_daemon,infrastructure_only):
    c={**configuration(),'enable_ai':False,'enable_speech':False}
    supervisor=local.Supervisor(c,'fake-docker','fake-node',tmp_path)
    items=[]
    for spec in c['containers']:
        destination={'db':'/var/lib/postgresql/data','redis':'/data'}.get(spec['role'])
        items.append(dict(Id=spec['id'],HostConfig={'AutoRemove':False},State={'Running':True},
            Mounts=[dict(Type='volume',Name=spec['volume'],Destination=destination)] if destination else []))
    def cli(*args):
        if args[0]=='info':
            if launch_daemon:raise local.Refused('daemon absent')
            return 'version'
        if args[0]=='ps':return '\n'.join(s['id'] for s in c['containers'])
        if args[0]=='inspect' and '--format' in args:return json.dumps({'Health':{'Status':'healthy'}})
        if args[0]=='inspect':return json.dumps(items)
        pytest.fail('Unexpected service action')
    monkeypatch.setattr(supervisor,'cli',cli);monkeypatch.setattr(supervisor,'save',lambda *_:None)
    spawns=[]
    monkeypatch.setattr(supervisor,'spawn',lambda *args:spawns.append(args[0]))
    monkeypatch.setattr(local,'command',lambda *_a,**_k:'')
    monkeypatch.setattr(local,'database_check',lambda *_:None)
    monkeypatch.setattr(local,'environment',lambda *_:{'NEXT_PUBLIC_API_BASE_URL':'http://127.0.0.1:1/api/v1','FRONTEND_ORIGIN':'http://127.0.0.1:2'})
    monkeypatch.setattr(local,'json_http',lambda *_:{'status':'ok'})
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
    monkeypatch.setattr(local,'urlopen',lambda *_a,**_k:Response())
    supervisor.start(infrastructure_only=infrastructure_only)
    assert supervisor.started==([s['id'] for s in c['containers']] if launch_daemon else [])
    assert spawns==([] if infrastructure_only else ['api','frontend'])


@pytest.mark.parametrize("change", [
    {"database_url": "postgresql+psycopg://test:test@remote.example/db"},
    {"expected_database": "different"},
    {"minimum_c_free_gib": 10},
    {"enable_personal_preview": True, "personal_preview_user_ids": []},
    {"frontend_port": 8000},
])
def test_bad_or_unsafe_config_refused(tmp_path, change):
    c = configuration()
    c.update(change)
    with pytest.raises(local.Refused):
        load(tmp_path, c)


def test_container_order_normalized_and_no_grants_by_default(tmp_path):
    c = configuration()
    c["containers"].reverse()
    result = load(tmp_path, c)
    assert [c["role"] for c in result["containers"]] == ["db", "redis", "mailpit"]
    assert result["enable_personal_preview"] is False


def test_low_disk_refuses_before_any_command(monkeypatch):
    monkeypatch.setattr(local.sys, "platform", "win32")
    monkeypatch.setattr(local.shutil, "disk_usage", lambda _: type("Usage", (), {"free": 19 * 1024**3})())
    monkeypatch.setattr(local, "command", lambda *_a, **_k: pytest.fail("No WSL/Docker call allowed"))
    with pytest.raises(local.Refused, match="Storage reserve"):
        local.initial_checks(configuration())


@pytest.mark.parametrize("drive,free", [("C:\\", 29), ("D:\\", 49)])
def test_runtime_storage_reserve_checks_both_drives(monkeypatch, drive, free):
    def usage(path):
        return type("Usage", (), {"free": (free if path == drive else 100) * 1024**3})
    monkeypatch.setattr(local.shutil, "disk_usage", usage)
    with pytest.raises(local.Refused, match="Storage reserve"):
        local.storage_check(configuration())


def test_schema_check_resolves_revisions_outside_backend(tmp_path):
    """Real revision discovery with a fake DB, from a clean external cwd."""
    code = r'''
import importlib.util, json, sys
spec=importlib.util.spec_from_file_location('launcher',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
import psycopg
class Result:
    def __init__(self, rows):self.rows=rows
    def fetchone(self):return self.rows[0]
    def __iter__(self):return iter(self.rows)
class Database:
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def execute(self,query,*args):
        return Result([('disposable',)]) if 'current_database' in query else Result([('20261115_0016',)])
def connect(**kwargs):
    assert kwargs['dbname']=='disposable'
    assert 'default_transaction_read_only=on' in kwargs['options']
    return Database()
psycopg.connect=connect
module.database_check({'database_url':'postgresql+psycopg://test:test@127.0.0.1:1/disposable',
                      'expected_database':'disposable','enable_personal_preview':False})
print('schema discovery passed')
'''
    env = {**os.environ, "DATABASE_URL": "sqlite://", "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("PYTHONPATH", None)
    result = subprocess.run([sys.executable, "-B", "-c", code,
        str(ROOT / "scripts/personal_local.py")], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "schema discovery passed" in result.stdout


def test_readiness_requires_true_and_observes_child_exit(monkeypatch):
    child = type("Child", (), {"poll": lambda _: 1})()
    with pytest.raises(local.Refused, match="process exited"):
        local.wait_for(lambda: True, children=[child])


def test_stuck_writer_preserves_databases(tmp_path, monkeypatch):
    supervisor = local.Supervisor(configuration(), "fake-docker", "fake-node", tmp_path)
    def stuck(*_, **__):
        raise subprocess.TimeoutExpired("owned", 90)
    child = type("Child", (), {"wait": stuck})()
    supervisor.children = [("api", child, tmp_path / "api.stop")]
    supervisor.started = ["db-id"]
    monkeypatch.setattr(supervisor, "save", lambda *_: None)
    monkeypatch.setattr(supervisor, "cli", lambda *_: pytest.fail("Database must not be stopped"))
    with pytest.raises(local.Refused, match="databases left running"):
        supervisor.stop()


def test_stop_only_owned_containers_in_reverse_order(tmp_path, monkeypatch):
    c = configuration()
    supervisor = local.Supervisor(c, "fake", "fake", tmp_path)
    # Redis was already running, so only this run's PostgreSQL and Mailpit stop.
    supervisor.started = [c["containers"][0]["id"], c["containers"][2]["id"]]
    calls = []
    def cli(*args):
        calls.append(args)
        return json.dumps(dict(Running=False, ExitCode=0)) if args[0] == "inspect" else ""
    monkeypatch.setattr(supervisor, "cli", cli)
    monkeypatch.setattr(supervisor, "save", lambda *_: None)
    supervisor.stop()
    stopped = [args[-1] for args in calls if args[0] == "stop"]
    assert stopped == list(reversed(supervisor.started))
    assert all("--timeout=-1" in args and "SIGTERM" in args for args in calls if args[0] == "stop")


def test_environment_does_not_inherit_admin_preview(monkeypatch):
    monkeypatch.setenv("ENABLE_DRAFT_LEARNING_PREVIEW", "true")
    env = local.environment({**configuration(), "enable_speech": False})
    assert env["ENABLE_DRAFT_LEARNING_PREVIEW"] == "false"
    assert env["ENABLE_PERSONAL_LEARNING_PREVIEW"] == "false"
    assert env["PERSONAL_PREVIEW_USER_IDS"] == "[]"
    assert env["DATABASE_URL"].endswith("/disposable")
    assert "127.0.0.1" in env["FRONTEND_ORIGIN"]


def test_owned_uvicorn_stop_runs_lifespan_without_database(tmp_path):
    (tmp_path / "disposable_app.py").write_text(
        "from fastapi import FastAPI\nfrom contextlib import asynccontextmanager\n"
        "from pathlib import Path\nimport os\n"
        "@asynccontextmanager\nasync def lifespan(app):\n    yield\n"
        "    Path(os.environ['EXIT_EVIDENCE']).write_text('graceful')\n"
        "app=FastAPI(lifespan=lifespan)\n@app.get('/')\ndef ready(): return {'ok': True}\n")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    stop = tmp_path / "owned.stop"
    evidence = tmp_path / "exit.txt"
    env = {**os.environ, "PYTHONPATH": str(tmp_path), "EXIT_EVIDENCE": str(evidence), "PYTHONDONTWRITEBYTECODE": "1"}
    child = subprocess.Popen([sys.executable, "-B", str(ROOT / "scripts/personal_uvicorn.py"),
                              "disposable_app:app", str(port), str(stop)], env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        local.wait_for(lambda: json.loads(urlopen(f"http://127.0.0.1:{port}", timeout=1).read())["ok"],
                       seconds=20, children=[child])
    finally:
        stop.touch()
        child.wait(timeout=20)
    assert child.returncode == 0
    assert evidence.read_text() == "graceful"


@pytest.mark.skipif(not shutil.which("node"), reason="Existing Node required, no installation")
def test_next_wrapper_requests_in_process_graceful_cleanup():
    # Executes the real wrapper with a fake pinned server, without Next compilation.
    harness = r"""
const vm = require('node:vm'), fs = require('node:fs');
let emitted = 0;
const fakeProcess = {env:{}, argv:['node','wrapper','3999','stop'], listenerCount:()=>1,
 emit:(event,signal)=>{if(event==='SIGTERM' && signal==='SIGTERM') emitted++}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'), {
 __dirname:require('node:path').dirname(process.argv[1]), console, process:fakeProcess,
 require:(name)=>name==='node:fs'?{existsSync:()=>true}:name==='node:path'?require(name):
 {startServer:async(options)=>{if(options.hostname!=='127.0.0.1'||options.allowRetry!==false) throw Error('unsafe');
 if(fakeProcess.env.TURBOPACK!=='1'||fakeProcess.env.__NEXT_DEV_SERVER!=='1') throw Error('wrong dev bundler')}},
 setInterval:(fn)=>{fn();fn(); if(emitted!==1) throw Error('not graceful or duplicated'); console.log('graceful')}
});
"""
    result = subprocess.run([shutil.which("node"), "-e", harness, str(ROOT / "scripts/personal_next.cjs")],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert "graceful" in result.stdout


@pytest.mark.skipif(not shutil.which("node"), reason="Existing Node required, no installation")
def test_pinned_next_shutdown_on_disposable_project(tmp_path):
    """Actual pinned Next initialization/shutdown, no protected frontend or build."""
    frontend = tmp_path / "frontend"
    (frontend / "app").mkdir(parents=True)
    (frontend / "package.json").write_text('{"private":true}')
    (frontend / "app/page.js").write_text("export default function Page() { return 'Disposable'; }")
    (frontend / "app/layout.js").write_text("export default function Layout({children}) { return children; }")
    # A test-only VM maps the fixed wrapper's frontend to this disposable folder,
    # but delegates startup and graceful cleanup to the real installed Next code.
    harness = r"""
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const [wrapper,fixture,server,port,stop]=process.argv.slice(1);
process.argv=['node',wrapper,port,stop];
vm.runInThisContext('(function(require,__dirname){'+fs.readFileSync(wrapper,'utf8')+'\n})')(
 name=>name.endsWith('/next/dist/server/lib/start-server')||name.endsWith('\\next\\dist\\server\\lib\\start-server')?
 require(server):require(name),path.join(fixture,'scripts'));
"""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    stop = tmp_path / "next.stop"
    env = {**os.environ, "NODE_ENV": "development", "NEXT_TELEMETRY_DISABLED": "1"}
    env.pop("NEXT_MANUAL_SIG_HANDLE", None)
    with (tmp_path / "next.log").open("wb") as log:
        child = subprocess.Popen([shutil.which("node"), "-e", harness,
            str(ROOT / "scripts/personal_next.cjs"), str(tmp_path),
            str(ROOT / "frontend/node_modules/next/dist/server/lib/start-server"), str(port), str(stop)],
            env=env, stdout=log, stderr=log)
        def listening():
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        try:
            try:
                local.wait_for(listening, seconds=30, children=[child])
            except local.Refused as exc:
                # Preserve the actual startup error in CI instead of losing it
                # behind the supervisor's deliberately generic private-log hint.
                pytest.fail(f"{exc}\n{(tmp_path / 'next.log').read_text(errors='replace')}")
        finally:
            stop.touch()
            child.wait(timeout=60)
    assert child.returncode == 143, (tmp_path / "next.log").read_text(errors="replace")
