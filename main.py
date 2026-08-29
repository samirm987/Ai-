import os, re, uuid, threading, subprocess, textwrap, urllib.parse, urllib.request, json, math
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP=Path(__file__).resolve().parent
ROOT=APP/"jobs"; ROOT.mkdir(exist_ok=True)
app=FastAPI(title="LongForge Real AI Video Backend")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
app.mount("/videos",StaticFiles(directory=str(ROOT)),name="videos")
jobs={}

class Req(BaseModel):
    title:str; topic:str; script:str; category:str="All Other"; language:str="English (USA)"
    duration_seconds:int=600; visual_style:str="Cinematic"; voice:str="Auto"; aspect_ratio:str="16:9"

def split_scenes(script, duration):
    words=re.findall(r'\S+',script)
    # ~10-15 seconds per visual, with a practical cap.
    n=max(6,min(120,math.ceil(duration/12)))
    size=max(1,math.ceil(len(words)/n))
    out=[]
    for i in range(0,len(words),size):
        txt=" ".join(words[i:i+size])
        out.append({"scene":len(out)+1,"narration":txt})
    return out

def safe(s): return re.sub(r'[^A-Za-z0-9_-]+','_',s)[:70]

def make_image(prompt,out):
    # Pollinations is used as a no-key image generation fallback.
    url="https://image.pollinations.ai/prompt/"+urllib.parse.quote(prompt,safe='')
    req=urllib.request.Request(url,headers={"User-Agent":"LongForge/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r:
        out.write_bytes(r.read())

def tts(text,out,voice):
    # Edge TTS is optional. Install edge-tts. If unavailable, backend reports a clear error.
    import asyncio
    import edge_tts
    v=voice
    if v=="Auto": v="en-US-GuyNeural"
    elif "Female" in v: v="en-US-JennyNeural"
    elif "Energetic" in v: v="en-US-GuyNeural"
    else: v="en-US-ChristopherNeural"
    async def run(): await edge_tts.Communicate(text,v).save(str(out))
    asyncio.run(run())

def render(job, req):
    d=Path(job["dir"]); scenes=job["scenes"]
    job["status"]="rendering";job["message"]="Generating AI visuals and voice…";job["progress"]=10
    scene_dirs=[]
    for i,s in enumerate(scenes):
        sd=d/f"s{i+1:03d}";sd.mkdir(exist_ok=True); scene_dirs.append(sd)
        prompt=f"{req.visual_style}, professional high quality video frame, {req.category}, topic: {req.topic}, title: {req.title}. Scene {i+1}. Visualize this narration naturally: {s['narration']}. No text, no subtitles, no logos, no watermark."
        try: make_image(prompt,sd/"image.jpg")
        except Exception as e: raise RuntimeError("AI image generation failed: "+str(e))
        try: tts(s["narration"],sd/"voice.mp3",req.voice)
        except Exception as e: raise RuntimeError("Voice generation failed. Install edge-tts: "+str(e))
        job["progress"]=10+int(55*(i+1)/len(scenes));job["message"]=f"AI scene {i+1}/{len(scenes)} ready"
    # Build concat file using ffprobe for real audio durations.
    clips=[]
    for sd in scene_dirs:
        img=sd/"image.jpg";aud=sd/"voice.mp3";clip=sd/"clip.mp4"
        cmd=["ffmpeg","-y","-loop","1","-i",str(img),"-i",str(aud),"-c:v","libx264","-tune","stillimage","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-vf","scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2","-shortest",str(clip)]
        subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); clips.append(clip)
    concat=d/"concat.txt"
    concat.write_text("\n".join("file '"+str(x).replace("'","'\\''")+"'" for x in clips))
    out=d/f"{safe(req.title)}.mp4"
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    job["video_url"]="/videos/"+job["id"]+"/"+urllib.parse.quote(out.name)
    job["status"]="done";job["progress"]=100;job["message"]="MP4 ready"

def worker(job,req):
    try: render(job,req)
    except Exception as e: job["status"]="error";job["message"]=str(e)

@app.post("/generate")
def generate(req:Req):
    jid=uuid.uuid4().hex[:10];d=ROOT/jid;d.mkdir()
    scenes=split_scenes(req.script,req.duration_seconds)
    job={"id":jid,"dir":str(d),"status":"queued","progress":1,"message":"Job queued","scenes":scenes}
    jobs[jid]=job;threading.Thread(target=worker,args=(job,req),daemon=True).start()
    return {"job_id":jid,"status":"queued","scenes":scenes}

@app.get("/jobs/{jid}")
def status(jid:str):
    return jobs.get(jid,{"status":"error","message":"Job not found"})
