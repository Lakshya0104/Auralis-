"""Collect training photos from the cane's own camera while walking.

    python3 capture.py                 # one photo every 1.0 s into dataset_raw/<date>/
    python3 capture.py --every 0.5     # faster
    python3 capture.py --only-moving   # skip near-identical frames (standing still)

Walk your campus routes holding the cane normally. Photos taken from the real camera height
and angle make the detector far more accurate than internet photos alone.
Then upload dataset_raw/ to Roboflow, draw boxes, and export in YOLOv8 format (see docs/DATASET_GUIDE.md).
"""
import argparse
import datetime
import pathlib
import time

import cv2
import numpy as np

from camera import Camera


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=float, default=1.0, help="seconds between photos")
    ap.add_argument("--only-moving", action="store_true")
    ap.add_argument("--video", help="extract frames from a recorded video instead of the camera")
    args = ap.parse_args()

    out = pathlib.Path(__file__).resolve().parent / "dataset_raw" / datetime.date.today().isoformat()
    out.mkdir(parents=True, exist_ok=True)
    cam = Camera(args.video)
    last_small, n, last_t = None, 0, 0.0
    print(f"Saving to {out}  (Ctrl+C to stop)")
    try:
        while True:
            frame = cam.read()
            if frame is None:
                break
            now = time.time()
            if not args.video and now - last_t < args.every:
                time.sleep(0.02)
                continue
            small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (32, 24)).astype(np.float32)
            if args.only_moving and last_small is not None and np.abs(small - last_small).mean() < 6:
                continue
            last_small, last_t = small, now
            cv2.imwrite(str(out / f"{datetime.datetime.now():%H%M%S}_{n:05d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            n += 1
            if n % 25 == 0:
                print(f"{n} photos")
    except KeyboardInterrupt:
        pass
    print(f"Saved {n} photos in {out}")


if __name__ == "__main__":
    main()
