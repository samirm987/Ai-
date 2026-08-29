# TextForge — REAL Text → Video

This is a real backend-backed video generator, not a fake progress-bar demo.

## What it does

1. User enters **Title + Topic + full Script**.
2. Selects category, language, 1–20 minute duration, visual style, aspect ratio and clip length.
3. Backend breaks the supplied script into scenes.
4. Backend calls **Runway Dev** for real text-to-video clips.
5. Backend downloads each generated clip.
6. FFmpeg stitches the clips into one MP4.
7. Browser shows the actual MP4 and download button.

## Important

A 10–20 minute video is assembled from many short AI clips. It can take a long time and consume API credits. The Runway API currently generates video in short durations; the long-form result is therefore assembled from multiple scenes.

## Setup (Windows / Linux / macOS)

Install Python 3.10+ and FFmpeg.

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Install:
```bash
pip install -r requirements.txt
```

Set your Runway secret on the SERVER:

Windows PowerShell:
```powershell
$env:RUNWAYML_API_SECRET="YOUR_RUNWAY_KEY"
```

macOS/Linux:
```bash
export RUNWAYML_API_SECRET="YOUR_RUNWAY_KEY"
```

Run:
```bash
uvicorn backend:app --host 0.0.0.0 --port 8000
```

Open:
`http://127.0.0.1:8000`

## Deploying

For a public website, deploy the Python backend to a server/VPS/cloud service that supports long-running processes and FFmpeg. Keep `RUNWAYML_API_SECRET` in the host's secret/environment-variable settings. Do NOT put the production key into GitHub or public HTML.

## Why the previous version showed "Failed to fetch"

The browser was trying to call `localhost`, but the backend was not running on the same device. This version keeps the API call on the backend and serves the UI from the same application.

## Limitation

This package intentionally does not claim that an HTML page can create a real MP4 by itself. Real generation requires a configured video provider and server-side processing.
