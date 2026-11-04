# Local Ollama setup and verification (Windows PowerShell)

The verified deployment uses existing Windows-host Ollama **0.40.13**, model **llama3.2:3b**, 3.2B parameters, Q4_K_M, approximately 2.02 GB on disk. Its tag was returned by `/api/tags`; nothing was downloaded. The laptop reports about 16 GB RAM and an RTX 3050 laptop GPU with 4 GB VRAM. Available memory changes with other apps; these observations are not performance guarantees. Larger installed models (`qwen3:latest`, `llama3.1:8b`) were not loaded for this implementation. The code does not require this particular model name.

Inspect resources and existing models before choosing or downloading anything:

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory
Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
Invoke-RestMethod http://127.0.0.1:11434/api/version
(Invoke-RestMethod http://127.0.0.1:11434/api/tags).models | Select-Object name,size,details
Invoke-RestMethod http://127.0.0.1:11434/api/ps
```

If Ollama is absent, install it from its official distribution using your normal software-installation process. Explicitly approve model storage/RAM implications before running `ollama pull <chosen-model>`. No install or pull occurs automatically. A compact multilingual instruct model is the intended starting point; validate French tutoring and correction behavior rather than relying on model size or a coding-model label. The optional container's internal-only network intentionally cannot download a model itself; provision approved model files separately or temporarily use a controlled provisioning network, then restore the internal-only configuration.

This workspace's `.env` is configured for the verified Windows host:

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b
PREVIEW_OLLAMA_BASE_URL=http://host.docker.internal:11434
PREVIEW_OLLAMA_MODEL=llama3.2:3b
AI_REQUEST_TIMEOUT_SECONDS=60
AI_MAX_OUTPUT_TOKENS=600
AI_MAX_INPUT_CHARACTERS=4000
AI_MAX_CONCURRENT_REQUESTS=1
```

The URL is server-side only. `host.docker.internal` was tested from the running Docker Desktop backend. It is not assumed available on other systems. A locally executed Python backend instead needs `OLLAMA_BASE_URL=http://127.0.0.1:11434`. Do not expose port 11434 on a public interface. Restrict any host listener/firewall access to loopback and trusted Docker traffic; an HTTP test verifies reachability, not every Windows firewall rule.

The Docker CLI on this laptop is outside PATH. Exact commands from the project root:

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI'
$dockerPath = 'C:\Users\Shyam\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
& $dockerPath compose config --quiet
& $dockerPath compose build backend frontend
& $dockerPath compose up -d --no-deps backend frontend
& $dockerPath compose -p fluentloop-preview -f docker-compose.preview.yml build preview-backend preview-frontend
& $dockerPath compose -p fluentloop-preview -f docker-compose.preview.yml up -d --no-deps preview-backend preview-frontend
& $dockerPath compose ps
& $dockerPath compose -p fluentloop-preview -f docker-compose.preview.yml ps
& $dockerPath compose exec -T backend alembic current
& $dockerPath compose exec -T backend python -c "from app.ai.providers.ollama_provider import get_provider; print(get_provider().health())"
& $dockerPath compose -p fluentloop-preview -f docker-compose.preview.yml exec -T preview-backend python -c "from app.ai.providers.ollama_provider import get_provider; print(get_provider().health())"
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health/ready
```

For a different deployment, the optional `ai` Compose profile supplies an Ollama service on an internal network with no published port and a separate model volume. Set `OLLAMA_BASE_URL=http://ollama:11434` and the approved installed tag. `docker compose --profile ai up -d ollama` starts the service only; it does not provision model weights. This alternative container profile was configuration-validated but not launched in the measured host-based setup. Never use `down -v` to troubleshoot this project.

The adapter checks `/api/tags` for the exact configured model before generation. An empty/missing model or unsupported provider returns unavailable; there is no silent fallback. Connection failure, timeout, malformed output or exhausted generation capacity return controlled 503. Stop unnecessary workloads, reduce output tokens, or explicitly select a smaller approved installed model if resources are tight. Do not use the embedding-only `nomic-embed-text` model for tutoring.

Backend and genuine model verification uses dedicated databases, never main/preview:

```powershell
& $dockerPath compose exec -T db createdb -U fluentloop fluentloop_m05_verify
Push-Location backend
$env:DATABASE_URL = 'postgresql+psycopg://fluentloop:REPLACE_WITH_DATABASE_PASSWORD@127.0.0.1:5432/fluentloop_m05_verify'
..\.venv312\Scripts\python.exe -m alembic upgrade head
..\.venv312\Scripts\python.exe -m pytest tests -ra
$env:AI_TEST_DATABASE_URL = $env:DATABASE_URL
..\.venv312\Scripts\python.exe -m pytest tests/test_ai_postgres.py -ra
$env:AI_LIVE_OLLAMA = '1'
..\.venv312\Scripts\python.exe -m pytest tests/test_ai_postgres.py -ra -s
$env:PYTHONPATH = '.'
..\.venv312\Scripts\python.exe scripts/ollama_smoke.py
Remove-Item Env:AI_LIVE_OLLAMA
# This next script intentionally discards ONLY AI test tables on rollback:
..\.venv312\Scripts\python.exe scripts/verify_ai_migration.py
Pop-Location
```

If the isolated database already exists, omit `createdb`; do not drop it. Replace the default local development database credentials if customized. The migration script refuses database names outside `fluentloop_m05_*`, compares all pre-M05 row counts and hashes, and must never be used against an application database.

Frontend checks and deterministic UI tests:

```powershell
Push-Location frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
$env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:3015'
Remove-Item Env:PLAYWRIGHT_API_BASE_URL -ErrorAction SilentlyContinue
npm.cmd exec -- playwright test e2e/ai-tutor.spec.ts --workers=1
Pop-Location
```

Real browser → FastAPI → PostgreSQL checks use a guarded test server with fake inference. In a separate PowerShell window:

```powershell
Set-Location 'D:\shyam\Projects\FluentLoop AI\backend'
$env:DATABASE_URL = 'postgresql+psycopg://fluentloop:REPLACE_WITH_DATABASE_PASSWORD@127.0.0.1:5432/fluentloop_m05_verify'
$env:APP_ENV = 'development'
$env:ENABLE_DRAFT_LEARNING_PREVIEW = 'true'
$env:FRONTEND_ORIGIN = 'http://127.0.0.1:3015'
$env:CORS_ORIGINS = '["http://127.0.0.1:3015"]'
$env:AI_E2E_TEST_SERVER = '1'
$env:SMTP_HOST = '127.0.0.1'
$env:SMTP_PORT = '1025'
..\.venv312\Scripts\python.exe -m uvicorn scripts.ai_e2e_server:app --host 127.0.0.1 --port 8015
```

Then in the frontend window:

```powershell
Push-Location frontend
$env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:3015'
$env:PLAYWRIGHT_API_BASE_URL = 'http://127.0.0.1:8015/api/v1'
$env:AI_E2E_REAL_API = '1'
npm.cmd exec -- playwright test e2e/ai-api.spec.ts --workers=1
Pop-Location
```

Stop only that test server with Ctrl+C. Its seeded credentials are test-only and restricted to the dedicated database. Browser API mocking, real PostgreSQL tests and genuine Ollama checks are separate evidence categories. The production health endpoint requires authentication and can also be inspected after signing into `/ai-tutor`.
