# Demo day: build, set up and run AURALIS on the Raspberry Pi 4

This takes about 3–4 hours in total. Do the steps in order, and **test after each one**.

## What runs where

```
 PVC cane:  Pi Camera ──► Raspberry Pi 4 ──► voice out of HDMI (projector) or 3.5 mm earphones
            HC-SR04  ──►   (detects + speaks)  ──► app on the projector (Pi browser) and/or phone
```

- **Novelty 1, obstacle detection with voice, runs entirely on the Pi.** No phone or internet needed. The camera sees "chair", and the Pi says *"Chair detected ahead, 2 metres"* in English, Hindi, Telugu or Tamil.
- **Novelty 2, location memory, runs in the app.** It shows a map with remembered hazards and gives early warnings. Inside a classroom GPS can't move, so the **Classroom walk** switch replays a route on the map while the camera stays live.

## 1. Install Raspberry Pi OS (30 min, on a laptop)
1. Install **Raspberry Pi Imager** and choose *Raspberry Pi 4 → Raspberry Pi OS (64-bit)*. Pick the desktop version, not Lite.
2. Before writing the SD card, click **Edit settings**:
   - username `pi`, plus a password;
   - your phone hotspot's Wi-Fi name and password;
   - under *Services*, **Enable SSH**.
3. Write the SD card, put it in the Pi, and connect the micro-HDMI cable to a monitor or projector, plus a keyboard and mouse. Power it with a **5 V 3 A** USB-C supply or power bank.

## 2. Connect the camera (10 min, Pi switched OFF)
- Lift the black clip on the **CAMERA** connector, between the HDMI ports and the audio jack.
- Insert the ribbon with the **blue side facing the audio jack / USB ports**, then press the clip down.
- After booting, run `rpicam-hello -t 5000` in a terminal. A preview should appear for 5 seconds.

## 3. Wire the ultrasonic sensor (15 min, Pi switched OFF)

| HC-SR04 | Raspberry Pi pin |
|---|---|
| VCC | **Pin 2** (5 V) |
| GND | **Pin 6** (GND) |
| TRIG | **Pin 16** (GPIO23) |
| ECHO | **1 kΩ resistor → Pin 18** (GPIO24), plus a **2 kΩ resistor from Pin 18 to GND** (pin 14 or 20) |

**Never connect ECHO straight to the Pi.** It outputs 5 V and can damage the Pi. The two resistors bring it down to 3.3 V.

If you don't have a 2 kΩ resistor, use two 1 kΩ resistors in series.

Pin 1 is the one nearest the SD-card end of the 40-pin header, on the inner row. Pins 2, 4 and 6 are on the outer row.

## 4. Install the software (15 min, on the Pi)
Open a terminal and run:
```bash
git clone https://github.com/Lakshya0104/Auralis-.git
cd Auralis-/pi
bash setup_pi.sh
source venv/bin/activate
python check.py
```
`check.py` tests three things one by one:
1. **Voice:** you should hear "Speaker test".
2. **Ultrasonic:** the readings should change when you move your hand.
3. **Camera and detector:** it lists what it sees, for example `chair 0.81`.

**If there's no sound:** right-click the **speaker icon** at the top right of the Pi desktop and choose **HDMI** (projector) or **AV jack** (earphones). A Bluetooth speaker or earphones can be paired from the Bluetooth icon.

## 5. Mount everything on the PVC pipe (30 min)

Tape is fine for a classroom demo. Use **electrical (insulation) tape** or strong cloth tape, and add zip ties if you have them.

| Part | Where on the pipe | How |
|---|---|---|
| **Camera** | Top of the pipe, near the handle, about 80–90 cm from the floor, facing **forward**, tilted slightly down | Tape it to a small piece of cardboard first, then tape that to the pipe. **Don't put tape over the lens or bend the ribbon sharply.** |
| **HC-SR04** | Just below the camera, facing **straight forward**, the "eyes" level | Tape around the back and sides only. **The two round eyes must stay uncovered.** |
| **Raspberry Pi 4** | Near the handle, or in a small pouch / box taped to the pipe | Don't cover the Pi's chips with tape, because it gets hot. Leave the USB-C and HDMI ports reachable. |
| **Power bank** | Taped below the Pi, or in your pocket with a long cable | 5 V 3 A output. |
| **Wires** | Along the pipe | Tape every 10 cm so nothing catches. Leave some slack at the camera ribbon. |

After mounting, measure the camera's height from the floor and its tilt. Set them in `pi/config.py` as `CAM_HEIGHT_M` and `CAM_PITCH_DEG`. The sensor is set to face forward (`US_MODE = "front"`), which is best for the classroom.

## 6. Run the demo
```bash
cd ~/Auralis-/pi && source venv/bin/activate
python server.py --lang en      # or hi / te / ta
```
- The Pi says *"AURALIS ready"*. Walk the cane towards a chair, a bag or a person, and it says *"Chair detected ahead, 2 metres"*. Closer than 80 cm, it says *"Stop. Chair very close"*.
- **On the projector:** open Chromium on the Pi and go to `https://localhost:8443/`. Click *Advanced → Proceed* once. You'll see the app with the live corridor radar and alerts, and the camera view under "Camera view for a helper".
- **On a phone:** join the same hotspot and open `https://<pi-ip>:8443/`. The terminal prints the address.
- **For the location memory demo:** go to Settings and turn on **Classroom walk**. Tap **Start walking** and open **Places** to see the map of Chennai with paths, hazards and places. The cane announces remembered hazards about 25 m before reaching them, and **Memory → Location intelligence** shows how many seconds earlier that is than the camera.

The map background needs internet (the hotspot). Without it, the paths, hazards and places still draw on a plain background.

## 7. Suggested 5-minute demo script
1. **Problem:** ordinary smart canes only react to what is in front of them, and they forget it straight away.
2. **Novelty 1:**
   - Walk towards a chair: *"Chair detected ahead, 2 metres."*
   - Someone steps in front: *"Person detected ahead."*
   - Switch language with `--lang ta` (or the app's language setting) and repeat.
   - Point out that the neural network runs **on the Pi itself**, about 4–6 frames per second, offline.
3. **Novelty 2:** turn on Classroom walk and show the map. The cane warns about the remembered pothole 25 m early. Show the Memory screen: 25 m and 21 s early with memory, against about 3 m with the camera alone.
4. **Close:** cost is under ₹12k, it works offline, and it supports 4 languages.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Picamera2 unavailable` | Check the ribbon cable direction and run `rpicam-hello`. A USB webcam also works. |
| Ultrasonic always shows 300 cm | ECHO/TRIG are swapped, or the divider is wrong. Check pins 16 and 18. |
| No voice | Pick the audio output from the speaker icon, and test with `espeak-ng hello`. |
| Hindi/Telugu/Tamil sound robotic | That's espeak-ng. The phone's voice sounds better: run `python server.py --no-voice` and let the app speak. |
| Slow (under 2 fps) | Close other apps, use a 3 A power supply, and keep the Pi cool. |
| Phone can't open the page | The phone and Pi must be on the same hotspot. Use `https://`, not `http://`. |
