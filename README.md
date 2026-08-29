# LongForge backend

## Requirements
- Python 3.10+
- FFmpeg installed and available as `ffmpeg`
- Internet access from the server (for AI image generation and TTS)

## Start
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open `frontend/index.html` and keep Backend URL as `http://localhost:8000`.

## What this does
Title + topic + script + category + language + duration are sent to the backend.
The backend creates topic/script-specific AI image prompts, generates images, creates narration with Edge TTS, combines scenes with FFmpeg, and returns an MP4.

## Important
This is a real backend pipeline, not a canvas fake-video generator. It still needs the server to have Python, FFmpeg and internet access. Pollinations and Edge TTS are third-party services and can change availability/rate limits. For production, replace them with paid or self-hosted providers and add authentication/queue storage.
