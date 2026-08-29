TEXTFORGE AI — VEED-STYLE TEXT-TO-VIDEO FRONTEND

This is a polished, mobile-friendly single HTML frontend focused ONLY on text-to-video.

IMPORTANT:
A browser HTML file cannot magically create a real 9–20 minute AI video. Real AI video generation requires an AI video provider/API and a server-side endpoint. The previous "Failed to fetch" problem happened because the frontend tried to contact localhost.

HOW THIS VERSION WORKS:
1. Deploy your own AI-video backend/API.
2. Put its HTTPS /generate endpoint into "AI VIDEO API ENDPOINT".
3. The frontend sends:
   - prompt/script
   - category
   - language
   - duration (1–20 minutes)
   - aspect ratio
   - visual style
   - voice
4. Your backend should return either:
   {"video_url":"https://.../video.mp4"}
   OR
   {"job_id":"abc123"}
   and then expose:
   GET /jobs/abc123
   -> {"status":"processing","progress":40,"message":"..."}
   -> {"status":"done","progress":100,"video_url":"https://..."}

SECURITY:
Do NOT put a production API key in public GitHub HTML. Keep the provider key on your backend and have the backend call the AI video service.

This package intentionally does not fake an AI video. It is the VEED-style text-to-video interface and API client.
