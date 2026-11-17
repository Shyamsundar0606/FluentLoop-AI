"""Bounded RC workload against the explicitly disposable loopback demo only."""
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
from uuid import uuid4

import httpx
import redis
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session
from rc_test_controls import current_database, ROOT


def distribution(samples):
    samples = sorted(samples)
    return dict(samples=len(samples), p50_ms=round(samples[(len(samples)-1)//2],2),
                p95_ms=round(samples[math.ceil(len(samples)*.95)-1],2), max_ms=round(max(samples),2))


def main():
    options = current_database()  # Validates explicit flag, role, port and active fixture.
    fixture = json.loads((ROOT/".publication-private/m08/m09-manual-fixture.json").read_text())
    url = URL.create("postgresql+psycopg", username=options["user"], password=options["password"],
        host=options["host"], port=options["port"], database=options["dbname"])
    from app.ai.models import Conversation, Message
    from app.models import User
    engine = create_engine(url, pool_size=5, max_overflow=0)
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email==fixture["email"]))
        conversation = Conversation(user_id=user.id, title="Synthetic RC 300-message history", mode="tutor", cefr_level="A1")
        db.add(conversation); db.flush(); history = str(conversation.id)
        db.add_all([Message(conversation_id=conversation.id, role="user" if n%2==0 else "assistant",
                            content="Bonjour, ceci est une conversation fictive.") for n in range(300)])
        db.commit()
    base = "http://127.0.0.1:8012/api/v1"
    headers = {"Origin":"http://127.0.0.1:3012"}
    clients = []
    def login(_):
        client = httpx.Client(base_url=base, headers=headers, timeout=90)
        before=time.perf_counter(); response=client.post("/auth/login",json=dict(email=fixture["email"],password=fixture["password"]))
        assert response.status_code==200, response.status_code
        client.headers["X-CSRF-Token"]=client.cookies.get("fluentloop_m083_csrf")
        clients.append(client)
        return (time.perf_counter()-before)*1000
    report={"concurrency":5,"targets":{"reads_p95_ms":2000,"unexpected_error_rate":0},"read_requests_per_endpoint":20}
    with ThreadPoolExecutor(max_workers=5) as pool:report["concurrent_logins"]=distribution(list(pool.map(login,range(5))))
    client=clients[0]
    log=(ROOT/".publication-private/m08/m08_3_runtime/api.log").read_text()
    process_id=int(re.findall(r"Started server process \[(\d+)\]",log)[-1])
    def resources():
        result=subprocess.check_output(["powershell.exe","-NoProfile","-Command",
            f"Get-Process -Id {process_id} | Select-Object CPU,WorkingSet64,PeakWorkingSet64 | ConvertTo-Json -Compress"],text=True)
        return json.loads(result)
    report["api_resources_before"]=resources(); started=time.perf_counter()
    paths=[("courses","/courses?level=A1"),("grammar","/learning/grammar?level=A1"),
           ("assessments","/learning/assessments"),("progress","/learning/progress"),
           ("large_history",f"/ai/conversations/{history}")]
    for label,path in paths:
        def read(_):
            before=time.perf_counter(); response=client.get(path)
            assert response.status_code==200,(label,response.status_code)
            if label=="large_history":
                assert len(response.json()["messages"])==100 and response.json()["has_more_messages"]
            return (time.perf_counter()-before)*1000
        with ThreadPoolExecutor(max_workers=5) as pool:report[label]=distribution(list(pool.map(read,range(20))))
    report["read_window_seconds"]=round(time.perf_counter()-started,2)
    report["api_resources_after"]=resources()
    report["api_cpu_one_core_pct"]=round((report["api_resources_after"]["CPU"]-report["api_resources_before"]["CPU"])/report["read_window_seconds"]*100,2)
    output=ROOT/".publication-private/integration-wsl/rc-load.json"
    report["complete"]=False
    output.write_text(json.dumps(report,indent=2))
    cache=redis.Redis(host="127.0.0.1",port=56379,password=options["password"],db=13)
    def ping(_):
        before=time.perf_counter(); assert cache.ping(); return (time.perf_counter()-before)*1000
    with ThreadPoolExecutor(max_workers=5) as pool:report["redis_ping"]=distribution(list(pool.map(ping,range(50))))
    report["redis_used_memory_bytes"]=cache.info("memory")["used_memory"]
    with engine.connect() as db:
        report["database_connections"]=db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()")).scalar_one()
    conversations=[client.post("/ai/conversations",json={"mode":"tutor"}).json()["id"] for _ in range(2)]
    def infer(identifier):
        before=time.perf_counter(); response=client.post(f"/ai/conversations/{identifier}/messages",json={"message":"Bonjour, comment allez-vous ?","request_id":str(uuid4())})
        assert response.status_code in (200,429,503),response.status_code
        return dict(status=response.status_code,ms=round((time.perf_counter()-before)*1000,2))
    with ThreadPoolExecutor(max_workers=2) as pool:report["concurrent_ai"]=list(pool.map(infer,conversations))
    assert any(row["status"]==200 for row in report["concurrent_ai"]),"No actual AI generation succeeded"
    worker=json.loads((ROOT/".publication-private/m08/local.json").read_text())
    from app.config import get_settings
    token=worker.get("SPEECH_WORKER_TOKEN") or get_settings().speech_worker_token
    with httpx.Client(base_url="http://127.0.0.1:8098",headers={"X-Speech-Key":token},timeout=90) as speech:
        before=time.perf_counter(); audio=speech.post("/synthesize",json={"text":"Bonjour, je voudrais une baguette, s'il vous plaît."})
        assert audio.status_code==200,audio.status_code
        report["piper_ms"]=round((time.perf_counter()-before)*1000,2)
        before=time.perf_counter(); transcript=speech.post("/transcribe",content=audio.content,headers={"Content-Type":"audio/wav"})
        assert transcript.status_code==200 and transcript.json()["text"].strip(),transcript.status_code
        report["asr_ms"]=round((time.perf_counter()-before)*1000,2)
    report["unexpected_errors"]=0
    report["read_target_passed"]=all(report[label]["p95_ms"]<=2000 for label,_ in paths)
    for item in clients:
        item.post("/auth/logout");item.close()
    cache.close();engine.dispose()
    report["complete"]=True
    output.write_text(json.dumps(report,indent=2));print(json.dumps(report))
    if not report["read_target_passed"]:raise SystemExit("Controlled read-latency target exceeded; investigate the measured path.")


if __name__=="__main__":main()
