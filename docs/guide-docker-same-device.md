# TTSAudio8Model: Docker Desktop on this PC

Run Audio8-TTS-Realistic-Air text to speech with voice cloning on an NVIDIA GPU (1.2 GiB loaded, 2.5 GiB peak) in Docker Desktop on the machine you work on, so other programs on it can call it.

## Requirements

- Docker Desktop with Compose v2 (Windows: WSL2 backend).
- An NVIDIA GPU with a current driver, and GPU support in Docker Desktop. Check it: `docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi` must print your card.
- Network access on the first start to download about 2.5 GB from Hugging Face into the `models` volume.
- GPU memory per replica: about 1.2 GiB loaded and up to 2.5 GiB while speaking long text (measured), so a 6 GB card holds one replica comfortably. The weights are about 2.5 GB on disk; the image is 17.6 GB.
- This service does not belong on a box without a GPU (ZimaOS here). Run it on the GPU PC and let other machines call it over the LAN or Tailscale.

## Steps

1. Configure. In `TTSAudio8Model/`:
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

## Settings

In `.env` next to `docker-compose.yml`:

| Variable | Default | Effect |
|---|---|---|
| `AUDIO8_REPLICAS` | `1` | Number of `audio8` containers. Read by Compose. |
| `AUDIO8_PORT` | `9200` | Host port `audio8_lb` publishes. |
| `AUDIO8_ADMIN_PASSWORD` | empty | Password for `/admin/`. When set, every call except `/health` must send a token as `X-Internal-Token`. Empty = no auth. |
| `AUDIO8_NUM_THREAD` | torch decides | Starting value for the CPU threads card (it only serves what runs on the CPU, such as reading the reference clip); a value saved on `/admin/` wins. Use the number of physical cores, not logical CPUs. |

On the **Settings** card of `/admin/` (saved in `settings.json` beside the tokens, shared by all replicas; a saved
value beats the environment variable named in brackets): update check hours (`AUDIO8_UPDATE_CHECK_HOURS`, 6),
in-flight cap (`AUDIO8_MAX_INFLIGHT`, 0 = 4), answers kept per replica (`AUDIO8_CACHE_SIZE`, 32, 0 = off; seeded calls only, at most 1 MB each), model revision (`AUDIO8_MODEL_REVISION`, restart; the pinned Hub commit), device (`AUDIO8_DEVICE`, restart, `cuda`), data type (`AUDIO8_DTYPE`, restart, `bfloat16`; the CPU needs `float32`), most audio tokens per piece (`AUDIO8_MAX_NEW_TOKENS`, restart, 1024) and load at start (`AUDIO8_WARM`, restart). Compose does not pass these;
add the variable under `environment:` of `audio8` to use one as a starting value.

## Daily use

```bash
docker compose ps          # state
docker compose logs -f audio8
docker compose down        # stop (the weights volume is kept)
docker compose up -d --build && docker compose restart audio8_lb   # after a code change
```

## Time it

Try it and time it:

```bash
python tools/bench.py http://127.0.0.1:9200 --save out
```

## Problems

| Symptom | Fix |
|---|---|
| `address already in use` on 9200 | Another copy (`run.bat`, or the same stack on another compose project) is running. Stop it or change `AUDIO8_PORT`. |
| `/health` shows `ready: false` for minutes | First start: the weights are downloading or loading. Check `docker compose logs -f audio8`. |
| 401 Invalid token | The caller's token is missing or revoked; make one on `/admin/`. |
| 503 `no GPU is visible here` | The container has no GPU. Enable GPU support in Docker Desktop and re-run the `nvidia-smi` check above. |
| Container restarts in a loop | Out of GPU memory. Close other GPU programs. |
| `audio8_lb` never starts | No replica is healthy yet (first download, or out of memory). `docker compose logs audio8`. |
| Replicas restart in a loop | Out of GPU memory. Lower `AUDIO8_REPLICAS`, or check `docker compose logs audio8` for `no GPU is visible`. |
| 403 "may not use voice" | The token's list on `/admin/` does not include that voice (or `none`, when `voice` is left out). |
| 404 on `/v1/speak` | The voice is not served here. `GET /v1/voices` lists them. |
| 422 on `format` or another field | Only `text`, `voice`, `seed`, `temperature` and `stream` exist; the reply is always WAV. |
| 429 | Over the token's rate limit, or too many calls waiting for the model. |
| nginx 502 after scaling | `audio8_lb` not restarted after the replica count changed. |
