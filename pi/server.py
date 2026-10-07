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
from config import DEPTH_EVERY_N, VOICE_LANG, ANNOUNCE_WITHIN_M, REPEAT_AFTER_S
from speaker import Speaker, Announcer, PHRASES

ROOT = pathlib.Path(__file__).resolve().parent
APP_DIR = ROOT.parent / "app"
latest = {"obstacles": [], "ultra": {}, "fps": 0, "t": 0, "announced": None, "piVoice": False}
latest_jpeg = None
speaker = None   # set by perception_loop; the app can change its language
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
        said = announcer.update(obstacles)          # novelty 1: "<object> detected ahead, 2 metres"
        if said:
            print(f"[voice] {said['text']}  (detector {det.last_ms:.0f} ms)")
        latest = {"obstacles": obstacles, "ultra": us.state(), "fps": round(fps, 1), "t": now,
                  "detMs": round(det.last_ms), "announced": said, "piVoice": speaker.enabled}
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
                lang = json.loads(msg.data).get("lang")
            except Exception:
                continue
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
    return ws


async def mjpeg_handler(request):
    resp = web.StreamResponse(headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"})
    await resp.prepare(request)
    while True:
        if latest_jpeg:
            await resp.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + latest_jpeg + b"\r\n")
        await asyncio.sleep(0.15)


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
    app.router.add_get("/app/", app_page)
    app.router.add_get("/app/index.html", app_page)
    app.router.add_static("/app", APP_DIR)
    scheme = "http" if args.http else "https"
    print(f"\n  On the Pi screen / projector:  {scheme}://localhost:{args.port}/")
    print(f"  On a phone (same Wi-Fi):      {scheme}://{local_ip()}:{args.port}/\n")
    web.run_app(app, port=args.port, ssl_context=None if args.http else ssl_context(), print=None)


if __name__ == "__main__":
    main()
