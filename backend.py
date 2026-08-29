import os, uuid, asyncio, subprocess, shutil, json, re
from pathlib import Path
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"outputs"; JOBS=ROOT/"jobs"; OUT.mkdir(exist_ok=True); JOBS.mkdir(exist_ok=True)
RUNWAY_URL="https://api.dev.runwayml.com/v1/image_to_video"
RUNWAY_VERSION="2024-11-06"
jobs={}

class Req(BaseModel):
    title:str=""
    topic:str=""
    script:str
    category:str="Other"
    language:str="English (USA)"
    duration_minutes:int=1
    aspect:str="16:9"
    style:str="Cinematic"
    clip_seconds:int=5
    api_key:Optional[str]=None

def split_script(text, target):
    paras=[p.strip() for p in re.split(r'\n\s*\n|\n(?=[A-Z0-9\u0980-\u09ff\u0905-\u0939])',text) if p.strip()]
    if not paras: paras=[text.strip()]
    if len(paras)>=target:return paras[:target]
    # distribute words into target-ish chunks without inventing content
    words=text.split()
    chunks=[]; step=max(1,(len(words)+target-1)//target)
    for i in range(0,len(words),step): chunks.append(" ".join(words[i:i+step]))
    return chunks

def ratio_for(a):
    return {"16:9":"1280:720","9:16":"720:1280","1:1":"960:960"}.get(a,"1280:720")

async def runway_clip(prompt,key,ratio,duration):
    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","X-Runway-Version":RUNWAY_VERSION}
    payload={"model":"gen4.5","promptText":prompt,"ratio":ratio,"duration":duration}
    async with httpx.AsyncClient(timeout=90) as c:
        r=await c.post(RUNWAY_URL,headers=headers,json=payload)
        if r.status_code>=400: raise RuntimeError(f"Runway create failed {r.status_code}: {r.text[:500]}")
        task=r.json()["id"]
        for _ in range(180):
            await asyncio.sleep(5)
            q=await c.get(f"https://api.dev.runwayml.com/v1/tasks/{task}",headers={"Authorization":f"Bearer {key}","X-Runway-Version":RUNWAY_VERSION})
            if q.status_code>=400: raise RuntimeError(f"Runway status failed {q.status_code}: {q.text[:300]}")
            data=q.json(); status=data.get("status")
            if status=="SUCCEEDED": return data["output"][0]
            if status in ("FAILED","CANCELED"): raise RuntimeError("Runway task "+status+": "+json.dumps(data)[:600])
        raise RuntimeError("Runway task timed out")

async def download(url,path):
    async with httpx.AsyncClient(timeout=120) as c:
        r=await c.get(url); r.raise_for_status(); path.write_bytes(r.content)

async def generate(job_id,req):
    try:
        key=req.api_key or os.getenv("RUNWAYML_API_SECRET")
        if not key: raise RuntimeError("No Runway API key. Set RUNWAYML_API_SECRET on the server or enter a local test key.")
        minutes=max(1,min(20,req.duration_minutes))
        total=max(1,int(minutes*60/req.clip_seconds))
        scenes=split_script(req.script,total)
        jobs[job_id]={"status":"running","progress":1,"message":f"Preparing {total} scenes…"}
        work=JOBS/job_id; work.mkdir()
        clips=[]
        for i in range(total):
            scene=scenes[i % len(scenes)]
            prompt=(f"Create scene {i+1} of a long-form {req.category} video. "
                     f"Title: {req.title}. Topic: {req.topic}. Language/context: {req.language}. "
                     f"Visual style: {req.style}. Scene narration/source text: {scene}. "
                     "Use coherent cinematic composition, natural motion, clean visuals, no captions, no logos, no watermarks. "
                     "This is one continuous sequence, so keep the visual subject consistent with the scene text.")
            url=await runway_clip(prompt,key,ratio_for(req.aspect),req.clip_seconds)
            p=work/f"{i:04d}.mp4"; await download(url,p); clips.append(p)
            jobs[job_id]["progress"]=int((i+1)/total*90); jobs[job_id]["message"]=f"Generated scene {i+1}/{total}"
        listfile=work/"concat.txt"
        listfile.write_text("\n".join("file '"+str(p).replace("'","'\\''")+"' " for p in clips))
        final=OUT/f"{job_id}.mp4"
        if not shutil.which("ffmpeg"): raise RuntimeError("FFmpeg is not installed on the server.")
        proc=await asyncio.create_subprocess_exec("ffmpeg","-y","-f","concat","-safe","0","-i",str(listfile),"-c","copy",str(final),stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.PIPE)
        _,err=await proc.communicate()
        if proc.returncode!=0: raise RuntimeError("FFmpeg stitching failed: "+err.decode(errors="ignore")[-800:])
        jobs[job_id]={"status":"completed","progress":100,"message":"Finished","video_url":f"/videos/{final.name}"}
    except Exception as e:
        jobs[job_id]={"status":"failed","progress":0,"message":str(e)}

app=FastAPI(title="TextForge Real Video API")
app.mount("/static",StaticFiles(directory=str(ROOT)),name="static")
@app.get("/")
def home(): return FileResponse(ROOT/"index.html")
@app.post("/api/generate")
async def start(req:Req):
    if not req.script.strip(): raise HTTPException(400,"Script is required.")
    if req.duration_minutes<1 or req.duration_minutes>20: raise HTTPException(400,"Duration must be 1–20 minutes.")
    jid=uuid.uuid4().hex; jobs[jid]={"status":"queued","progress":0,"message":"Queued"}
    asyncio.create_task(generate(jid,req)); return {"job_id":jid}
@app.get("/api/status/{jid}")
def status(jid:str):
    if jid not in jobs: raise HTTPException(404,"Job not found")
    return jobs[jid]
@app.get("/videos/{name}")
def video(name:str):
    p=OUT/name
    if not p.exists(): raise HTTPException(404,"Video not found")
    return FileResponse(p,media_type="video/mp4",filename=name)
