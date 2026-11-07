# TTSAudio8Model: Docker on a deployment machine

Run Audio8-TTS-Realistic-Air text to speech with voice cloning on an NVIDIA GPU (1.2 GiB loaded, 2.5 GiB peak) on a separate always-on machine (default `lex@scutiserver1.local`, folder
`/media/ZimaOS-HD/Apps/TTSAudio8Model`). Callers reach it over the published port.

## Requirements on the machine

- Docker + Compose v2, and ssh access (root over ssh is refused; use the normal user).
- Linux with an NVIDIA GPU, the NVIDIA driver and the NVIDIA Container Toolkit. Check it: `docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi`.
- This service does not belong on a box without a GPU. The default Deploy target (`lex@scutiserver1.local`, ZimaOS) has none, so point `DEPLOY_HOST` and `DEPLOY_DIR` at the GPU machine (see step 1).

## 1. Publish the code (from your PC)

Run `TTSAudio8Model\run.bat` and choose **Deploy** (or `run.bat deploy`). Menu:

| Option | Does |
|---|---|
| 1 | Publish code to the `live` branch |
| 2 | Copy your `.env` to the server (one ssh/tar session, one password prompt) |
| 3 | Both |
| 4, 5 | Dry runs of 1 and 2 |
| 6 | chown helper, if option 2 says `Permission denied` |
| R | Release: publish, then tag `VERSION` |

Keep your own target in the git-ignored `tools\deploy.local.ini` (copy `tools\deploy.local.example.ini`), or set
`DEPLOY_HOST`, `DEPLOY_DIR` and `DEPLOY_WEB_PORT` before running. Commit `main` first: publish reads committed `main`.

## 2. First-time setup on the machine

```bash
mkdir -p /media/ZimaOS-HD/Apps
git clone -b live <your-repo-url> /media/ZimaOS-HD/Apps/TTSAudio8Model
cd /media/ZimaOS-HD/Apps/TTSAudio8Model
```
Create `.env` (deploy option 2 copies yours, or `cp .env.example .env` and edit):
- `AUDIO8_ADMIN_PASSWORD`: a real password.
- `AUDIO8_REPLICAS=1` unless you have the memory for more.
- `AUDIO8_PORT=9200` (published on all interfaces; firewall it if the LAN should not reach it, or bind it to
  `127.0.0.1` in the `ports:` line of `audio8_lb` when only callers on the machine need it).

## 3. Start

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:9200/health
```
The first start downloads about 2.5 GB of weights into the `models` volume; `audio8_lb` waits for a healthy service
(up to 300 s grace).

## 4. Connect callers

1. Open `http://<machine-ip>:9200/admin/`, sign in with the admin password and create one token per caller
   (see [guide-web-ui.md](guide-web-ui.md)).
2. The caller holds the URL and token:
   - Caller on another machine: `http://<machine-ip>:9200`.
   - Caller in a Docker stack on the same machine: `http://host.docker.internal:9200`.
3. Try a call from the machine:
   ```bash
   curl -X POST http://127.0.0.1:9200/v1/speak -H "Content-Type: application/json" -H "X-Internal-Token: audio8_..." -d '{"text":"Hello from the model service."}' -o hello.wav
   ```

## Scaling

```bash
AUDIO8_REPLICAS=3 docker compose up -d --build
docker compose restart audio8_lb
```

The restart is needed because nginx resolves replica addresses once at start.

## Updating

```bash
cd /media/ZimaOS-HD/Apps/TTSAudio8Model
git pull
docker compose up -d --build
docker compose restart audio8_lb
```

## Releasing

A plain publish (`run.bat`, Deploy, option 1) only updates the `live` branch. For a release set `VERSION` (and
`pyproject.toml` to the same number), commit, then run `run.bat`, Deploy, option R or
`py tools\publish_live.py --release`. `run.bat`, Build the release ZIP, then builds `_zip_versions\TTSAudio8Model-<VERSION>.zip`.

## Problems

| Symptom | Fix |
|---|---|
| Caller cannot reach the service | Check the caller's URL and token, and that `curl http://<machine-ip>:9200/health` works. |
| nginx 502 after an update | `docker compose restart audio8_lb`. |
| Permission denied on push | run.bat Deploy option 6. |
| Port 9200 in use | Another stack on the machine already publishes it. |
| 503 `no GPU is visible here` | Install the NVIDIA Container Toolkit and restart Docker, then re-run the `nvidia-smi` check. |
