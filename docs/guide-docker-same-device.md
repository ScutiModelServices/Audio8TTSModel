# Audio8TTSModel: Docker Desktop on this PC

Run Audio8-TTS-Realistic-Air text to speech with voice cloning on an NVIDIA GPU (1.2 GiB loaded, 2.5 GiB peak) in Docker Desktop on the machine you work on, so other programs on it can call it.

## Requirements
- Docker Desktop with Compose v2 (Windows: WSL2 backend).
- An NVIDIA GPU with a current driver, and GPU support in Docker Desktop. Check it: `docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi` must print your card.
- Internet on the first start (about 2.5 GB of weights).

## Steps
1. Configure. In `Audio8TTSModel/`:
   ```bash
   cp .env.example .env
   ```
   Set `AUDIO8_ADMIN_PASSWORD` (empty = no auth and no admin page, fine for a local test). Leave `AUDIO8_PORT=9200`. Leave `AUDIO8_REPLICAS=1`.
2. Start:
   ```bash
   docker compose up -d --build
   ```
   The first start downloads about 2.5 GB of weights into the `models` volume. `audio8_lb` starts only after the service is healthy
   (up to 300 s grace). Watch with `docker compose ps` and `docker compose logs -f audio8`.
3. Check:
   ```bash
   curl http://127.0.0.1:9200/health
   ```
   `ready` is `false` until the model has loaded, then `true`.
4. Open the admin page: `http://127.0.0.1:9200/admin/` (see [guide-web-ui.md](guide-web-ui.md)) and make a token for each caller.
5. Try a call:
   ```bash
   curl -X POST http://127.0.0.1:9200/v1/speak -H "Content-Type: application/json" -H "X-Internal-Token: audio8_..." -d '{"text":"Hello from the model service."}' -o hello.wav
   ```
   Expect a WAV file, `hello.wav`.
6. Callers connect to the published port. The caller holds the URL and token:
   - Caller on the host: `http://127.0.0.1:9200`.
   - Caller in another Docker stack on the same host: `http://host.docker.internal:9200`.

## Daily use
```bash
docker compose ps          # state
docker compose logs -f audio8
docker compose down        # stop (the weights volume is kept)
docker compose up -d --build && docker compose restart audio8_lb   # after a code change
```

## Problems
| Symptom | Fix |
|---|---|
| `address already in use` on 9200 | Another copy (`run.bat`, or the same stack on another compose project) is running. Stop it or change `AUDIO8_PORT`. |
| `/health` shows `ready: false` for minutes | First start: the weights are downloading or loading. Check `docker compose logs -f audio8`. |
| 401 Invalid token | The caller's token is missing or revoked; make one on `/admin/`. |
| 503 `no GPU is visible here` | The container has no GPU. Enable GPU support in Docker Desktop and re-run the `nvidia-smi` check above. |
| Container restarts in a loop | Out of GPU memory. Close other GPU programs. |
