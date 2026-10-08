"""AURALIS Pi server.

    python3 server.py              # on the Pi (camera + ultrasonic + YOLO)
    python3 server.py --simulate   # on a laptop, no hardware, fake detections

Serves the phone web app over HTTPS (needed for GPS + microphone in Chrome),
streams obstacles on wss://<pi>:8443/ws and the annotated camera on /video.mjpg.
"""
import argparse
import asyncio
import json
import pathlib
import socket
import ssl
import subprocess
import threading
import time

import cv2
from aiohttp import web

from camera import Camera
from detector import Detector
from distance import DepthNet
from perception import perceive
from ultrasonic import Ultrasonic
from config import DEPTH_EVERY_N, VOICE_LANG, ANNOUNCE_WITHIN_M, REPEAT_AFTER_S, COLLEGE_LAT, COLLEGE_LON
from speaker import Speaker, Announcer, PHRASES

ROOT = pathlib.Path(__file__).resolve().parent
APP_DIR = ROOT.parent / "app"
latest = {"obstacles": [], "ultra": {}, "fps": 0, "t": 0, "announced": None, "piVoice": False}
latest_jpeg = None
speaker = None   # set by perception_loop; the app can change its language
active = True    # paused = no announcements (hand gesture on the ultrasonic, or the app's button)
MEMORY_FILE = ROOT / "memory.json"   # the cane's own memory of places and hazards
LASTFIX_FILE = ROOT / "lastfix.json"  # last phone GPS fix, so the map opens where the cane really is
mem_ver = 0          # bumped on every memory save, so the Pi screen reloads the map
phone_voice = set()  # phones that speak the alerts (into headphones); the Pi speaker is quiet meanwhile
try:
    phone_fix = json.loads(LASTFIX_FILE.read_text())
except Exception:
    phone_fix = None
if COLLEGE_LAT is not None and COLLEGE_LON is not None:
    # the college set in config.py wins over an old GPS fix from somewhere else
    phone_fix = {"lat": COLLEGE_LAT, "lon": COLLEGE_LON, "accuracy": 0, "heading": None, "t": 0}
_fix_saved = 0.0


def set_active(on, announce=True):
    global active
    if on == active:
        return
    active = on
    print(f"[cane] {'active' if on else 'paused'}")
    if announce and speaker:
        speaker.say(PHRASES[speaker.lang]["resumed" if on else "paused"], urgent=True)
COLORS = {"drop": (0, 0, 255), "raised": (0, 140, 255), "static": (0, 220, 255),
          "head": (255, 0, 255), "moving": (255, 160, 0), "zone": (180, 180, 180)}


def perception_loop(args):
    global latest, latest_jpeg
    cam = Camera(args.video) if not args.simulate or args.video else None
    det = Detector(simulate=args.simulate)
    us = Ultrasonic(simulate=args.simulate)
    depth = DepthNet()
    global speaker
    speaker = Speaker(args.lang, enabled=not args.no_voice)
    announcer = Announcer(speaker, ANNOUNCE_WITHIN_M, REPEAT_AFTER_S)
    speaker.say(PHRASES[args.lang]["ready"])
    n, t_last, last_warn = 0, time.time(), 0.0
    hand_since, hand_used = None, False
    fps = 0.0
    while True:
        frame = cam.read() if cam else None
        if frame is None:
            if cam and time.time() - last_warn > 5:
                print("[camera] NO PICTURE from the webcam - check the USB cable, or set USB_CAMERA_INDEX = 1 in config.py")
                last_warn = time.time()
            frame = 40 * __import__("numpy").ones((480, 640, 3), "uint8")
            time.sleep(0.2)
        if n % DEPTH_EVERY_N == 0:
            depth.update(frame)
        obstacles = perceive(det.detect(frame), us.state(), depth)
        now = time.time()
        fps = 0.8 * fps + 0.2 / max(now - t_last, 1e-3)
        t_last = now
        # Hands-free pause / resume: hold a hand < 10 cm from the ultrasonic sensor for 2 seconds
        cm = us.state().get("cm")
        if cm is not None and cm < 10:
            hand_since = hand_since or now
            if not hand_used and now - hand_since > 2:
                set_active(not active)
                hand_used = True
        else:
            hand_since, hand_used = None, False
        said = announcer.update(obstacles) if active else None   # novelty 1: "<object> detected ahead, 2 metres"
        if said:
            print(f"[voice] {said['text']}  (detector {det.last_ms:.0f} ms)")
        latest = {"obstacles": obstacles, "ultra": us.state(), "fps": round(fps, 1), "t": now,
                  "detMs": round(det.last_ms), "announced": said, "piVoice": speaker.enabled, "active": active,
                  "voiceOnPhone": bool(phone_voice), "phone": phone_fix, "memVer": mem_ver}
        for o in obstacles:
            if o["box"]:
                x1, y1, x2, y2 = o["box"]
                c = COLORS[o["category"]]
                cv2.rectangle(frame, (x1, y1), (x2, y2), c, 3 if o["inCorridor"] else 1)
                cv2.putText(frame, f'{o["cls"]} {o["dist"]}m', (x1, max(y1 - 6, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 2)
        cv2.line(frame, (320, 480), (320, 240), (255, 255, 255), 1)
        latest_jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])[1].tobytes()
        n += 1


