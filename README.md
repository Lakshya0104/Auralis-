# AURALIS: a smart cane that remembers

> **Building the demo? Start with [`docs/DEMO_DAY.md`](docs/DEMO_DAY.md):** Pi setup, wiring, mounting and the demo script.

A smart white cane for visually impaired users. A Raspberry Pi 4 with a camera sees obstacles, and the user's phone speaks them in **English, Hindi, Telugu or Tamil** through Bluetooth earphones. Unlike reactive smart canes, AURALIS **remembers** where hazards are, warns about them before they're even in view, and routes around them.

Design and research plan: [`docs/AURALIS_Research_and_Design_Plan.pdf`](docs/AURALIS_Research_and_Design_Plan.pdf) · Paper outline: [`docs/paper_outline.md`](docs/paper_outline.md) · Dataset guide: [`docs/DATASET_GUIDE.md`](docs/DATASET_GUIDE.md)

**The phone app** has four screens: Walk, Places, Memory and Settings. Every screen is translated into all 4 languages, and you pick one the first time you open it. Without a Pi connected, it runs in *demo mode* with simulated cane data, so you can show it anywhere.

## How it works

```
 Pi 4 on the cane (pi/)                                  Phone (app/, opened from the Pi)
 ───────────────────────                                 ─────────────────────────────────
 Camera ─► YOLO (NN 1) ─► distance: ground geometry      GPS + compass
                          + MiDaS depth (NN 2)    ─wss─► fusion network (NN 3) ─► alert level
 HC-SR04 (down) ─► drop / step detection                 voice (4 languages) + vibration
 ─► obstacle list: class, category, distance,            hazard memory (decay + repeat evidence)
    side, in-corridor?, approach speed                   self-learned path map + safest-route A*
```

**Obstacle** means anything inside the 1 m wide walking corridor, from the ground up to head height, within 4 m. Each detected class belongs to one category, set in `pi/config.py`:

| Category | Classes | Remembered? |
|---|---|---|
| drop | pothole, open_drain, stairs_down, curb + ultrasonic "drop" | yes; always **STOP** |
| raised | stairs_up, speed_breaker + ultrasonic "step up" | yes |
| static | pole, tree, wall, barrier, dustbin, bench, chair, parked vehicles | yes |
| head | branch, signboard, anything high in the frame and close | yes |
| moving | person, bicycle, motorcycle, car, auto_rickshaw, bus, truck, dog, cow | no (announced only) |
| zone | construction | yes |

A vehicle that has been standing still for 3 s counts as parked (static), so it gets remembered.

## Repo layout

| Path | What |
|---|---|
| `pi/server.py` | Main program on the Pi: camera → perception → HTTPS + WebSocket server |
| `pi/detector.py` | YOLO wrapper (custom model or stock COCO) |
| `pi/distance.py` | Distance from one camera: ground-plane geometry, known size, MiDaS depth |
| `pi/perception.py` | Taxonomy, walking corridor, tracking / approach speed, parked-vehicle logic |
| `pi/ultrasonic.py` | HC-SR04 drop / step detection with self-learning ground baseline |
| `pi/config.py` | **All settings**: camera height/tilt, pins, classes, thresholds |
| `app/` | Phone web app: voice, memory, routing, fusion network, corridor radar, demo mode |
| `pi/capture.py` | Collect training photos from the cane camera while walking |
| `ml/AURALIS_train_yolo.ipynb` | **Colab notebook:** download, merge, train, evaluate and export the detector |
| `ml/merge_datasets.py` | Merge Roboflow / Kaggle / own datasets into AURALIS class ids |
| `ml/train_yolo.py` | Fine-tune YOLO on our classes |
| `ml/train_fusion.py` | Train the fusion network |

## Setup

### 1. Hardware
- **Camera:** on the handle, about 90 cm high, tilted about 20° down. Measure yours and set `CAM_HEIGHT_M` / `CAM_PITCH_DEG` in `pi/config.py`, because distances depend on it.
- **HC-SR04:** about 30–40 cm above the tip, pointing 35–45° down. Wiring: VCC → pin 2 (5 V), GND → pin 6, TRIG → GPIO23 (pin 16). ECHO goes through **1 kΩ** to GPIO24 (pin 18), with **2 kΩ** from GPIO24 to GND. The ECHO pin is 5 V, so never connect it straight to the Pi.
- **Power:** a power bank rated 5 V 3 A into the Pi's USB-C.

### 2. Pi software (once)
Install Raspberry Pi OS 64-bit (Bookworm) and make sure the camera works (`rpicam-hello`). Then:
```bash
git clone https://github.com/Lakshya0104/Auralis-.git && cd Auralis-/pi
bash setup_pi.sh
```

### 3. Run
1. Turn on the **phone's hotspot** and connect the Pi to it (set up Wi-Fi once in `raspi-config`).
2. On the Pi:
   ```bash
   cd Auralis-/pi && source venv/bin/activate && python server.py
   ```
   It prints `Open on the phone: https://<ip>:8443/`.
3. On the phone, open that address in **Chrome**. It shows a certificate warning because the Pi uses its own certificate: tap *Advanced → Proceed*. This is needed because GPS and the microphone only work over HTTPS.
4. Pick a language, connect your Bluetooth earphones, and tap **Start walking**.
5. Optional, to run it automatically at boot: `crontab -e` and add `@reboot cd /home/pi/Auralis-/pi && venv/bin/python server.py`.

Install the voice packs once on the phone: Settings → Text-to-speech → Google → install Hindi, Telugu and Tamil.

### Testing without the Pi
```bash
cd pi && pip install aiohttp numpy opencv-python-headless onnxruntime
python server.py --simulate          # fake pole + person + a pit every 20 s
python server.py --video walk.mp4    # run the real model on a recorded video (needs ultralytics)
```

## Training the neural networks

**NN 1, YOLO (custom classes).** The stock model already knows people, vehicles and animals. For pothole, drain, stairs, curb, pole and similar classes, follow [`docs/DATASET_GUIDE.md`](docs/DATASET_GUIDE.md):
1. Collect your own photos with `pi/capture.py`.
2. Combine them with public datasets from Roboflow or Kaggle.
3. Run [`ml/AURALIS_train_yolo.ipynb`](ml/AURALIS_train_yolo.ipynb) on a free Colab GPU (about 1 hour).
4. Unzip the result into `pi/models/`.

**NN 2, MiDaS depth.** It's pre-trained, and `setup_pi.sh` downloads it. Its relative depth is scaled to metres every frame using the geometric estimates.

**NN 3, fusion MLP.** Train it with `python ml/train_fusion.py`, or with `--real auralis_training.csv` once you've labelled field data in the app's *Research mode*.

## Safety rules built in
- A drop or pit closer than 1.5 m is always **STOP**. The network can raise an alert level but never lower this one.
- If the Pi stream stops for more than 3 s, the phone says "Camera link lost" and vibrates. It never goes silent without warning.
- People and moving vehicles are never stored as hazards.
