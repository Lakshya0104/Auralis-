"""Camera source: Pi Camera (Picamera2), else USB webcam (OpenCV), else a test video file."""
import pathlib
import time

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
        self.loop_file = isinstance(source, str)
        self.fails = 0
        if self.loop_file:
            self.cap = cv2.VideoCapture(source)
            print(f"[camera] {'using ' + source if self.cap.isOpened() else 'could not open ' + source}")
        else:
            self.want = source
            self.cap = self._find_webcam(source)

    @staticmethod
    def _open(index):
        cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
        if not cap.isOpened():
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        for _ in range(5):                       # the first frames can be empty while it wakes up
            ok, frame = cap.read()
            if ok and frame is not None and frame.ndim == 3:
                return cap
            time.sleep(0.1)
        cap.release()
        return None

    def _find_webcam(self, first):
        """USB webcam: the configured number first, then every /dev/video* (on a Pi 4, numbers 10-23
        are the Pi's own video chip, so the webcam is not always number 0)."""
        others = sorted(int(p.name[5:]) for p in pathlib.Path("/dev").glob("video*") if p.name[5:].isdigit())
        for index in [first] + [i for i in others if i != first]:
            cap = self._open(index)
            if cap:
                print(f"[camera] using USB webcam /dev/video{index}")
                return cap
        print("[camera] NO WEBCAM FOUND. Check: is it plugged into the Pi (blue USB port)? Run: ls /dev/video*")
        return None

    def read(self):
        """Returns a BGR frame of FRAME_W x FRAME_H, or None."""
        if self.picam:
            frame = self.picam.capture_array()  # RGB888 in Picamera2 is BGR byte order
            return frame if frame.ndim == 3 else None
        ok, frame = self.cap.read() if self.cap else (False, None)
        if not ok and self.loop_file and self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
        if not ok:
            # webcam unplugged or not found yet: look for it again every ~3 s, so plugging it in just works
            self.fails += 1
            if not self.loop_file and self.fails % 15 == 0:
                if self.cap:
                    self.cap.release()
                self.cap = self._find_webcam(self.want)
            return None
        self.fails = 0
        return cv2.resize(frame, (FRAME_W, FRAME_H))
