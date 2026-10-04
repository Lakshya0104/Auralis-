"""Neural network 1: YOLO object detector (CNN)."""
import os
import time

from config import MODELS, YOLO_MODEL, YOLO_IMGSZ, YOLO_CONF, CLASSES


class Detector:
    def __init__(self, simulate=False):
        self.model = None
        if simulate:
            return
        from ultralytics import YOLO
        path = YOLO_MODEL if os.path.exists(YOLO_MODEL) else str(MODELS / "yolov8n.pt")
        # an NCNN export runs ~2x faster on the Pi 4 (see README)
        ncnn = path.replace(".pt", "_ncnn_model")
        self.model = YOLO(ncnn if os.path.isdir(ncnn) else path, task="detect")
        print(f"[detector] loaded {path}")

    def detect(self, frame):
        """Returns [{cls, conf, box:(x1,y1,x2,y2)}] for classes in our taxonomy."""
        if self.model is None:
            return self._simulated()
        r = self.model.predict(frame, imgsz=YOLO_IMGSZ, conf=YOLO_CONF, verbose=False)[0]
        out = []
        for b in r.boxes:
            name = r.names[int(b.cls)]
            if name in CLASSES:
                out.append({"cls": name, "conf": float(b.conf), "box": tuple(float(v) for v in b.xyxy[0])})
        return out

    def _simulated(self):
        # a pole that slowly gets closer, and a person off to the right
        t = time.time() % 12
        bottom = 300 + t * 14
        return [{"cls": "pole", "conf": 0.82, "box": (290, bottom - 260, 330, bottom)},
                {"cls": "person", "conf": 0.9, "box": (520, 180, 600, 400)}]
