"""AURALIS settings and the obstacle taxonomy (see docs/AURALIS_Research_and_Design_Plan.pdf, section 4)."""
import math
import pathlib

MODELS = pathlib.Path(__file__).resolve().parent / "models"

# ---- Camera mounting (measure on your cane) --------------------------------
FRAME_W, FRAME_H = 640, 480
CAM_HFOV_DEG = 66          # Pi Camera Module 3 standard lens (v2 camera: 62)
CAM_HEIGHT_M = 0.90        # camera height above the ground
CAM_PITCH_DEG = 20         # camera tilted down from horizontal
FOCAL_PX = (FRAME_W / 2) / math.tan(math.radians(CAM_HFOV_DEG / 2))

# ---- Walking corridor -------------------------------------------------------
CORRIDOR_WIDTH_M = 1.0     # objects whose nearest edge is within +-0.5 m of the centre line
MAX_RANGE_M = 4.0          # beyond this, track silently

# ---- Ultrasonic HC-SR04 ---------------------------------------------------------
# "front": facing forward (best for a classroom demo: announces any obstacle closer than
#          US_FRONT_ALERT_CM, even ones the camera does not recognise)
# "down":  pointing down near the tip to detect drops / steps (outdoor use)
US_MODE = "front"
US_FRONT_ALERT_CM = 100
US_TRIG_PIN, US_ECHO_PIN = 23, 24
DROP_DELTA_CM = 15         # reading this much longer than normal ground = drop / pit
RAISE_DELTA_CM = 12        # this much shorter = step up / raised obstacle

# ---- Models -------------------------------------------------------------------
YOLO_MODEL = str(MODELS / "auralis_yolo.pt")   # custom-trained (ml/train_yolo.py), used if present
YOLO_ONNX = str(MODELS / "yolov8n.onnx")       # stock COCO model, runs with onnxruntime only (no PyTorch)
YOLO_IMGSZ = 320
YOLO_CONF = 0.45

# ---- Voice on the Pi (espeak-ng through HDMI / 3.5 mm jack / Bluetooth speaker) -----
VOICE_LANG = "en"          # en, hi, te, ta  (override: python server.py --lang ta)
ANNOUNCE_WITHIN_M = 3.0    # announce corridor obstacles closer than this
REPEAT_AFTER_S = 5         # do not repeat the same object sooner than this
DEPTH_MODEL = str(MODELS / "midas_small.onnx") # optional depth network
DEPTH_EVERY_N = 4                       # run depth on every Nth frame (Pi 4 is slow)

# ---- Obstacle taxonomy ------------------------------------------------------
DROP, RAISED, STATIC, HEAD, MOVING, ZONE = "drop", "raised", "static", "head", "moving", "zone"

# class -> (category, typical real height in m for size-based distance, severity 0..1)
CLASSES = {
    # custom classes (trained with ml/train_yolo.py)
    "pothole":       (DROP,   0.0, 1.0),
    "open_drain":    (DROP,   0.0, 1.0),
    "stairs_down":   (DROP,   0.0, 1.0),
    "curb":          (DROP,   0.15, 0.7),
    "stairs_up":     (RAISED, 0.5, 0.6),
    "speed_breaker": (RAISED, 0.1, 0.5),
    "pole":          (STATIC, 2.5, 0.6),
    "tree":          (STATIC, 3.0, 0.6),
    "wall":          (STATIC, 2.0, 0.6),
    "barrier":       (STATIC, 1.0, 0.7),
    "dustbin":       (STATIC, 0.9, 0.5),
    "branch":        (HEAD,   0.5, 0.8),
    "signboard":     (HEAD,   0.6, 0.8),
    "construction":  (ZONE,   1.5, 0.8),
    "auto_rickshaw": (MOVING, 1.7, 0.9),
    # COCO classes (work with the stock yolov8n.pt)
    "person":        (MOVING, 1.65, 0.3),
    "bicycle":       (MOVING, 1.0, 0.6),
    "motorcycle":    (MOVING, 1.1, 0.85),
    "car":           (MOVING, 1.5, 0.9),
    "bus":           (MOVING, 3.0, 0.9),
    "truck":         (MOVING, 3.0, 0.9),
    "dog":           (MOVING, 0.6, 0.5),
    "cow":           (MOVING, 1.4, 0.7),
    "bench":         (STATIC, 0.8, 0.4),
    "chair":         (STATIC, 0.9, 0.4),
    "fire hydrant":  (STATIC, 0.8, 0.5),
    "stop sign":     (STATIC, 2.2, 0.5),
    "potted plant":  (STATIC, 0.6, 0.4),
    # Indoor / classroom objects (stock COCO model, good for the classroom demo)
    "backpack":      (STATIC, 0.45, 0.4),
    "suitcase":      (STATIC, 0.6, 0.5),
    "bottle":        (STATIC, 0.25, 0.3),
    "cup":           (STATIC, 0.12, 0.2),
    "laptop":        (STATIC, 0.25, 0.3),
    "cell phone":    (STATIC, 0.15, 0.2),
    "book":          (STATIC, 0.25, 0.2),
    "dining table":  (STATIC, 0.75, 0.6),
    "couch":         (STATIC, 0.85, 0.5),
    "bed":           (STATIC, 0.6, 0.5),
    "tv":            (STATIC, 0.6, 0.4),
    "umbrella":      (STATIC, 1.0, 0.4),
    "handbag":       (STATIC, 0.35, 0.3),
    "cat":           (MOVING, 0.3, 0.4),
    "traffic light": (HEAD,   1.0, 0.5),
}
# Vehicles that stand still are parked obstacles -> treated as static and remembered
PARKABLE = {"bicycle", "motorcycle", "car", "auto_rickshaw", "bus", "truck"}
