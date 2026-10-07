"""Neural network 1: YOLO object detector (CNN).

Default: the stock YOLOv8n (COCO, 80 classes) exported to ONNX (models/yolov8n.onnx, in the repo),
run with onnxruntime - no PyTorch needed on the Pi. If a custom model trained with
ml/AURALIS_train_yolo.ipynb is in models/, it is used instead (needs ultralytics).
"""
import os
import time

import cv2
import numpy as np

import sys

from config import YOLO_MODEL, YOLO_ONNX, YOLO_ONNX_FAST, YOLO_IMGSZ, YOLO_CONF, CLASSES

COCO = ["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
        "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
        "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
        "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
        "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
        "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard",
        "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
        "scissors", "teddy bear", "hair drier", "toothbrush"]


class OnnxYolo:
    def __init__(self, path, size=YOLO_IMGSZ):
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 4  # Pi 4 has 4 cores
        self.sess = ort.InferenceSession(path, opts, providers=["CPUExecutionProvider"])
        inp = self.sess.get_inputs()[0]
        self.input = inp.name
        self.size = inp.shape[2] if isinstance(inp.shape[2], int) else size   # e.g. 320 or 480, from the model file

    def __call__(self, frame, conf):
        h, w = frame.shape[:2]
        scale = self.size / max(h, w)
        nw, nh = int(w * scale), int(h * scale)
        canvas = np.full((self.size, self.size, 3), 114, np.uint8)       # letterbox
        top, left = (self.size - nh) // 2, (self.size - nw) // 2
        canvas[top:top + nh, left:left + nw] = cv2.resize(frame, (nw, nh))
        blob = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)[None].astype(np.float32) / 255
        out = self.sess.run(None, {self.input: blob})[0][0].T            # (anchors, 4 + classes)
        scores = out[:, 4:]
        cls = scores.argmax(1)
        best = scores[np.arange(len(cls)), cls]
        keep = best > conf
        if not keep.any():
            return []
        boxes, cls, best = out[keep, :4], cls[keep], best[keep]
        x1 = (boxes[:, 0] - boxes[:, 2] / 2 - left) / scale
        y1 = (boxes[:, 1] - boxes[:, 3] / 2 - top) / scale
        bw, bh = boxes[:, 2] / scale, boxes[:, 3] / scale
        # class-aware NMS: shift boxes of different classes apart so they never suppress each other
        offs = cls * 4096
        idx = cv2.dnn.NMSBoxes(np.stack([x1 + offs, y1, bw, bh], 1).tolist(), best.tolist(), conf, 0.45)
        res = []
        for i in np.array(idx).flatten():
            res.append((COCO[cls[i]], float(best[i]),
                        (float(max(x1[i], 0)), float(max(y1[i], 0)), float(min(x1[i] + bw[i], w)), float(min(y1[i] + bh[i], h)))))
        return res


class Detector:
    def __init__(self, simulate=False):
        self.model, self.ultra = None, None
        self.last_ms = 0
        if simulate:
            return
        if os.path.exists(YOLO_MODEL):
            from ultralytics import YOLO
            ncnn = YOLO_MODEL.replace(".pt", "_ncnn_model")
            self.ultra = YOLO(ncnn if os.path.isdir(ncnn) else YOLO_MODEL, task="detect")
            print(f"[detector] custom model {YOLO_MODEL}")
        else:
            path = YOLO_ONNX_FAST if "--fast" in sys.argv or not os.path.exists(YOLO_ONNX) else YOLO_ONNX
            self.model = OnnxYolo(path)
            print(f"[detector] COCO model {os.path.basename(path)} at {self.model.size}px (onnxruntime)")

    def detect(self, frame):
        """Returns [{cls, conf, box:(x1,y1,x2,y2)}] for classes in our taxonomy."""
        t0 = time.time()
        if self.ultra is not None:
            r = self.ultra.predict(frame, imgsz=YOLO_IMGSZ, conf=YOLO_CONF, verbose=False)[0]
            raw = [(r.names[int(b.cls)], float(b.conf), tuple(float(v) for v in b.xyxy[0])) for b in r.boxes]
        elif self.model is not None:
            raw = self.model(frame, YOLO_CONF)
        else:
            return self._simulated()
        self.last_ms = (time.time() - t0) * 1000
        return [{"cls": n, "conf": c, "box": b} for n, c, b in raw if n in CLASSES]

    def _simulated(self):
        # a chair that slowly gets closer, and a person off to the right
        t = time.time() % 12
        bottom = 300 + t * 14
        return [{"cls": "chair", "conf": 0.82, "box": (270, bottom - 150, 350, bottom)},
                {"cls": "person", "conf": 0.9, "box": (520, 180, 600, 400)}]
