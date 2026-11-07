# TTSAudio8Model: without Docker, on Windows

Run Audio8-TTS-Realistic-Air text to speech with voice cloning on an NVIDIA GPU (1.2 GiB loaded, 2.5 GiB peak) directly with Python: one process, no load balancer, listening on `127.0.0.1:9200`.

## Requirements
- Windows with Python 3.11 or newer and uv (`winget install astral-sh.uv`).
- An NVIDIA GPU with a current driver. The `uv.lock` pins a CUDA build of torch, so no extra CUDA toolkit is needed.
- Internet on the first start (about 2.5 GB of weights).

## Start
Double-click `run.bat`, or run it in a terminal from `TTSAudio8Model\`. Choose **1 Run the service** in the menu, or run `run.bat run` to skip the menu. It runs `uv sync` to create or update `.venv`, then starts
`python src/app.py`. The first start downloads about 2.5 GB of weights.

Linux or macOS:
```bash
cd TTSAudio8Model
uv sync
uv run python src/app.py
```
On macOS there is no NVIDIA GPU, so this service cannot run there.

## Settings
`run.bat` loads `.env` in this folder (copy `.env.example`); a real environment variable wins over it. Set variables in `.env` or in the environment before starting:

| Variable | Default | Effect |
|---|---|---|
| `AUDIO8_HOST` | `127.0.0.1` | Bind address. Use `0.0.0.0` only if other devices must reach it. |
| `AUDIO8_PORT` | `9200` | Port. |
| `AUDIO8_ADMIN_PASSWORD` | empty | Unlocks `/admin/` and requires tokens on every call but `/health`. Empty = no auth. |
| `AUDIO8_WARM` | `1` | Load the model at start; with `0` the first request pays the load time. |
| `AUDIO8_DEVICE` | `cuda` | `cpu` exists for tests only and is far too slow to use. |

PowerShell: `$env:AUDIO8_ADMIN_PASSWORD = "secret"; .\run.bat`
Bash: `AUDIO8_ADMIN_PASSWORD=secret uv run python src/app.py`

## Check
```bash
curl http://127.0.0.1:9200/health
```
`ready` is `false` until the model has loaded. Then open `http://127.0.0.1:9200/admin/` (see [guide-web-ui.md](guide-web-ui.md)),
make a token, and try a call:
```bash
curl -X POST http://127.0.0.1:9200/v1/speak -H "Content-Type: application/json" -H "X-Internal-Token: audio8_..." -d '{"text":"Hello from the model service."}' -o hello.wav
```

## Stop
Ctrl+C in the terminal. Do not run this and the Docker stack together: both use port 9200.

## Tests
`uv run pytest`.
