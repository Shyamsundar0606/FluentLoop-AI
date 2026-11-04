"""Private optional inference service. Persistent, killable model processes."""

import hmac
import multiprocessing as mp
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from app.config import get_settings
from app.speech.schemas import Synthesize


def child(connection, kind):
    try:
        import resource

        # Linux worker hard memory cap; Docker additionally limits CPU/RAM/PIDs.
        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
    except (ImportError, ValueError, OSError):
        pass
    while True:
        payload = connection.recv()
        try:
            if kind == "asr":
                from app.speech.faster_whisper_provider import transcribe

                result = transcribe(payload)
            else:
                from app.speech.french_tts_provider import synthesize

                result = synthesize(payload)
            connection.send(("ok", result))
        except Exception as exc:
            import av

            connection.send(
                (
                    (
                        "invalid"
                        if isinstance(exc, (ValueError, av.FFmpegError))
                        else "unavailable"
                    ),
                    None,
                )
            )


class ProcessSlot:
    def __init__(self, kind):
        self.kind = kind
        self.lock = threading.Lock()
        self.process = None
        self.pipe = None

    def call(self, payload):
        if not self.lock.acquire(False):
            raise HTTPException(503, "Speech worker busy. Retry later.")
        try:
            if self.process is None or not self.process.is_alive():
                ctx = mp.get_context("spawn")
                parent, remote = ctx.Pipe()
                self.pipe = parent
                self.process = ctx.Process(
                    target=child, args=(remote, self.kind), daemon=True
                )
                self.process.start()
                remote.close()
            self.pipe.send(payload)
            if not self.pipe.poll(get_settings().speech_processing_timeout_seconds):
                self.process.terminate()
                self.process.join(3)
                self.pipe.close()
                self.process = None
                raise HTTPException(503, "Speech processing timed out.")
            status, result = self.pipe.recv()
            if status != "ok":
                raise HTTPException(
                    422 if status == "invalid" else 503,
                    "Audio invalid or speech model unavailable.",
                )
            return result
        except (EOFError, BrokenPipeError, OSError):
            if self.process:
                self.process.terminate()
                self.process.join(2)
            self.process = None
            raise HTTPException(503, "Speech process unavailable.") from None
        finally:
            self.lock.release()


app = FastAPI(docs_url=None, redoc_url=None)
asr = ProcessSlot("asr")
tts = ProcessSlot("tts")


@app.middleware("http")
async def boundary(request, call_next):
    token = get_settings().speech_worker_token
    if not token or not hmac.compare_digest(
        request.headers.get("x-speech-key", ""), token
    ):
        return JSONResponse(status_code=403, content={"detail": "Private service."})
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > get_settings().speech_max_upload_bytes + 10000:
            return JSONResponse(
                status_code=413, content={"detail": "Request too large."}
            )
    request._body = bytes(body)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health():
    from app.speech.faster_whisper_provider import asr_model_path
    root = Path(get_settings().speech_model_path)
    return {
        "asr": (asr_model_path() / "model.bin").is_file(),
        "tts": (root / "tts" / (get_settings().speech_tts_voice + ".onnx")).is_file(),
        "asr_provider": get_settings().speech_asr_provider,
        "tts_provider": get_settings().speech_tts_provider,
    }


@app.post("/transcribe")
async def transcribe_route(request: Request):
    from starlette.concurrency import run_in_threadpool
    from app.speech.audio_validation import validate_upload

    data = await request.body()
    validate_upload(data)
    return await run_in_threadpool(asr.call, data)


@app.post("/synthesize")
def synthesize_route(payload: Synthesize):
    return Response(tts.call(payload.text), media_type="audio/wav")
