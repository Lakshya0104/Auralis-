"""Make distances match YOUR webcam (1 minute):

    python calibrate.py

Ask a friend to stand exactly 2 metres in front of the camera (measure it), whole body visible.
The script measures how tall they look and prints the CAM_HFOV_DEG value to put in config.py.
"""
import math
import statistics
import time

from camera import Camera
from config import FRAME_W
from detector import Detector

DIST_M, HEIGHT_M = 2.0, 1.65   # change HEIGHT_M to your friend's height
cam, det = Camera(), Detector()
heights = []
print(f"Stand {DIST_M} m from the camera, whole body in view ...")
t0 = time.time()
while len(heights) < 15 and time.time() - t0 < 30:
    frame = cam.read()
    if frame is None:
        continue
    people = [d for d in det.detect(frame) if d["cls"] == "person"]
    if people:
        x1, y1, x2, y2 = max(people, key=lambda d: d["box"][3] - d["box"][1])["box"]
        if y1 > 3 and y2 < frame.shape[0] - 3:          # whole body visible
            heights.append(y2 - y1)
            print(f"  person {y2 - y1:.0f} px tall")
if len(heights) < 5:
    print("Could not see a whole person. Step back a little, check the light, and run again.")
else:
    h = statistics.median(heights)
    focal = DIST_M * h / HEIGHT_M
    hfov = 2 * math.degrees(math.atan((FRAME_W / 2) / focal))
    print(f"\nPut this in config.py:   CAM_HFOV_DEG = {hfov:.0f}")
