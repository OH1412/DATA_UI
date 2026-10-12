from __future__ import annotations

import argparse, asyncio, base64, io, math, random, time
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont
import uvicorn

app = FastAPI(title="PICO Mock Gateway", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

BODY_NAMES = ["Pelvis","LEFT_HIP","RIGHT_HIP","SPINE1","LEFT_KNEE","RIGHT_KNEE","SPINE2","LEFT_ANKLE","RIGHT_ANKLE","SPINE3","LEFT_FOOT","RIGHT_FOOT","NECK","LEFT_COLLAR","RIGHT_COLLAR","HEAD","LEFT_SHOULDER","RIGHT_SHOULDER","LEFT_ELBOW","RIGHT_ELBOW","LEFT_WRIST","RIGHT_WRIST","LEFT_HAND","RIGHT_HAND"]
HAND_NAMES = ["Palm","Wrist","Thumb_metacarpal","Thumb_proximal","Thumb_distal","Thumb_tip","Index_metacarpal","Index_proximal","Index_intermediate","Index_distal","Index_tip","Middle_metacarpal","Middle_proximal","Middle_intermediate","Middle_distal","Middle_tip","Ring_metacarpal","Ring_proximal","Ring_intermediate","Ring_distal","Ring_tip","Little_metacarpal","Little_proximal","Little_intermediate","Little_distal","Little_tip"]

def vadd(a, b): return [a[i] + b[i] for i in range(3)]
def vsub(a, b): return [a[i] - b[i] for i in range(3)]
def vscale(a, s): return [x * s for x in a]
def norm(a): return math.sqrt(sum(x*x for x in a))
def q_identity(): return [0.0, 0.0, 0.0, 1.0]
def pose(name: str, idx: int, p, valid=True, extra=None):
    d = {"id": idx, "name": name, "valid": valid, "position": [round(x, 5) for x in p], "quaternion": q_identity(), "linear_velocity": [0,0,0], "angular_velocity": [0,0,0], "linear_acceleration": [0,0,0], "angular_acceleration": [0,0,0]}
    if extra: d.update(extra)
    return d

@dataclass
class Gateway:
    tracking_fps: float = 60.0
    video_fps: float = 10.0
    random_faults: bool = False
    online: bool = True
    streaming: bool = True
    calibrated: bool = True
    seq: int = 0
    video_seq: int = 0
    started: float = field(default_factory=time.monotonic)
    sockets: dict[str, set[WebSocket]] = field(default_factory=lambda: {"telemetry": set(), "video": set(), "events": set()})
    origin: list[float] = field(default_factory=lambda: [0,0,0])
    previous: dict[int, list[float]] = field(default_factory=dict)
    previous_vel: dict[int, list[float]] = field(default_factory=dict)
    last_buttons: dict[str, bool] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    calibration_task: asyncio.Task | None = None
    restart_task: asyncio.Task | None = None

    async def broadcast(self, channel: str, message: dict[str, Any]):
        dead = []
        for ws in list(self.sockets[channel]):
            try: await ws.send_json(message)
            except Exception: dead.append(ws)
        for ws in dead: self.sockets[channel].discard(ws)

    async def event(self, message: str, level="info", event=None, data=None):
        await self.broadcast("events", {"type":"event", "timestamp_ns":time.time_ns(), "level":level, "event":event or message, "message":message, "data":data or {}})

    def body(self, t: float, dt: float):
        sway = 0.025 * math.sin(t * 1.2); lift = 0.018 * math.sin(t * 1.7)
        p = [[0,1.0+lift,0],[-.12, .98, .01],[.12,.98,.01],[0,1.16,0],[ -.14,.58,.02],[.14,.58,.02],[0,1.35,0],[-.14,.12,.04],[.14,.12,.04],[0,1.52,0],[-.16,.06,.16],[.16,.06,.16],[0,1.62,0],[-.13,1.51,0],[.13,1.51,0],[0,1.75,0],[-.22,1.50,0],[.22,1.50,0],[-.40,1.30,.05],[.40,1.30,.05],[-.55,1.17,.14],[.55,1.17,.14],[-.60,1.14,.18],[.60,1.14,.18]]
        p = [vadd(x, [sway,0,0]) for x in p]
        p[18][2] += .08 * math.sin(t*1.8); p[19][2] += .08 * math.sin(t*1.8+1.4)
        p[20][1] += .06 * math.sin(t*1.8); p[21][1] += .06 * math.sin(t*1.8+1.4)
        p = [vsub(x, self.origin) for x in p]
        joints=[]
        for i, x in enumerate(p):
            vel = vscale(vsub(x, self.previous.get(i, x)), 1/max(dt, .001)); acc = vscale(vsub(vel, self.previous_vel.get(i, vel)), 1/max(dt, .001))
            joints.append(pose(BODY_NAMES[i], i, x, self.online, {"linear_velocity":vel,"linear_acceleration":acc}))
            self.previous[i], self.previous_vel[i] = x, vel
        return p, joints

    def hand(self, side: int, wrist, t: float):
        palm = vadd(wrist, [0, .015, .015]); curl = .5 + .5*math.sin(t*1.1 + side*.7)
        joints=[pose("Palm",0,palm, self.online, {"radius":.035}), pose("Wrist",1,wrist,self.online,{"radius":.018})]
        dirs=[[-.05,.02,.04],[-.02,.03,.065],[.015,.035,.075],[.048,.025,.058],[.075,.015,.038]]
        for finger, base in enumerate(dirs):
            start=len(joints); root=vadd(palm,base); direction=[base[0]*.3, .015, base[2]]
            count = 4 if finger == 0 else 5
            for k in range(count):
                bend = -curl * .018 * k*k
                q=vadd(root, [direction[0]*k/4, direction[1]*k/4+bend, direction[2]*k/4])
                joints.append(pose(HAND_NAMES[start+k], start+k, q, self.online, {"radius":.01}))
        return {"active":self.online,"confidence":1.0 if self.online else 0.0,"scale":1.0,"joint_count":26,"joints":joints}

    def telemetry(self, t: float, dt: float):
        positions, joints = self.body(t,dt); head=positions[15]; lw,rw=positions[20],positions[21]
        left_hand=self.hand(-1, positions[22], t); right_hand=self.hand(1, positions[23], t)
        def controller(pos, phase, button):
            vel=vscale(vsub(pos, self.previous.get(20 if phase<0 else 21,pos)), 1/max(dt,.001))
            return {"valid":self.online,"position":vadd(pos,[0,0,.035]),"quaternion":q_identity(),"linear_velocity":vel,"axis":[round(math.sin(t*1.3+phase),3),round(math.cos(t*1.1+phase),3)],"trigger":round(.5+.45*math.sin(t*1.7+phase),3),"grip":round(.45+.4*math.sin(t*1.1+phase+.7),3),"axis_click":False,"primary_button":button=="primary","secondary_button":button=="secondary","menu_button":False}
        button_phase=int(t/4)%4; lb="primary" if button_phase==1 else ("secondary" if button_phase==3 else ""); rb="primary" if button_phase==2 else ""
        trackers=[]
        for i, idx in enumerate((7,8)): trackers.append(pose("tracker",i,vadd(positions[idx],[0,0,.004]),self.online,{"sn":"SIM_TRACKER_LEFT" if i==0 else "SIM_TRACKER_RIGHT"}))
        speed_l=norm(joints[20]["linear_velocity"]); speed_r=norm(joints[21]["linear_velocity"])
        now=time.time_ns(); latency=random.uniform(3,15); source=now-int(latency*1e6)
        return {"type":"telemetry","schema":"pico.telemetry.v1","device_id":"pico_01","seq":self.seq,"source_timestamp_ns":source,"gateway_timestamp_ns":now,"input_mode":"controller","coordinate_frame":{"name":"pico_world","handedness":"left","x":"right","y":"up","z":"inward"},"head":{"valid":self.online,"confidence":1.0,"position":head,"quaternion":q_identity(),"linear_velocity":joints[15]["linear_velocity"],"angular_velocity":[0,0,0]},"controllers":{"left":controller(lw,-1,lb),"right":controller(rw,1,rb)},"body":{"valid":self.online,"calibrated":self.calibrated,"joint_count":24,"joints":joints},"hands":{"left":left_hand,"right":right_hand},"motion_trackers":trackers,"derived":{"head_pitch_deg":round(4*math.sin(t*.7),3),"head_yaw_deg":round(6*math.sin(t*.43),3),"head_roll_deg":round(2*math.cos(t*.6),3),"left_wrist_speed_mps":round(speed_l,4),"right_wrist_speed_mps":round(speed_r,4),"left_wrist_depth_m":round(abs(lw[2]),4),"right_wrist_depth_m":round(abs(rw[2]),4),"left_hand_speed_mps":round(speed_l*.9,4),"right_hand_speed_mps":round(speed_r*.9,4)},"health":{"streaming":self.streaming,"tracking_fps":self.tracking_fps,"latency_ms":round(latency,2),"packet_loss_percent":round(random.uniform(0,.2),3),"head_valid":self.online,"left_controller_valid":self.online,"right_controller_valid":self.online,"body_valid":self.online,"left_hand_valid":self.online,"right_hand_valid":self.online,"tracker_count":2}}

    def frame(self, stream: str, t: float):
        colors={"ego":(10,65,76),"left_wrist":(8,45,90),"right_wrist":(105,50,20),"pico_view":(62,26,92)}; bg=colors[stream]; im=Image.new("RGB",(640,360)); px=im.load()
        for y in range(360):
            for x in range(640):
                f=(math.sin(t*.8+x*.008)+1)*10; px[x,y]=tuple(min(255,int(c+f+y*.025)) for c in bg)
        d=ImageDraw.Draw(im); cx=int(320+180*math.sin(t*.8)); cy=int(180+90*math.cos(t*.7)); d.ellipse((cx-34,cy-34,cx+34,cy+34),outline=(210,240,245),width=3); d.rectangle((70,70,570,290),outline=(100,180,190),width=2); d.text((20,18),f"PICO MOCK CAMERA / {stream.upper()}",fill=(225,245,245)); d.text((20,335),f"FRAME {self.video_seq:06d}  {time.strftime('%H:%M:%S')}",fill=(190,220,220)); out=io.BytesIO(); im.save(out,"JPEG",quality=72); return base64.b64encode(out.getvalue()).decode()

gateway=Gateway()

@app.get("/api/status")
async def status(): return {"device_id":"pico_01","online":gateway.online,"streaming":gateway.streaming,"body_calibrated":gateway.calibrated,"tracking_mode":"full_body","tracker_count":2,"uptime_s":round(time.monotonic()-gateway.started,1)}

@app.post("/api/command")
async def command(payload: dict):
    cmd=payload.get("command",""); print(f"[COMMAND] {cmd}")
    if cmd not in {"prepare","start_stream","stop_stream","recenter","recalibrate","restart_client"}: return {"command_id":"invalid","command":cmd,"success":False,"message":"unknown command"}
    if cmd=="prepare": await asyncio.sleep(.5); await gateway.event("READY",event="READY")
    elif cmd=="start_stream": gateway.streaming=True; await gateway.event("Stream started",event="STREAM_STARTED")
    elif cmd=="stop_stream": gateway.streaming=False; await gateway.event("Stream stopped",event="STREAM_STOPPED")
    elif cmd=="recenter": gateway.origin=[0,0,0]; await gateway.event("Recenter completed",event="RECENTER_COMPLETED")
    elif cmd=="recalibrate":
        gateway.calibrated=False; await gateway.event("Calibration started",event="CALIBRATION_STARTED"); gateway.calibration_task=asyncio.create_task(finish_calibration())
    elif cmd=="restart_client": gateway.restart_task=asyncio.create_task(restart_client())
    return {"command_id":f"cmd_{int(time.time()*1000)}","command":cmd,"success":True,"message":f"{cmd} accepted"}

async def finish_calibration():
    await asyncio.sleep(2); gateway.calibrated=True; await gateway.event("Calibration completed",event="CALIBRATION_COMPLETED")
async def restart_client():
    gateway.online=False; gateway.streaming=False; await gateway.event("Client restarting",event="CLIENT_RESTARTING",level="warning"); await asyncio.sleep(1.5); gateway.online=True; gateway.streaming=True; await gateway.event("Client restarted",event="CLIENT_RESTARTED")

@app.websocket("/ws/telemetry")
async def telemetry_ws(ws: WebSocket):
    await ws.accept(); gateway.sockets["telemetry"].add(ws); last=time.monotonic()
    try:
        while True:
            if gateway.online and gateway.streaming:
                now=time.monotonic(); dt=max(.001,now-last); last=now; gateway.seq+=1; await ws.send_json(gateway.telemetry(now,dt))
            await asyncio.sleep(1/gateway.tracking_fps)
    except WebSocketDisconnect:
        gateway.sockets["telemetry"].discard(ws)
    except Exception as exc:
        print(f"[TELEMETRY ERROR] {type(exc).__name__}: {exc}", flush=True)
        gateway.sockets["telemetry"].discard(ws)

@app.websocket("/ws/video")
async def video_ws(ws: WebSocket):
    await ws.accept(); gateway.sockets["video"].add(ws)
    try:
        while True:
            if gateway.online and gateway.streaming:
                for stream in ("ego","left_wrist","right_wrist","pico_view"):
                    gateway.video_seq+=1; await ws.send_json({"type":"video","stream":stream,"seq":gateway.video_seq,"source_timestamp_ns":time.time_ns(),"width":640,"height":360,"fps":gateway.video_fps,"encoding":"jpeg_base64","data":gateway.frame(stream,time.monotonic())})
            await asyncio.sleep(1/gateway.video_fps)
    except (WebSocketDisconnect, Exception): gateway.sockets["video"].discard(ws)

@app.websocket("/ws/events")
async def events_ws(ws: WebSocket):
    await ws.accept(); gateway.sockets["events"].add(ws); await gateway.event("Connected to mock gateway",event="CONNECTED")
    try:
        while True: await asyncio.sleep(30)
    except (WebSocketDisconnect, Exception): gateway.sockets["events"].discard(ws)

async def stats_loop():
    while True:
        await asyncio.sleep(5); print(f"[STATS] clients={sum(len(x) for x in gateway.sockets.values())} telemetry_fps={gateway.tracking_fps:.0f} video_fps={gateway.video_fps:.0f} uptime={time.monotonic()-gateway.started:.0f}s")

@app.on_event("startup")
async def startup(): asyncio.create_task(stats_loop())

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--host",default="0.0.0.0"); parser.add_argument("--port",type=int,default=8765); parser.add_argument("--tracking-fps",type=float,default=60); parser.add_argument("--video-fps",type=float,default=10); parser.add_argument("--enable-random-faults",action="store_true"); args=parser.parse_args(); gateway.tracking_fps=args.tracking_fps; gateway.video_fps=args.video_fps; gateway.random_faults=args.enable_random_faults
    print("======================================\n PICO MOCK GATEWAY\n======================================\nHTTP       http://127.0.0.1:%d\nTelemetry  ws://127.0.0.1:%d/ws/telemetry\nVideo      ws://127.0.0.1:%d/ws/video\nEvents     ws://127.0.0.1:%d/ws/events\nTracking   %.0f Hz\nVideo      %.0f Hz\nDevice     pico_01\nStatus     READY\n======================================"%(args.port,args.port,args.port,args.port,args.tracking_fps,args.video_fps))
    uvicorn.run(app,host=args.host,port=args.port,log_level="info")
