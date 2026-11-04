# Faster-Whisper setup (PowerShell)

The current local main/preview deployment selects **Base**, CPU int8, after the [human-introduction comparison](../verification/VOICE_CONVERSATION_REFINEMENT.md). Tiny remains the compatible default when no model is explicitly selected; existing `asr/` installations continue to work. Base uses separate `asr-base/` weights. Provision it explicitly, then set `SPEECH_ASR_MODEL=base` in the local `.env` and recreate the speech workers. Missing Base weights return unavailable; there is no silent model fallback.

```powershell
$env:PYTHONPATH = 'backend'
.\.venv-speech\Scripts\python.exe -m app.speech.provision_models --destination .speech-models --download-compact-models --asr-model base
# Set SPEECH_ASR_MODEL=base in .env before running the deployment commands below.
```

Base weights are approximately 145 MB; the exact revision/hashes are recorded in `manifest-base.json`. Beam size 3, automatic language checking, VAD, uncertainty and silence safeguards are unchanged. The comparison found name/spelling errors even with Base, so learner review remains necessary.

The measured initial model is **Systran/faster-whisper-tiny**, multilingual, CPU `int8`, two CPU threads. The repository is a CTranslate2 conversion of Whisper tiny and publishes MIT licensing; see the [model card](https://huggingface.co/Systran/faster-whisper-tiny) and [Faster-Whisper implementation](https://github.com/SYSTRAN/faster-whisper). CPU was selected for the 16-GB laptop with approximately 2–3 GB free RAM during inspection; the RTX 3050 has only 4 GB VRAM and is also used by Ollama. No GPU ASR benchmark is claimed.

One-time provisioning downloads only the selected compact ASR weights (approximately 75 MB) and French voice (approximately 63 MB), plus small configuration files. It records exact upstream commit revisions and SHA-256 file hashes in `.speech-models/manifest.json`. Runtime loads only local files, never downloads a model and never falls back to an unapproved model. Larger models require an explicit resource/quality decision and separately provisioned compatible files.

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory
Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
.\.venv312\Scripts\python.exe -m venv .venv-speech
.\.venv-speech\Scripts\python.exe -m pip install -r backend/requirements-speech.txt
$env:PYTHONPATH = 'backend'
.\.venv-speech\Scripts\python.exe -m app.speech.provision_models --destination .speech-models --download-compact-models
```

Do not rerun provisioning on every startup. Keep the manifest and voice attribution with the models. `.speech-models`, `.speech-data` and `.venv-speech` are private/local and Git-ignored. The optional worker pins Faster-Whisper 1.2.1, PyAV 19.0.2, CTranslate2 4.8.4, numpy 2.5.4 and ONNX Runtime 1.31.1, with Piper 1.8.0. PyAV's wheel contains the decoding libraries; no filename-controlled ffmpeg shell command is used.

The default policy accepts usable detected French, uses VAD/word timestamps, rejects strong non-French detection and marks constrained hypotheses uncertain. Low-confidence non-French predictions (below 0.8) can be reviewed regardless of total recording length. VAD-empty noise returns no speech. The human “bonjour” fixture initially looked Russian to tiny's language identifier; the constrained hypothesis correctly returned Bonjour but remains uncertain and is not sent to AI. Tiny also misrecognized part of a longer synthetic phrase. These observations demonstrate why recognition is shown as an editable-by-text fallback experience and not a claim of phonetic accuracy. See the [recognition fix investigation](../verification/SPEECH_RECOGNITION_FIX.md) for measured comparisons and browser retest steps.

CPU is the verified deployment path. Optional `SPEECH_ASR_DEVICE=cuda` and a compatible compute type require compatible CTranslate2/CUDA/cuDNN libraries, explicit GPU access and sufficient VRAM; the provided slim image does not claim a verified GPU configuration. Missing files, unsupported configuration, busy slots and timeouts return controlled unavailable responses. Do not solve model errors by downloading unrelated models automatically.

Main/preview deployment commands (after generating separate random `.env` keys `SPEECH_WORKER_TOKEN` and `PREVIEW_SPEECH_WORKER_TOKEN`):

```powershell
$dockerPath = 'C:\Users\Shyam\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
& $dockerPath compose --profile speech config --quiet
& $dockerPath compose --profile speech build backend frontend speech-worker
& $dockerPath compose --profile speech up -d speech-worker
& $dockerPath compose --profile speech up -d --no-deps backend frontend
& $dockerPath compose -p fluentloop-preview -f docker-compose.preview.yml --profile speech build preview-backend preview-frontend preview-speech-worker
& $dockerPath compose -p fluentloop-preview -f docker-compose.preview.yml up -d preview-db preview-redis preview-mailpit
& $dockerPath compose -p fluentloop-preview -f docker-compose.preview.yml --profile speech up -d preview-speech-worker
& $dockerPath compose -p fluentloop-preview -f docker-compose.preview.yml up -d --no-deps preview-backend preview-frontend
& $dockerPath compose --profile speech ps
& $dockerPath compose -p fluentloop-preview -f docker-compose.preview.yml --profile speech ps
```

Both workers run on separate internal networks, with no published port. Model files are read-only and backend audio volumes are separate. Without the profile, speech is unavailable while normal text features continue. Never run `down -v`. Health is `/api/v1/speech/health` with the normal authenticated browser session; core readiness does not require a speech model.

For isolated live tests only, start the worker on loopback in a separate PowerShell terminal:

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
$env:PYTHONPATH = 'backend'
$env:SPEECH_MODEL_PATH = (Join-Path (Get-Location) '.speech-models')
$env:SPEECH_WORKER_TOKEN = 'isolated-speech-test-key'
$env:OMP_NUM_THREADS = '2'
$env:OPENBLAS_NUM_THREADS = '2'
.\.venv-speech\Scripts\python.exe -m uvicorn app.speech.worker:app --host 127.0.0.1 --port 8095
```

That test key is not the main/preview worker credential and must never be used for deployment. Provision a new isolated PostgreSQL database, then:

```powershell
& $dockerPath compose exec -T db createdb -U fluentloop fluentloop_m06_verify
Push-Location backend
$env:DATABASE_URL = 'postgresql+psycopg://fluentloop:REPLACE_WITH_DATABASE_PASSWORD@127.0.0.1:5432/fluentloop_m06_verify'
..\.venv312\Scripts\python.exe -m alembic upgrade head
..\.venv312\Scripts\python.exe -m pytest tests -ra
..\.venv-speech\Scripts\python.exe -m pytest tests/test_speech_decode.py -ra
$env:SPEECH_TEST_DATABASE_URL = $env:DATABASE_URL
$env:SPEECH_LIVE = '1'
..\.venv312\Scripts\python.exe -m pytest tests/test_speech_postgres.py -ra -s
Pop-Location
```

If the dedicated test database already exists, omit `createdb`; do not recreate it. Adjust the repository's default local credentials if customized. Unit tests do not require model downloads or native speech packages in the core backend environment.
