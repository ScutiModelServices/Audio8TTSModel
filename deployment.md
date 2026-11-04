# Deploying TTSAudio8Model

TTSAudio8Model is one HTTP service (port 9200). It runs as `audio8` replicas behind an nginx load balancer,
`audio8_lb`. Callers use `http://<host>:9200`; they never reach a replica directly.

## Requirements

- Docker with Compose v2 and an NVIDIA GPU with the NVIDIA Container Toolkit. On Windows: Docker Desktop with the WSL2 backend and GPU support (check with `docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi`).
- GPU memory per replica: about 1.2 GiB loaded and up to 2.5 GiB while speaking long text (measured), so a 6 GB card holds one replica comfortably. The weights are about 2.5 GB on disk; the image is 17.6 GB.
- Network access on the first start to download about 2.5 GB from Hugging Face into the `models` volume.
- This service does not belong on a box without a GPU (ZimaOS here). Run it on the GPU PC and let other machines call it over the LAN or Tailscale.

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

## Start

```bash
docker compose up -d --build
curl http://127.0.0.1:9200/health
```

Expect `"ready": true` once a replica has loaded the model. The first start downloads about 2.5 GB into the `models`
volume (about 5 minutes on the first run here, then about 40 s to load), so `audio8_lb` can take a minute to appear (the health check allows 300 s before failures count; run
`docker compose ps` and wait).

Try it and time it:

```bash
python tools/bench.py http://127.0.0.1:9200 --save out
```

## Scaling

```bash
AUDIO8_REPLICAS=3 docker compose up -d --build
docker compose restart audio8_lb
```

The restart is needed because nginx resolves replica addresses once at start.

## Updating the files

The model revision is pinned, so the **Updates** card only reports a missing download. To move to a newer commit, read its code (the model runs it), change the *Model revision* setting, restart, then press **Download new weights**.
That button fetches them into the models volume; every replica drops its old copy within a few seconds and loads the
new one on its next request. Updating the service itself: `docker compose up -d --build`, then
`docker compose restart audio8_lb`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `audio8_lb` never starts | No replica is healthy yet (first download, or out of memory). `docker compose logs audio8`. |
| Replicas restart in a loop | Out of GPU memory. Lower `AUDIO8_REPLICAS`, or check `docker compose logs audio8` for `no GPU is visible`. |
| 401 "Invalid token" | The caller sends no token, or a revoked one. |
| 403 "may not use voice" | The token's list on `/admin/` does not include that voice (or `none`, when `voice` is left out). |
| 404 on `/v1/speak` | The voice is not served here. `GET /v1/voices` lists them. |
| 422 on `format` or another field | Only `text`, `voice`, `seed`, `temperature` and `stream` exist; the reply is always WAV. |
| 503 `no GPU is visible here` | The container has no GPU: install the NVIDIA Container Toolkit, or enable GPU support in Docker Desktop. |
| 429 | Over the token's rate limit, or too many calls waiting for the model. |
| nginx 502 after scaling | `audio8_lb` not restarted after the replica count changed. |

## Releasing

A plain publish (`tools\deploy.bat` option 1) only updates the `live` branch. For a release set `VERSION` (and
`pyproject.toml` to the same number), commit, then run `tools\deploy.bat` option R or
`py tools\publish_live.py --release`. `tools\make_zip.bat` then builds `zip_versions\TTSAudio8Model-<VERSION>.zip`.
