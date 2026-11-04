@echo off
REM Starts the audio8 service on port 9200 (syncs .venv with uv on each run). The first start downloads about 2.5 GB of weights. Needs an NVIDIA GPU and a CUDA build of torch.
REM LABEL: Audio8TTS Service
REM DESCRIPTION: Shared HTTP service that runs Audio8-TTS-Realistic-Air text to speech with voice cloning on the GPU for every project.

cd /d "%~dp0"

python -m uv sync
if errorlevel 1 (
    echo uv sync failed. Install uv: python -m pip install uv
    pause
    exit /b 1
)
call .venv\Scripts\activate

python src/app.py
pause
