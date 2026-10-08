# AURALIS: presentation script (about 10 minutes + questions)

Three speakers: **A** (problem and idea), **B** (live demo), **C** (AI, location intelligence, paper). Change the split to fit your team.
Bring: the cane (Pi + webcam + ultrasonic + power bank), a phone with Bluetooth headphones, the projector showing the Pi screen, a chair and a bag as obstacles, and the IEEE draft (`docs/paper/auralis_ieee.pdf`) printed or on a laptop.

## Before mam arrives (10 minutes earlier)
1. Turn on the phone hotspot and power the Pi. Run `cd ~/Auralis-/pi && source venv/bin/activate && python server.py`. Check that you hear "AURALIS ready" and see `[camera] using USB webcam`.
2. On the projector, open `https://localhost:8443/` (Advanced → Proceed).
3. On the phone, scan the QR code, Proceed, allow location, tap the screen once, and connect the headphones.
4. Walk outside for one minute so the phone gets a GPS fix and the map shows the college.
5. Walk once past a fixed obstacle outside (bench, pole, parked bike) so the cane remembers it. This is what you show in part 4.

---

## 1. Problem (A, 1 minute)
> "Ma'am, about 2.2 billion people have a vision impairment, and the white cane is still the main aid. It only reaches one metre ahead. Smart canes add sensors, but all of them are *reactive*: they warn only when the obstacle is right in front, and they forget it immediately.
> A blind student walks the same route to the library every day. The same open drain is there every day. Today's canes discover it fresh every single time, two metres before it.
> Our idea: **a cane that remembers.**"

## 2. What we built (A, 1 minute), show the architecture figure (Fig. 1 in the paper)
> "AURALIS has two parts.
> On the cane, a Raspberry Pi 4 runs a **neural network, YOLOv8**, on a webcam to recognise obstacles, and an **ultrasonic sensor** gives the exact distance straight ahead.
> The user's **phone** connects to the cane. It adds **GPS**, speaks the alerts in **English, Hindi, Telugu or Tamil** into **Bluetooth headphones**, and keeps the **memory** of hazards and paths.
> Inside the phone there is a second **neural network** that fuses camera, ultrasonic and memory into one alert level."

## 3. Live demo: obstacle detection (B, 2 minutes)
B wears the headphones. Hand mam a second earphone, or turn the phone speaker on so she can hear.
1. Walk towards the chair.
   > Headphones: "Chair detected ahead, 2 metres."
   Point at the projector: the box on the camera view, the dot on the walking-corridor radar, the alert in the list.
2. Keep walking until it is very close.
   > "Stop. Chair very close."
3. A teammate steps in front.
   > "Person detected ahead."
   > "People and moving vehicles are announced but never stored in memory, because they move."
4. Hold the cane in front of a wall or a bag the camera does not know.
   > "Obstacle detected ahead, 1 metre." "The ultrasonic sensor catches things the camera cannot name."
5. Switch the language on the phone (top-right language button → தமிழ் / తెలుగు / हिन्दी) and repeat one obstacle.
6. Hold a hand over the ultrasonic sensor for 2 seconds.
   The app switches to *Paused* (the Pi also says "paused" when no phone is speaking).
   > "Hands-free pause, so a blind user never has to look at the phone."

## 4. Location intelligence (C, 2 minutes), Places and Memory tabs on the projector
> "Now the part that makes it different."
1. Show the **Places** map: it is our college, from the phone's real GPS. Point at the grey line: "This is the path we just walked. The cane builds its own map from the user's walks, with no Google Maps data."
2. Show the hazard on the map that it remembered when we walked past it earlier.
3. Show the **Memory** tab: "Each hazard has a risk bar. One sighting gives only 39% of full confidence; every time it is seen again the risk goes up; if it is not seen for a week the risk halves; and the user can say *hazard gone*."
4. Show the **Location intelligence** card:
   > "With the camera alone the user gets about 3 metres of warning. With memory the phone warns about 25 metres ahead: about 20 seconds instead of 2."
5. Show a saved place and the **Shortest vs Safest** route:
   > "When guiding to a saved place, our A* search treats risky paths as longer. On our test campus graph the safe route has 89% less risk for a longer walk." (Fig. 4 in the paper)

If you are indoors and GPS cannot move: Settings → **Classroom walk**. Say clearly: "This replays a recorded route at our college because GPS doesn't work indoors."

## 5. The AI (C, 1.5 minutes), Figs. 2, 3, 5 in the paper
> "There are two neural networks.
> **NN 1, YOLOv8n**, is a convolutional neural network that runs on the Pi itself, offline. It is pretrained on COCO, which knows people, vehicles, animals and furniture. For potholes, drains and stairs we have a training pipeline ready on Google Colab, with our own photos collected from the cane.
> **NN 2** is a small fusion network: 8 inputs (distance, drop, object type, confidence, size, position, memory risk, approach speed), two hidden layers of 16, and 4 outputs from safe to urgent. On a held-out test set it gets 89% accuracy and 93% recall on urgent cases, against 77% and 87% for plain distance rules.
> One safety rule sits above the network: a drop closer than 1.5 metres is *always* STOP."

## 6. Paper and next steps (C, 1 minute)
Hand over the IEEE draft.
> "We've written it up in IEEE conference format. The architecture, the memory model, routing and the fusion network are complete with figures. The orange parts are the field experiments we will run next: distance accuracy against a tape measure, alert delay, warning distance on a real route walked 5 times, and the custom pothole model."

## 7. Close (A, 20 seconds)
> "AURALIS: one Raspberry Pi, one camera, one ultrasonic sensor and the user's own phone and headphones, and a cane that warns 20 seconds earlier because it remembers."

---

## Questions mam may ask

**Is this AI or just if-else?**
Two trained neural networks: YOLOv8 (a CNN, millions of weights, object detection) on the Pi, and the fusion MLP (484 weights) on the phone. The rules are only the safety override and the fallback.

**Did you train the YOLO model yourselves?**
Not yet for our classes. Today it is the pretrained COCO model. The pipeline to fine-tune it on pothole, drain and stairs (`ml/AURALIS_train_yolo.ipynb`) is ready; that is our next step. Be honest here.

**What data was the fusion network trained on?**
Synthetic situations labelled by an expert rule set. That is why the paper calls the result preliminary. The app has a Research mode to label real walks and retrain it.

**How do you get distance from one camera?**
From how big the object looks compared with its usual real height, and from where it touches the ground given the camera height and tilt. The ultrasonic sensor gives the exact distance straight ahead and overrides the camera there.

**How accurate is GPS? Can memory be wrong?**
About 5–10 m outdoors. That's why hazards are merged within 8 m, need repeated sightings to reach full risk, and fade if not seen again. The warning says "about 20 metres ahead", not an exact position.

**What happens if the phone or the Wi-Fi disconnects?**
The Pi speaks the alerts itself through its own speaker. If the camera data stops, the phone says "camera link lost" and vibrates. It never goes silent without warning.

**Why not just use Google Maps?**
Google Maps doesn't know about the open drain on our campus path. Our cane learns it from use, and it works offline.

**Cost?**
Raspberry Pi 4, a USB webcam, an HC-SR04 sensor, a power bank and a PVC pipe. Put your real bill here: ₹ ____.

**What is novel compared with other smart canes?**
Memory of hazards with evidence and decay, a self-built map, risk-aware routing, and fusion of what the cane sees with what it remembers, all on minimal hardware.
