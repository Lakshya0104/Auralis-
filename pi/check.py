"""Quick hardware check before the demo:  python check.py
Tests the speaker, the ultrasonic sensor, the camera and the detector, one by one."""
import shutil
import subprocess
import time

print("1. Voice ...", end=" ", flush=True)
if shutil.which("espeak-ng"):
    subprocess.run(["espeak-ng", "Speaker test. One, two, three."])
    print("did you hear it? (if not: right-click the speaker icon on the Pi desktop and pick HDMI / AV jack)")
else:
    print("espeak-ng missing: sudo apt install espeak-ng")

print("2. Ultrasonic (move your hand in front of it) ...")
try:
    from gpiozero import DistanceSensor
    from config import US_TRIG_PIN, US_ECHO_PIN
    s = DistanceSensor(echo=US_ECHO_PIN, trigger=US_TRIG_PIN, max_distance=3)
    for _ in range(10):
        print(f"   {s.distance * 100:6.1f} cm")
        time.sleep(0.3)
except Exception as e:
    print("   FAILED:", e, "-> check wiring: TRIG=GPIO23 (pin 16), ECHO via 1k to GPIO24 (pin 18), 2k from GPIO24 to GND")

print("3. Camera + detector ...")
try:
    from camera import Camera
    from detector import Detector
    cam, det = Camera(), Detector()
    for _ in range(5):
        frame = cam.read()
        found = det.detect(frame)
        print(f"   {det.last_ms:5.0f} ms  ->", [f"{d['cls']} {d['conf']:.2f}" for d in found] or "nothing")
    import cv2
    cv2.imwrite("check_frame.jpg", frame)
    print("   saved check_frame.jpg (open it to see what the camera sees)")
except Exception as e:
    print("   FAILED:", e, "-> camera: run `rpicam-hello` and check the ribbon cable (blue side faces the USB ports)")