async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=10)
    await ws.prepare(request)
    async def receive():
        # the app sends {"lang": "ta"} when the user picks a language -> the Pi speaks that language
        async for msg in ws:
            try:
                data = json.loads(msg.data)
            except Exception:
                continue
            if "phoneVoice" in data:                   # this phone speaks into its headphones
                (phone_voice.add if data["phoneVoice"] else phone_voice.discard)(ws)
                set_phone_voice()
            if isinstance(data.get("gps"), dict):      # the phone's GPS: shown live on the Pi screen
                save_fix(data["gps"])
            if "active" in data:                       # app's start / stop button
                set_active(bool(data["active"]), announce=data.get("announce", True))
            if data.get("say") and speaker and active:  # e.g. remembered-hazard warnings from the app
                speaker.say(str(data["say"])[:200], urgent=bool(data.get("urgent")))
                print(f"[voice] (from app) {data['say']}")
            lang = data.get("lang")
            if speaker and lang in PHRASES and lang != speaker.lang:
                speaker.lang = lang
                speaker.say(PHRASES[lang]["ready"])
                print(f"[voice] language -> {lang}")
    reader = asyncio.ensure_future(receive())
    last = 0
    try:
        while not ws.closed:
            if latest["t"] != last:
                last = latest["t"]
                await ws.send_str(json.dumps(latest))
            await asyncio.sleep(0.05)
    finally:
        reader.cancel()
        phone_voice.discard(ws)
        set_phone_voice()
    return ws


def set_phone_voice():
    if speaker:
        speaker.muted = bool(phone_voice)


def save_fix(g):
    global phone_fix, _fix_saved
    try:
        phone_fix = {"lat": float(g["lat"]), "lon": float(g["lon"]), "accuracy": float(g.get("accuracy") or 0),
                     "heading": None if g.get("heading") is None else float(g["heading"]), "t": time.time()}
    except (KeyError, TypeError, ValueError):
        return
    if time.time() - _fix_saved > 30:
        _fix_saved = time.time()
        LASTFIX_FILE.write_text(json.dumps(phone_fix))


async def mjpeg_handler(request):
    resp = web.StreamResponse(headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"})
    await resp.prepare(request)
    while True:
        if latest_jpeg:
            await resp.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + latest_jpeg + b"\r\n")
        await asyncio.sleep(0.15)


async def memory_get(request):
    try:
        return web.json_response(json.loads(MEMORY_FILE.read_text()))
    except Exception:
        return web.json_response({})


async def memory_put(request):
    data = await request.json()
    tmp = MEMORY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(MEMORY_FILE)
    global mem_ver
    mem_ver += 1
    return web.json_response({"ok": True, "ver": mem_ver})


def phone_url(port, http=False):
    return f"{'http' if http else 'https'}://{local_ip()}:{port}/"


async def phone_info(request):
    return web.json_response({"url": phone_url(request.app["port"], request.app["http"])})


async def qr_svg(request):
    """QR code of the phone address, shown on the Pi screen (needs: pip install qrcode)."""
    try:
        import io
        import qrcode
        import qrcode.image.svg
        buf = io.BytesIO()
        qrcode.make(phone_url(request.app["port"], request.app["http"]), image_factory=qrcode.image.svg.SvgPathFillImage,
                     box_size=12, border=2).save(buf)
        return web.Response(body=buf.getvalue(), content_type="image/svg+xml")
    except Exception:
        raise web.HTTPNotFound()


async def index(request):
    raise web.HTTPFound("/app/index.html")


async def app_page(request):
    """app/index.html is written without the document skeleton (so it can also be published as a
    web artifact); add it here so the browser renders in standards mode."""
    body = (APP_DIR / "index.html").read_text(encoding="utf-8")
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            '</head><body>' + body + '</body></html>')
    return web.Response(text=html, content_type="text/html")


def ssl_context():
    cert, key = ROOT / "cert.pem", ROOT / "key.pem"
    if not cert.exists():
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650",
                        "-subj", "/CN=auralis", "-keyout", str(key), "-out", str(cert)], check=True,
                       capture_output=True)
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(cert, key)
    return ctx


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulate", action="store_true", help="no camera/GPIO/YOLO; fake data")
    ap.add_argument("--video", help="use a video file instead of the camera")
    ap.add_argument("--port", type=int, default=8443)
    ap.add_argument("--http", action="store_true", help="plain HTTP (GPS will not work on the phone)")
    ap.add_argument("--lang", default=VOICE_LANG, choices=["en", "hi", "te", "ta"], help="voice language on the Pi")
    ap.add_argument("--fast", action="store_true", help="smaller 320 px detector (~2x faster, less accurate)")
    ap.add_argument("--no-voice", action="store_true", help="let the phone speak instead of the Pi")
    args = ap.parse_args()

    threading.Thread(target=perception_loop, args=(args,), daemon=True).start()
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)
    app.router.add_get("/video.mjpg", mjpeg_handler)
    app["port"], app["http"] = args.port, args.http
    app.router.add_get("/phone", phone_info)
    app.router.add_get("/qr.svg", qr_svg)
    app.router.add_get("/memory", memory_get)
    app.router.add_post("/memory", memory_put)
    app.router.add_get("/app/", app_page)
    app.router.add_get("/app/index.html", app_page)
    app.router.add_static("/app", APP_DIR)
    scheme = "http" if args.http else "https"
    print(f"\n  On the Pi screen / projector:  {scheme}://localhost:{args.port}/")
    print(f"  On a phone (same Wi-Fi):      {phone_url(args.port, args.http)}\n")
    try:
        import qrcode
        q = qrcode.QRCode(border=1)
        q.add_data(phone_url(args.port, args.http))
        q.print_ascii(invert=True)
        print("  Scan with the phone camera, then tap Advanced -> Proceed.\n")
    except ImportError:
        pass
    web.run_app(app, port=args.port, ssl_context=None if args.http else ssl_context(), print=None)


if __name__ == "__main__":
    main()
