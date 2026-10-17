"""Measure AURALIS for the paper (about 10 minutes):   python measure.py

1. Distance accuracy: put a chair (or have a friend stand) straight in front of the cane at
   0.5, 1, 1.5, 2, 2.5 and 3 m (measure with a tape). Press Enter at each distance.
2. Speed: detection time and frames per second are recorded at the same time.

Writes results.json; docs/paper/make_paper.py puts these real numbers into the IEEE paper.
"""
import json
import pathlib
import statistics
import time

from camera import Camera
from detector import Detector
from distance import DepthNet, estimate
from ultrasonic import Ultrasonic

DISTANCES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
FRAMES = 20

cam, det, us, depth = Camera(), Detector(), Ultrasonic(), DepthNet()
target = input("Object you will use (e.g. chair, person): ").strip() or "chair"
rows, all_ms, t_start, n_frames = [], [], time.time(), 0

for true_d in DISTANCES:
    input(f"\nPlace the {target} at {true_d} m straight ahead, then press Enter ...")
    cam_d, us_d, hits = [], [], 0
    for _ in range(FRAMES):
        frame = cam.read()
        if frame is None:
            continue
        found = [d for d in estimate(det.detect(frame), depth) if d["cls"] == target]
        all_ms.append(det.last_ms)
        n_frames += 1
        if found:
            hits += 1
            cam_d.append(max(found, key=lambda d: (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]))["dist"])
        cm = us.state().get("cm")
        if cm is not None:
            us_d.append(cm / 100)
        time.sleep(0.05)
    row = {"true_m": true_d, "detection_rate": round(hits / FRAMES, 2),
           "camera_m": round(statistics.median(cam_d), 2) if cam_d else None,
           "ultrasonic_m": round(statistics.median(us_d), 2) if us_d else None}
    row["camera_err_pct"] = round(abs(row["camera_m"] - true_d) / true_d * 100, 1) if row["camera_m"] else None
    row["ultrasonic_err_pct"] = round(abs(row["ultrasonic_m"] - true_d) / true_d * 100, 1) if row["ultrasonic_m"] else None
    rows.append(row)
    print("  ", row)

elapsed = time.time() - t_start
results = {
    "object": target,
    "distance": rows,
    "detector_ms_median": round(statistics.median(all_ms), 1) if all_ms else None,
    "detector_ms_p95": round(sorted(all_ms)[int(0.95 * (len(all_ms) - 1))], 1) if all_ms else None,
    "model_px": det.model.size if det.model else None,
    "measured_on": time.strftime("%Y-%m-%d"),
}
out = pathlib.Path(__file__).resolve().parent / "results.json"
out.write_text(json.dumps(results, indent=1))
print(f"\nSaved {out}\nNow copy it to the repo:  cp results.json ../docs/paper/results.json && git add ../docs/paper/results.json")
