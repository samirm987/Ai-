import os,re,uuid,threading,subprocess,urllib.parse,urllib.request,math
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP=Path(__file__).resolve().parent
ROOT=APP/"jobs";ROOT.mkdir(exist_ok=True)
app=FastAPI(title="LongForge Real Video Backend")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
app.mount("/videos",StaticFiles(directory=str(ROOT)),name="videos")
jobs={}

class Req(BaseModel):
 title:str;topic:str;script:str;category:str="All Other";language:str="English (USA)"
 duration_seconds:int=600;visual_style:str="Cinematic";voice:str="Auto";aspect_ratio:str="16:9"

@app.get("/health")
def health(): return {"ok":True,"service":"LongForge Real Video Backend"}

def split_scenes(script,duration):
 words=re.findall(r"\S+",script); n=max(6,min(120,math.ceil(duration/12))); size=max(1,math.ceil(len(words)/n))
 return [{"scene":i//size+1,"narration":" ".join(words[i:i+size])} for i in range(0,len(words),size)]

def safe(s): return re.sub(r"[^A-Za-z0-9_-]+","_",s)[:60]

def make_image(prompt,out):
 url="https://image.pollinations.ai/prompt/"+urllib.parse.quote(prompt,safe="")
 req=urllib.request.Request(url,headers={"User-Agent":"LongForge/1.0"})
 with urllib.request.urlopen(req,timeout=180) as r: out.write_bytes(r.read())

def tts(text,out,voice):
 import asyncio,edge_tts
 if voice=="Auto": v="en-US-GuyNeural"
 elif "Female" in voice: v="en-US-JennyNeural"
 else: v="en-US-ChristopherNeural"
 async def go(): await edge_tts.Communicate(text,v).save(str(out))
 asyncio.run(go())

def render(job,req):
 d=Path(job["dir"]);clips=[];scenes=job["scenes"]
 for i,s in enumerate(scenes):
  sd=d/f"s{i+1:03d}";sd.mkdir(exist_ok=True)
  prompt=f"{req.visual_style}, high quality professional video frame, {req.category}, topic {req.topic}, scene {i+1}, visualize: {s['narration']}. No text, subtitles, logos or watermark."
  make_image(prompt,sd/"image.jpg");tts(s["narration"],sd/"voice.mp3",req.voice)
  clip=sd/"clip.mp4"
  vf="scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"
  subprocess.run(["ffmpeg","-y","-loop","1","-i",str(sd/"image.jpg"),"-i",str(sd/"voice.mp3"),"-c:v","libx264","-tune","stillimage","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-vf",vf,"-shortest",str(clip)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  clips.append(clip);job["progress"]=10+int(75*(i+1)/len(scenes));job["message"]=f"Generating scene {i+1}/{len(scenes)}"
 concat=d/"concat.txt";concat.write_text("\n".join("file '"+str(x).replace("'","'\\''")+"'" for x in clips))
 out=d/(safe(req.title)+".mp4")
 subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(out)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 job.update(status="done",progress=100,message="Real MP4 ready",video_url="/videos/"+job["id"]+"/"+urllib.parse.quote(out.name))

def worker(job,req):
 try: job.update(status="rendering",message="Generating real AI visuals + voice…");render(job,req)
 except Exception as e: job.update(status="error",message=str(e))

@app.post("/generate")
def generate(req:Req):
 jid=uuid.uuid4().hex[:10];d=ROOT/jid;d.mkdir()
 scenes=split_scenes(req.script,req.duration_seconds)
 job={"id":jid,"dir":str(d),"status":"queued","progress":1,"message":"Queued","scenes":scenes};jobs[jid]=job
 threading.Thread(target=worker,args=(job,req),daemon=True).start()
 return {"job_id":jid,"scenes":scenes,"status":"queued"}

@app.get("/jobs/{jid}")
def status(jid:str): return jobs.get(jid,{"status":"error","message":"Job not found"})
