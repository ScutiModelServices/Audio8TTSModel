# Changelog

## Unreleased

- Untracked folders now start with `.` or `_`: `zip_versions/` is `_zip_versions/`, `voices/` to `_voices/`. A local `voices`, `tem_code` or `zip_versions` folder from an older checkout needs renaming by hand.
- `run.bat` is now a menu (run the service, deploy, build the release ZIP) and `run.bat run|deploy|zip` skips it. `tools/deploy.bat`, `tools/make_zip.bat` and `tools/deploy.local.example.bat` are gone; the local deploy target is `tools/deploy.local.ini` (copy `tools/deploy.local.example.ini`).
- Admin page: **Connect to this service** card with the addresses other services can use (this page's address, same PC, Docker network, `host.docker.internal`) and every endpoint, each with a Copy button.
- Admin **Try it** panel: descriptor-driven public API requests, live text streams, JSON/media output, status and latency, cancellation and redacted curl. Auth choice (b): pasted public token stays in memory; normal scope, limits and caches apply. Shared `web/playground.js` is copied across all model and tool services.

- `run.bat`: runs `uv sync` directly; `python -m uv` failed when uv was installed only as a program (winget).
- Docker: `.dockerignore` keeps `.git`, `.venv`, tests and local state out of the build context (the same file in every model service).
- First version: Audio8-TTS-Realistic-Air (0.6B, 23 languages, zero-shot voice cloning, Apache-2.0) served on the GPU, with the admin page, tokens (scope, rate limit, expiry), metrics, Settings card, update checks and file downloads shared with the other model services.
- `POST /v1/speak` takes `text`, `voice`, `seed`, `temperature` and `stream` and returns a WAV file. `GET /v1/voices` lists the voices; `none` means no reference voice.
- Voices are a reference clip plus its transcript: `PUT /admin/voices/{name}` (admin password) and `DELETE /admin/voices/{name}`, kept in the shared `voices` volume.
- Text over 150 characters is split into pieces before the model sees it; `stream: true` sends the WAV piece by piece.
- Answer cache keeps only calls with a `seed` (`AUDIO8_CACHE_SIZE`, default 32, 0 = off; `X-Cache` header).
- The model revision is pinned to one Hub commit because the model runs remote code (`AUDIO8_MODEL_REVISION`).
- `tools/bench.py` times a service so `TTSPiperModel`, `TTSParadeeModel` and `TTSAudio8Model` can be compared.
