# LongForge backend — deploy this publicly

The screenshot error `Failed to fetch` happens because the GitHub Pages frontend is trying to call `http://localhost:8000`. A GitHub Pages website cannot use your phone's localhost as its production backend.

Deploy this `backend` folder to any service that supports Docker (for example Render, Railway, Fly.io, a VPS, etc.). After deployment, copy the public **HTTPS** URL and paste it into the frontend's **DEPLOYED BACKEND URL** field.

Health test:
`https://YOUR-BACKEND/health`

It should return JSON like:
`{"ok":true,"service":"LongForge Real Video Backend"}`

Then Generate Real Video.

The backend needs internet access, FFmpeg and enough CPU/disk for rendering. The demo AI image provider and Edge TTS are external services; for production, use your own AI provider/API keys and persistent job storage.
