"""Distance from a single camera.

Three estimates, combined:
  1. Ground-plane geometry: the box's bottom edge touches the ground; with the camera
     height and tilt known, the image row gives the distance. Works for anything on the ground.
  2. Known size: distance = real height x focal length / box height in pixels.
  3. Neural network 2 (optional): MiDaS monocular depth. It gives *relative* depth, which
     we scale to metres every frame by fitting it to the geometric estimates.
"""
import math
import os

import cv2
import numpy as np

from config import (FRAME_H, FRAME_W, FOCAL_PX, CAM_HEIGHT_M, CAM_PITCH_DEG,
                    CLASSES, DEPTH_MODEL)


def ground_distance(y_bottom):
    """Distance along the ground to the point at image row y_bottom (None if above the horizon)."""
    angle_below_center = math.atan((y_bottom - FRAME_H / 2) / FOCAL_PX)
    angle = math.radians(CAM_PITCH_DEG) + angle_below_center
    if angle <= math.radians(2):
        return None
    return CAM_HEIGHT_M / math.tan(angle)


def size_distance(cls, box_h_px):
    h = CLASSES.get(cls, (None, 0, 0))[1]
    if h <= 0 or box_h_px < 4:
        return None
    return h * FOCAL_PX / box_h_px


def lateral_offset_m(x_px, dist_m):
    """Sideways distance from the walking line at a given depth."""
    return (x_px - FRAME_W / 2) / FOCAL_PX * dist_m


class DepthNet:
    """MiDaS small (ONNX). Download: see README. Skipped if the model file is missing."""

    def __init__(self):
        self.sess = None
        self.depth = None
        if os.path.exists(DEPTH_MODEL):
            import onnxruntime as ort
            self.sess = ort.InferenceSession(DEPTH_MODEL, providers=["CPUExecutionProvider"])
            self.inp = self.sess.get_inputs()[0]
            self.size = self.inp.shape[2] if isinstance(self.inp.shape[2], int) else 256
            print("[depth] MiDaS loaded")

    def update(self, frame):
        if not self.sess:
            return
        img = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (self.size, self.size)).astype(np.float32) / 255
        img = (img - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
        out = self.sess.run(None, {self.inp.name: img.transpose(2, 0, 1)[None].astype(np.float32)})[0]
        self.depth = cv2.resize(out.squeeze(), (FRAME_W, FRAME_H))  # inverse relative depth

    def box_value(self, box):
        if self.depth is None:
            return None
        x1, y1, x2, y2 = (int(v) for v in box)
        patch = self.depth[max(y1, 0):max(y2, 1), max(x1, 0):max(x2, 1)]
        return float(np.median(patch)) if patch.size else None


def estimate(detections, depthnet):
    """Adds 'dist' (m) and 'method' to each detection."""
    pairs = []  # (MiDaS inverse depth, geometric metres) for scale fitting
    for d in detections:
        x1, y1, x2, y2 = d["box"]
        hanging = CLASSES.get(d["cls"], ("",))[0] == "head"     # branches / signboards don't touch the ground
        g = ground_distance(y2) if y2 < FRAME_H - 2 and not hanging else None   # bottom cut off -> can't trust it
        s = size_distance(d["cls"], y2 - y1)
        geo = g if g is not None else s
        d["dist"], d["method"] = geo, "ground" if g is not None else "size" if s is not None else None
        d["_inv"] = depthnet.box_value(d["box"])
        if geo and d["_inv"]:
            pairs.append((d["_inv"], geo))
    # Fit metres ~ k / inverse_depth from the geometric estimates of this frame, then use
    # MiDaS for objects geometry could not handle (bottom out of frame, unknown size).
    if pairs:
        k = float(np.median([inv * m for inv, m in pairs]))
        for d in detections:
            if d["dist"] is None and d["_inv"]:
                d["dist"], d["method"] = k / d["_inv"], "depthnet"
    for d in detections:
        d.pop("_inv", None)
        if d["dist"] is None:  # very close, fills the frame bottom
            d["dist"], d["method"] = 0.5, "fallback"
    return detections
