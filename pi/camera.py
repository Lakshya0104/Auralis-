"""Camera source: Pi Camera (Picamera2), else USB webcam (OpenCV), else a test video file."""
import cv2

from config import CAMERA, USB_CAMERA_INDEX, FRAME_W, FRAME_H


class Camera:
    def __init__(self, source=None):
        self.picam = None
        self.cap = None
        if isinstance(source, str) and source.isdigit():   # --video 0  = USB webcam via OpenCV
            source = int(source)
        if source is None and CAMERA == "usb":
            source = USB_CAMERA_INDEX
        if source is None:
            try:
                from picamera2 import Picamera2
                self.picam = Picamera2()
                self.picam.configure(self.picam.create_video_configuration(
                    main={"size": (FRAME_W, FRAME_H), "format": "RGB888"}))
                self.picam.start()
                return
            except Exception as e:  # not on a Pi, or camera not enabled
                print(f"[camera] Picamera2 unavailable ({e}); trying USB webcam")
                source = 0
        self.cap = cv2.VideoCapture(source, cv2.CAP_V4L2) if isinstance(source, int) else cv2.VideoCapture(source)
        if isinstance(source, int):
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # faster on USB webcams
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        self.loop_file = isinstance(source, str)
        if not self.cap.isOpened():
            print(f"[camera] could not open {source}")

    def read(self):
        """Returns a BGR frame of FRAME_W x FRAME_H, or None."""
        if self.picam:
            frame = self.picam.capture_array()  # RGB888 in Picamera2 is BGR byte order
            return frame if frame.ndim == 3 else None
        ok, frame = self.cap.read()
        if not ok and self.loop_file:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
        if not ok:
            return None
        return cv2.resize(frame, (FRAME_W, FRAME_H))
