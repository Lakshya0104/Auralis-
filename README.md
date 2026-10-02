# AURALIS — a smart cane that remembers

AURALIS is a smart cane plus phone app for visually impaired users. Most smart canes only react to what is in front of them. AURALIS also **remembers**:

1. **Hazard memory.** Every confirmed hazard (pit, step-down, parked bike, pole…) is stored with its GPS location and time. It gets more weight each time it is seen again and fades over time (half-life of 7 days). The next time you walk that way, the cane warns you *before* the sensors can see it: "Careful. Remembered step down or pit, 15 metres ahead."
2. **Self-built map.** As you walk, the app quietly records your path as a graph. You don't need any map data, and it works inside campuses and lanes that OpenStreetMap doesn't cover.
3. **Safest route, not shortest.** You can save places by voice ("library", "bus stop"). To guide you there, A* runs on the learned graph with `cost = length × (1 + λ·risk)`, so it chooses a slightly longer route that avoids remembered hazards.
4. **Neural sensor fusion.** A small neural network (MLP 8→16→16→4) combines ultrasonic distance, the drop sensor, the camera's detection (class, confidence, size, position), approach speed and the memory risk into one alert level: safe, caution, warning or urgent.
5. **Multilingual voice.** English, Hindi, Telugu and Tamil, through phone or Bluetooth earphones, plus haptic patterns on the cane.
6. **Graceful fallback.** If the phone disconnects, the cane still vibrates on its own.

```
 ESP32 cane ──BLE──► Phone app (PWA) ──► earphones (voice) / cane motor (haptics)
 front + down        camera → COCO-SSD detector
 ultrasonic,         features → neural fusion → alert level
 button, motor       GPS + compass → hazard memory + walk graph → risk-aware A*
```

## Repo layout

| Path | What |
|---|---|
| `firmware/auralis_cane/auralis_cane.ino` | ESP32 firmware: 2 ultrasonic sensors, motor, button, BLE |
| `app/` | Phone app (plain HTML/JS, no build step) |
| `app/memory.js` | Spatio-temporal hazard memory, places, self-built walk graph |
| `app/router.js` | Risk-aware A* |
| `app/fusion.js` + `fusion_weights.json` | Neural fusion inference on the phone |
| `app/i18n.js` | Multilingual phrases + text-to-speech |
| `ml/train_fusion.py` | Trains the fusion network (numpy only) |
| `docs/paper_outline.md` | Research paper structure and experiments |

## Hardware (about ₹1,500–2,000)

| Part | Qty | Note |
|---|---|---|
| ESP32 DevKit (WROOM-32) | 1 | BLE + brains on the cane |
| HC-SR04 (or JSN-SR04T waterproof) | 2 | front at handle height, down at 35–45° near the tip |
| Coin vibration motor | 1–2 | in the handle |
| 2N2222/BC547 + 1 kΩ + 1N4007 diode | 1 each | motor driver (never drive a motor from a GPIO pin) |
| 1 kΩ + 2 kΩ resistors | 2 sets | divide the HC-SR04's 5 V echo down to 3.3 V |
| Push button, active buzzer (optional) | 1 | "where am I" button |
| Small power bank + USB cable | 1 | powers the ESP32 |
| PVC pipe / old cane, phone clip or chest mount | — | the phone camera faces forward |

**Wiring.** The ultrasonic sensors take VCC 5 V (from VIN/5V) and GND.

| Sensor | TRIG | ECHO | Motor | Buzzer | Button |
|---|---|---|---|---|---|
| Front | GPIO5 | GPIO18 (through divider) | | | |
| Down | GPIO19 | GPIO21 (through divider) | | | |
| ESP32 pin | | | GPIO25 → 1 kΩ → transistor base | GPIO26 | GPIO27 → GND |

For the motor, connect the transistor's emitter to GND, the collector to the motor's (−) lead, and the motor's (+) lead to 3.3 V/5 V. Put the diode across the motor.

## Running it

**Firmware.** In Arduino IDE, install the ESP32 boards, open `firmware/auralis_cane/auralis_cane.ino`, choose "ESP32 Dev Module" and upload. The motor buzzes twice when it boots.

**App.** Web Bluetooth and the camera both need HTTPS, so host it on GitHub Pages (Settings → Pages → this branch, `/app`). You can also run `npx http-server app` and use `chrome://inspect` port forwarding to `localhost`. Then:

1. Open the app in **Chrome on Android**. iOS Safari has no Web Bluetooth; there you would need the Bluefy browser.
2. Install the voice packs once: Settings → Text-to-speech → Google → install Hindi, Telugu and Tamil.
3. Tap Connect cane → Start walking, then save places and walk your demo routes once.

**Retraining the network.** Collect labelled rows in Research mode, then run:

```
pip install numpy
python ml/train_fusion.py --real auralis_training.csv
```

## 3-day plan

- **Day 1:** Wire the ESP32, both sensors and the motor, flash the firmware, and test distances with Serial Monitor. Host the app and connect over BLE.
- **Day 2:** Build the cane (PVC, mounts, phone clip). Walk 2 campus routes and save places. Put safe cardboard "obstacles" on the short route so hazards get remembered. Collect about 300 labelled rows and retrain.
- **Day 3:** Run the experiments in `docs/paper_outline.md`, take screenshots and a demo video, and write the paper.

## Honest limits (put these in the paper)

- COCO-SSD knows people, vehicles, animals, benches and similar objects. It does **not** know potholes. Those come from the downward ultrasonic "drop" detection. A custom YOLO pothole model is future work.
- Phone GPS is accurate to about ±5–10 m, which is fine for "hazard ahead" memory but not for precise sidewalk steering.
- The bootstrap network is trained on synthetic data labelled by expert rules. Your field data is what makes it a real learned model, so report both.
