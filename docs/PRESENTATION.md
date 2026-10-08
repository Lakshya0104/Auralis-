# AURALIS: what to present

## One line
A smart cane for visually impaired people. A Raspberry Pi on the cane **sees** obstacles with neural networks, the user's **phone** speaks them into **Bluetooth headphones** in English, Hindi, Telugu or Tamil, and the cane **remembers** hazards at their real **GPS** position so it can warn before the camera sees them.

## System
```
 CANE (Raspberry Pi 4)                         PHONE (Chrome, opened from the Pi)          HEADPHONES
 camera ─► YOLOv8 CNN (NN 1) ─► distance        ─wss─►  fusion network (NN 3) ─► alert ─►  voice, 4 languages
 ultrasonic HC-SR04 ───────────► exact range            GPS + compass                      + vibration
 ─► obstacle: what, how far, left/ahead/right           hazard memory at GPS position
    in the path?, coming closer?                        self-learned path map + safest route (A*)
                     ◄── memory saved on the Pi ───     PROJECTOR: map follows the phone live
```

## What each part does (all of it runs, offline except the map background)
| Part | How | Where in the code |
|---|---|---|
| Object detection (AI) | YOLOv8n convolutional neural network, ONNX, about 4–6 frames/s on the Pi | `pi/detector.py` |
| Distance from one camera | object size + camera geometry; ultrasonic gives the exact distance straight ahead | `pi/distance.py`, `pi/perception.py` |
| Obstacle taxonomy | drop, raised, static, head height, moving; parked vehicle = static after 3 s | `pi/config.py` |
| Hazard level (AI) | small neural network (8 inputs → safe / caution / warning / urgent); a close drop is always STOP | `app/fusion.js`, `ml/train_fusion.py` |
| Voice | Pi decides what to say; the phone speaks it into headphones (the Pi speaks if no phone) | `pi/speaker.py`, `app/app.js` |
| Location intelligence | phone GPS; hazards stored at their position, confirmed by repeat sightings, risk halves every week it is not seen again | `app/memory.js` |
| Early warning | remembered hazard announced ~25 m ahead (~20 s) vs ~3 m when the camera sees it | `app/app.js` |
| Safest route | path map learned from walks; A* where risky segments cost more | `app/router.js` |
| Hands-free | hold a hand over the sensor 2 s to pause / resume | `pi/server.py` |

## Honest limits (say them before you are asked)
- The detector is the standard COCO model: people, vehicles, animals, chairs, benches, bags and similar. **Potholes, drains and stairs need our own trained model.** The training pipeline is ready (`ml/AURALIS_train_yolo.ipynb`, free Colab GPU, about 1 hour) and the cane loads it automatically when the file is in `pi/models/`. The ultrasonic sensor already catches anything close ahead that the camera does not recognise.
- The fusion network was first trained on data generated from expert rules. *Research mode* in the app records real labelled walks to retrain it (`python ml/train_fusion.py --real auralis_training.csv`).
- GPS is accurate to about 5–10 m outdoors and weak indoors. Indoors, *Classroom walk* replays a route on the map (clearly a simulation) while the camera stays live.
- The phone app is a web app served by the Pi, not a Play Store app. It needs Chrome and one "Proceed" tap for the Pi's own certificate.

## Next steps
1. Train the custom detector on pothole / drain / stairs / curb photos (Indian roads datasets + our own photos from `pi/capture.py`).
2. Collect labelled walks and retrain the fusion network on real data.
3. Measure: detection accuracy on our test photos, distance error vs tape measure, warning lead time with and without memory.
