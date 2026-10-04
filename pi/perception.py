"""Turns detections + distances + ultrasonic into obstacles (taxonomy, corridor, motion)."""
import time

from config import (CLASSES, CORRIDOR_WIDTH_M, MAX_RANGE_M, FRAME_H, FRAME_W, PARKABLE,
                    DROP, RAISED, STATIC, HEAD, MOVING)
from distance import estimate, lateral_offset_m


class Tracker:
    """Very small tracker: matches each object to the nearest same-class object of the last frame
    to get approach speed (m/s, positive = coming closer)."""

    def __init__(self):
        self.prev = []
        self.still_since = {}

    def update(self, objs, now):
        for o in objs:
            cx = (o["box"][0] + o["box"][2]) / 2
            best = min((p for p in self.prev if p["cls"] == o["cls"]),
                       key=lambda p: abs(p["cx"] - cx), default=None)
            if best and abs(best["cx"] - cx) < 80 and now > best["t"]:
                speed = (best["dist"] - o["dist"]) / (now - best["t"])
                o["approach"] = 0.6 * best.get("approach", 0) + 0.4 * speed
                o["still_for"] = best["still_for"] + (now - best["t"]) if abs(o["approach"]) < 0.25 else 0
            else:
                o["approach"], o["still_for"] = 0.0, 0.0
            o["cx"], o["t"] = cx, now
        self.prev = objs


tracker = Tracker()


def perceive(detections, ultra, depthnet):
    now = time.time()
    objs = estimate(detections, depthnet)
    tracker.update(objs, now)
    out = []
    for o in objs:
        category, _, severity = CLASSES[o["cls"]]
        x1, y1, x2, y2 = o["box"]
        # nearest edge of the object to the walking line
        # (0 if the object spans the centre line)
        mid = FRAME_W / 2
        lateral = lateral_offset_m(x1, o["dist"]) if x1 > mid else lateral_offset_m(x2, o["dist"]) if x2 < mid else 0.0
        # head-level: whole box in the upper part of the image and close
        if y2 < FRAME_H * 0.45 and o["dist"] < 2.5 and category in (STATIC, HEAD):
            category = HEAD
        # vehicles standing still for 3 s are parked obstacles
        if o["cls"] in PARKABLE and o["still_for"] > 3:
            category = STATIC
        in_corridor = abs(lateral) <= CORRIDOR_WIDTH_M / 2 and o["dist"] <= MAX_RANGE_M
        out.append({
            "cls": o["cls"], "category": category, "severity": severity,
            "conf": round(o["conf"], 2), "dist": round(o["dist"], 2), "method": o["method"],
            "lateral": round(lateral, 2), "side": "ahead" if abs(lateral) < 0.25 else "left" if lateral < 0 else "right",
            "approach": round(o["approach"], 2), "inCorridor": in_corridor,
            "area": round((x2 - x1) * (y2 - y1) / (FRAME_W * FRAME_H), 3),
            "offset": round(min(abs(o["cx"] - FRAME_W / 2) / (FRAME_W / 2), 1), 2),
            "box": [round(v) for v in o["box"]],
            "remember": category != MOVING,
        })
    # The ultrasonic sensor sees drops / raised ground the camera may miss
    if ultra["drop"]:
        out.append({"cls": "drop", "category": DROP, "severity": 1.0, "conf": 0.95, "dist": 0.5, "method": "ultrasonic",
                    "lateral": 0, "side": "ahead", "approach": 0, "inCorridor": True, "area": 0, "offset": 0,
                    "box": None, "remember": True})
    elif ultra["raised"]:
        out.append({"cls": "step_up", "category": RAISED, "severity": 0.6, "conf": 0.8, "dist": 0.5, "method": "ultrasonic",
                    "lateral": 0, "side": "ahead", "approach": 0, "inCorridor": True, "area": 0, "offset": 0,
                    "box": None, "remember": True})
    out.sort(key=lambda o: (not o["inCorridor"], o["dist"]))
    return out
