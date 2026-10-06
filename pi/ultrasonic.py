"""HC-SR04 pointing down near the cane tip: learns normal ground distance, flags drops and raised ground."""
import random
import threading
import time

from config import US_MODE, US_TRIG_PIN, US_ECHO_PIN, DROP_DELTA_CM, RAISE_DELTA_CM


class Ultrasonic:
    def __init__(self, simulate=False):
        self.sensor = None
        if not simulate:
            try:
                from gpiozero import DistanceSensor
                self.sensor = DistanceSensor(echo=US_ECHO_PIN, trigger=US_TRIG_PIN, max_distance=3, queue_len=3)
            except Exception as e:
                print(f"[ultrasonic] not available ({e}); simulating")
        self.cm = None
        self.baseline = None
        self._t0 = time.time()
        threading.Thread(target=self._loop, daemon=True).start()

    def _read_cm(self):
        if self.sensor:
            return self.sensor.distance * 100
        if US_MODE == "front":   # simulation: a wall that comes from 2.5 m to 0.4 m every 15 s
            return max(40, 250 - ((time.time() - self._t0) % 15) * 20) + random.gauss(0, 1.5)
        # simulation: flat ground ~70 cm with noise, and a "pit" for 1.5 s every 20 s
        pit = (time.time() - self._t0) % 20 > 18.5
        return (100 if pit else 70) + random.gauss(0, 1.5)

    def _loop(self):
        while True:
            cm = self._read_cm()
            self.cm = cm
            # learn the normal cane-to-ground distance only from "normal-looking" readings
            if self.baseline is None:
                self.baseline = cm
            elif abs(cm - self.baseline) < RAISE_DELTA_CM:
                self.baseline = 0.95 * self.baseline + 0.05 * cm
            time.sleep(0.06)

    def state(self):
        if self.cm is None or self.baseline is None:
            return {"cm": None, "baseline": None, "drop": False, "raised": False, "mode": US_MODE}
        if US_MODE == "front":
            return {"cm": round(self.cm, 1), "baseline": None, "drop": False, "raised": False, "mode": "front"}
        delta = self.cm - self.baseline
        return {"cm": round(self.cm, 1), "baseline": round(self.baseline, 1),
                "drop": delta > DROP_DELTA_CM, "raised": delta < -RAISE_DELTA_CM, "mode": "down"}
