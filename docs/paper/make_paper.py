"""Build the IEEE-style conference paper:   python docs/paper/make_paper.py

Real measurements from the cane (pi/measure.py -> docs/paper/results.json) are used when present.
Without them, the distance / Pi-latency cells show values projected from the sensor datasheet and
the laptop benchmark, and are marked "projected" in the paper.
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (BaseDocTemplate, Frame, FrameBreak, Image, KeepTogether, NextPageTemplate,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

HERE = pathlib.Path(__file__).resolve().parent
FIG = HERE / "fig"
FIG.mkdir(exist_ok=True)
OUT = HERE.parent / "AURALIS_IEEE_Paper.pdf"
RES_FILE = HERE / "results.json"
RES = json.loads(RES_FILE.read_text()) if RES_FILE.exists() else None

# ---------------- measured values (this repository) ----------------
CONF = [[1090, 81, 1, 1], [89, 1365, 81, 2], [4, 92, 650, 36], [0, 2, 29, 477]]   # ml/train_fusion.py, test split
ACC, URGENT_RECALL = 0.895, 0.939
LAPTOP_MS = {320: 13, 480: 27}                    # ONNX Runtime, 4-core x86 CPU, 640x480 frame
EARLY_M, EARLY_S, CAMERA_M = 25, 21, 3.0          # app route simulation

# ---------------- distance table: measured or projected ----------------
TRUE = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
if RES:
    DIST = [(r["true_m"], r["camera_m"], r["ultrasonic_m"], r["detection_rate"]) for r in RES["distance"]]
    PI_MS = f'{RES["detector_ms_median"]:.0f} ms (median), {RES["detector_ms_p95"]:.0f} ms (95th pct.)'
    DIST_NOTE = f'Measured on {RES["measured_on"]} with a {RES["object"]}, 20 frames per distance (median).'
    projected = False
else:
    # Projection: HC-SR04 datasheet accuracy +-3 mm (2-400 cm); camera size model error = relative error of the
    # assumed object height (+-10 %), so the camera band is true +-10 %. Detection rate falls with distance
    # as the object occupies fewer pixels at 480 px input.
    DIST = [(d, d, d, rate) for d, rate in zip(TRUE, [1.0, 1.0, 1.0, 0.95, 0.9, 0.85])]
    PI_MS = "~220 ms"
    DIST_NOTE = ("Projected: ultrasonic from the HC-SR04 datasheet (+-3 mm); camera band = +-10 % from object-height "
                 "variation in the size model. Replace by running pi/measure.py on the cane.")
    projected = True


# ---------------- figures ----------------
def fig_architecture():
    fig, ax = plt.subplots(figsize=(3.5, 2.3), dpi=250)
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.6); ax.axis("off")
    boxes = [
        (0.1, 3.7, 2.7, 2.6, "SENSE", "USB webcam\nHC-SR04\nPhone GPS", "#e8f3f1", "#0f5f58"),
        (3.5, 3.7, 3.0, 2.6, "THINK (Pi 4)", "YOLOv8n (ONNX)\nDistance + corridor\nHazard memory", "#0e1a1c", "#7fd3c7"),
        (7.2, 3.7, 2.7, 2.6, "SPEAK", "Neural TTS\n4 languages\nPhone app", "#fbe8ea", "#c3202e"),
        (1.4, 0.2, 7.2, 2.4, "LOCATION INTELLIGENCE", "risk memory (decay + repeat evidence)\nself-learned path graph + risk-aware A*", "#f4f7f6", "#0f5f58"),
    ]
    for x, y, w, h, title, body, fc, tc in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.25", fc=fc, ec=tc, lw=1.2))
        ax.text(x + w / 2, y + h - 0.45, title, ha="center", va="center", fontsize=6.5, weight="bold",
                color=tc if fc != "#0e1a1c" else "#7fd3c7", family="DejaVu Sans")
        ax.text(x + w / 2, y + h / 2 - 0.35, body, ha="center", va="center", fontsize=5.6,
                color="#eef3f2" if fc == "#0e1a1c" else "#1a2a2c", linespacing=1.4)
    for x0, x1 in [(2.85, 3.45), (6.55, 7.15)]:
        ax.annotate("", (x1, 5.0), (x0, 5.0), arrowprops=dict(arrowstyle="-|>", color="#0f5f58", lw=1.2))
    ax.annotate("", (5.0, 2.65), (5.0, 3.65), arrowprops=dict(arrowstyle="<|-|>", color="#0f5f58", lw=1.0))
    fig.savefig(FIG / "architecture.png", bbox_inches="tight", pad_inches=0.02); plt.close(fig)


def fig_confusion():
    import numpy as np
    m = np.array(CONF, float); m = m / m.sum(1, keepdims=True)
    fig, ax = plt.subplots(figsize=(2.6, 2.3), dpi=250)
    ax.imshow(m, cmap="GnBu", vmin=0, vmax=1)
    labels = ["Safe", "Caution", "Warning", "Urgent"]
    ax.set_xticks(range(4), labels, fontsize=6); ax.set_yticks(range(4), labels, fontsize=6)
    ax.set_xlabel("Predicted", fontsize=6.5); ax.set_ylabel("True", fontsize=6.5)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", fontsize=6, color="white" if m[i, j] > 0.5 else "#1a2a2c")
    fig.tight_layout(); fig.savefig(FIG / "confusion.png"); plt.close(fig)


def fig_distance():
    fig, ax = plt.subplots(figsize=(3.3, 2.0), dpi=250)
    t = [r[0] for r in DIST]
    ax.plot([0, 3.3], [0, 3.3], color="#9aa4a8", lw=0.8, ls="--", label="ideal")
    cam = [r[1] for r in DIST]
    if projected:
        ax.fill_between(t, [d * 0.9 for d in t], [d * 1.1 for d in t], color="#0f5f58", alpha=0.18, label="camera (projected ±10%)")
        ax.plot(t, [r[2] for r in DIST], "o-", color="#c3202e", ms=3, lw=1, label="ultrasonic (datasheet)")
    else:
        ax.plot(t, cam, "s-", color="#0f5f58", ms=3, lw=1, label="camera size model")
        ax.plot(t, [r[2] for r in DIST], "o-", color="#c3202e", ms=3, lw=1, label="ultrasonic")
    ax.set_xlabel("True distance (m)", fontsize=6.5); ax.set_ylabel("Estimated (m)", fontsize=6.5)
    ax.tick_params(labelsize=6); ax.legend(fontsize=5.5, frameon=False); ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout(); fig.savefig(FIG / "distance.png"); plt.close(fig)


def fig_early():
    fig, ax = plt.subplots(figsize=(3.3, 1.35), dpi=250)
    ax.barh(["Camera only", "With memory"], [CAMERA_M, EARLY_M], color=["#9aa4a8", "#0f5f58"], height=0.55)
    for y, v, s in [(0, CAMERA_M, f"{CAMERA_M:.0f} m"), (1, EARLY_M, f"{EARLY_M} m  (~{EARLY_S} s earlier)")]:
        ax.text(v + 0.4, y, s, va="center", fontsize=6)
    ax.set_xlim(0, 34); ax.set_xlabel("Warning distance before the hazard (m)", fontsize=6.5)
    ax.tick_params(labelsize=6); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "early.png"); plt.close(fig)


for f in (fig_architecture, fig_confusion, fig_distance, fig_early):
    f()

# ---------------- styles ----------------
T = "Times-Roman"; TB = "Times-Bold"; TI = "Times-Italic"
S = {
    "title": ParagraphStyle("title", fontName=T, fontSize=21, leading=25, alignment=TA_CENTER, spaceAfter=10),
    "auth": ParagraphStyle("auth", fontName=T, fontSize=10, leading=12, alignment=TA_CENTER),
    "authi": ParagraphStyle("authi", fontName=TI, fontSize=9, leading=11, alignment=TA_CENTER),
    "abs": ParagraphStyle("abs", fontName=TB, fontSize=9, leading=10.6, alignment=TA_JUSTIFY, spaceAfter=6),
    "body": ParagraphStyle("body", fontName=T, fontSize=10, leading=11.6, alignment=TA_JUSTIFY, firstLineIndent=10, spaceAfter=3),
    "h1": ParagraphStyle("h1", fontName=T, fontSize=10, leading=12, alignment=TA_CENTER, spaceBefore=8, spaceAfter=4),
    "h2": ParagraphStyle("h2", fontName=TI, fontSize=10, leading=12, spaceBefore=5, spaceAfter=2),
    "cap": ParagraphStyle("cap", fontName=T, fontSize=8, leading=9.4, alignment=TA_JUSTIFY, spaceBefore=3, spaceAfter=8),
    "tcap": ParagraphStyle("tcap", fontName=T, fontSize=8, leading=9.4, alignment=TA_CENTER, spaceBefore=6, spaceAfter=3),
    "eq": ParagraphStyle("eq", fontName=TI, fontSize=9.5, leading=12, alignment=TA_CENTER, spaceBefore=3, spaceAfter=5),
    "ref": ParagraphStyle("ref", fontName=T, fontSize=8, leading=9.4, leftIndent=14, firstLineIndent=-14, spaceAfter=2),
}
P = lambda t, s="body": Paragraph(t, S[s])
H = lambda n, t: P(f"{n}. {t.upper()}", "h1")
H2 = lambda n, t: P(f"{n}. {t}", "h2")
COLW = 3.45 * inch


def table(rows, widths, cap):
    t = Table(rows, colWidths=widths, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), T, 7.6), ("FONT", (0, 0), (-1, 0), TB, 7.6),
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black), ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black), ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
    ]))
    return KeepTogether([P(cap, "tcap"), t, Spacer(1, 6)])


def figure(path, cap, width=COLW):
    from PIL import Image as PI
    w, h = PI.open(path).size
    return KeepTogether([Image(str(path), width=width, height=width * h / w), P(cap, "cap")])


# ---------------- content ----------------
story = []
story += [P("AURALIS: A Low-Cost Smart Cane with On-Device Neural Hazard Detection, Multilingual Neural Speech, "
            "and Spatio-Temporal Hazard Memory", "title"),
          P("Team AURALIS", "auth"),
          P("Department of Computer Science and Engineering — Artificial and Neural Networks Capstone", "authi"),
          Spacer(1, 4), P("Code: github.com/Lakshya0104/Auralis-", "authi"),
          FrameBreak(), NextPageTemplate("later")]

story += [P("<i>Abstract</i>—Conventional white canes and most smart canes are reactive: they report what is "
            "in front of the user and forget it immediately. We present AURALIS, a smart cane built from a Raspberry Pi 4, "
            "a USB webcam and one ultrasonic sensor, mounted on a PVC shaft for about Rs. 8,300. A YOLOv8n convolutional "
            "network runs on the cane's CPU through ONNX Runtime and recognizes 80 everyday object classes; a size-based "
            "monocular distance model, corrected by the ultrasonic range when the object is straight ahead, gives the "
            "distance, and the image position gives the side. Alerts are spoken in English, Hindi, Telugu and Tamil with "
            "neural text-to-speech that is cached on the device for offline replay, and can be streamed to the user's phone "
            "and Bluetooth headphones. A small multilayer perceptron fuses eight features into four alert levels "
            "(accuracy 0.895, urgent recall 0.939 on a held-out test set). Our main contribution is location "
            "intelligence: each confirmed static hazard is stored with its GPS position and weighted by repeated "
            "evidence and temporal decay; the cane then warns from memory about 25 m before a known hazard, versus "
            "about 3 m for the camera alone, and a risk-aware A* search over a self-learned path graph prefers safer routes. "
            "The system is hands-free: holding a hand at the sensor for two seconds pauses or resumes it.", "abs"),
          P("<i>Index Terms</i>—assistive technology, smart cane, object detection, YOLO, edge AI, sensor fusion, "
            "multilayer perceptron, neural text-to-speech, hazard memory, risk-aware routing.", "abs")]

story += [H("I", "Introduction"),
          P("About 2.2 billion people live with a vision impairment, and at least 43 million are blind [1]. The white "
            "cane remains the most used mobility aid because it is cheap and reliable, yet it senses only what its tip "
            "touches: head-level obstacles such as signboards and branches are missed, fast objects arrive before they "
            "can be felt, and the same hazard on a daily route must be rediscovered every time. Most electronic aids "
            "also speak only English, which excludes many users in India."),
          P("Recent smart canes add ultrasonic sensors, cameras and deep-learning detectors [5]–[7], [12], [13], but they "
            "remain reactive: detections are announced and discarded. AURALIS keeps what it detects. Its contributions "
            "are: (1) an on-device neural hazard-detection pipeline that speaks the object, side and distance in four "
            "languages; (2) a spatio-temporal hazard memory with repeated-evidence and decay weighting that warns "
            "before the hazard is visible; (3) a self-learned pedestrian graph with risk-aware routing; (4) a minimal, "
            "hands-free, low-cost hardware design; and (5) an open implementation.")]

story += [H("II", "Related Work"),
          P("Commercial devices such as the WeWALK cane [6] add ultrasonic head-level detection and app navigation. "
            "The Stanford Augmented Cane [5] combines LiDAR, SLAM and a motorized wheel and increased walking speed by "
            "about 20%, at the cost of weight and complexity. Camera-based canes use YOLO detectors with ultrasonic or "
            "depth sensing [7], [12], [13]. Crowdsourced accessibility maps exist, but they are not fused with live "
            "detections or weighted over time. To our knowledge, none of these systems turn on-device detections into "
            "a decaying, evidence-weighted hazard memory that drives early warnings and route choice.")]

story += [figure(HERE / "img" / "cane_front.jpg", "Fig. 1. AURALIS prototype: Logitech USB webcam at the handle, HC-SR04 "
                 "ultrasonic sensor below it on a breadboard (with the 1 kΩ/2 kΩ divider), and the Raspberry Pi 4 "
                 "mounted on the PVC shaft.", width=COLW * 0.62)]

story += [H("III", "System Design"),
          H2("A", "Hardware"),
          P("The cane carries a Raspberry Pi 4 (4 GB), a Logitech USB webcam (640×480) at about 0.9 m, and an HC-SR04 "
            "ultrasonic sensor facing forward. The sensor's 5 V echo is reduced to 3.3 V with a 1 kΩ/2 kΩ divider into "
            "GPIO24; the trigger is GPIO23. A 5 V/3 A power bank powers the Pi. The phone supplies GPS, the app and "
            "headphone audio. Table I lists the parts."),
          table([["Part", "Role", "Cost (Rs.)"],
                 ["Raspberry Pi 4 (4 GB)", "Inference, voice, memory", "6,000"],
                 ["Logitech USB webcam", "Vision, 640×480", "800"],
                 ["HC-SR04 + divider", "Range, hand gesture", "100"],
                 ["Power bank 5 V/3 A", "Power", "1,200"],
                 ["PVC pipe, breadboard, wires", "Body", "200"],
                 ["Total", "", "8,300"]], [1.35 * inch, 1.45 * inch, 0.6 * inch], "TABLE I<br/>HARDWARE AND COST"),
          figure(FIG / "architecture.png", "Fig. 2. Architecture. The Pi senses, detects and speaks; location "
                 "intelligence stores hazards and plans routes; the phone app shows the map and plays the voice."),
          H2("B", "Neural Hazard Detection"),
          P("Each frame is letterboxed to 480×480 and passed to YOLOv8n [2], [3] (3.2 M parameters, pre-trained on "
            "COCO [4]) exported to ONNX and run with ONNX Runtime [11] on four CPU threads, without PyTorch on the device. "
            "Class-aware non-maximum suppression (IoU 0.45, confidence 0.40) produces boxes. Classes are mapped to a "
            "hazard taxonomy: <i>drop</i> (pothole, drain, stairs down), <i>raised</i>, <i>static</i> (chair, table, pole, "
            "bag, parked vehicle), <i>head-level</i> (branch, signboard) and <i>moving</i> (person, bicycle, car, dog). "
            "An object is announced only if it overlaps the middle third of the image (the 1 m walking corridor), is "
            "within 3 m, and appears in at least two of the last three frames, which suppresses one-frame false alarms."),
          H2("C", "Monocular Distance and Ultrasonic Fusion"),
          P("With a pinhole camera of horizontal field of view θ and image width W, the focal length in pixels is "
            "f = (W/2)/tan(θ/2). An object of typical real height H that appears h pixels tall is at"),
          P("d<sub>cam</sub> = H · f / h ,", "eq"),
          P("which needs no knowledge of the camera's height or tilt. θ is calibrated once by measuring a person at 2 m "
            "(<i>calibrate.py</i>). A box that touches both the top and bottom of the image is larger than the view and "
            "is reported as very close (≤ 0.6 m). When the object is in the center third and the ultrasonic range r "
            "agrees within 1 m, d = r replaces d<sub>cam</sub>; an ultrasonic return between 12 cm and 1 m with no "
            "recognized object is announced as a generic obstacle. The side is left, ahead or right from the box "
            "center's position in thirds of the image."),
          H2("D", "Neural Sensor Fusion"),
          P("A multilayer perceptron (8–16–16–4, ReLU, softmax) maps eight features — normalized distance, drop "
            "signal, class severity, confidence, box area, center offset, memory risk and approach speed — to four "
            "alert levels (safe, caution, warning, urgent). It is trained with cross-entropy and Adam [10] on 20,000 "
            "samples generated from expert rules with 3% label noise, and runs in the phone app. A safety override "
            "forces <i>urgent</i> for any drop closer than 1.5 m; the network may raise, but never lower, this level."),
          figure(FIG / "confusion.png", f"Fig. 3. Normalized confusion matrix of the fusion MLP on 4,000 held-out "
                 f"samples (accuracy {ACC}, urgent recall {URGENT_RECALL}).", width=COLW * 0.8),
          H2("E", "Location Intelligence"),
          P("Every hazard announced at warning level or above, except moving objects, is stored at the user's GPS "
            "position projected d meters along the heading, merged with any record of the same class within 8 m. "
            "With n sightings, age a days, class severity s and confidence c, its risk is"),
          P("risk = s · (1 − e<sup>−n/2</sup>) · 0.5<sup>a/7</sup> · c ,", "eq"),
          P("so repeated sightings strengthen a hazard and an unconfirmed one halves every week; the user can also "
            "clear it. GPS breadcrumbs every 5 m (nodes merged within 6 m) form a pedestrian graph learned from the "
            "user's own walks. Routes to saved places use A* [9] with edge cost"),
          P("cost = ℓ · (1 + λ · Σ risk) ,", "eq"),
          P("summing the risk of hazards within 10 m of the edge (λ = 4). While walking, remembered hazards within "
            "25 m and ±45° of the heading are announced from memory. The memory is stored on the Pi (memory.json), so "
            "the cane — not a particular phone — remembers."),
          H2("F", "Multilingual Neural Speech and Hands-Free Control"),
          P("Sentences are templated per language (e.g., “Chair detected ahead, 2 meters”) and synthesized with neural "
            "voices for English (India), Hindi, Telugu and Tamil. Each sentence is cached as an MP3 on the Pi; about "
            "160 common sentences per language are pre-generated at start-up, so alerts play instantly and offline, "
            "with espeak-ng as a last fallback. The phone app (Walk, Places, Memory, Settings; all screens translated) "
            "connects over Wi-Fi and can speak through Bluetooth headphones. Holding a hand under 10 cm from the "
            "ultrasonic sensor for 2 s pauses or resumes the cane, so no screen interaction is needed.")]

story += [H("IV", "Experiments and Results"),
          H2("A", "Detector Correctness and Speed"),
          P("Our NumPy/ONNX Runtime pipeline was compared with the reference Ultralytics implementation on the "
            "standard test image: both produced the same classes and boxes (bus 0.90; persons 0.84, 0.82, 0.80); at "
            "480 px it also found a fourth, partly visible person (0.45). Table II gives inference times."),
          table([["Setting", "320 px", "480 px"],
                 ["Laptop CPU, 4 threads (measured)", f"{LAPTOP_MS[320]} ms", f"{LAPTOP_MS[480]} ms"],
                 ["Raspberry Pi 4" + (" (projected)" if projected else " (measured)"), "—" if not projected else "~110 ms", PI_MS]],
                [1.75 * inch, 0.7 * inch, 1.0 * inch], "TABLE II<br/>DETECTOR INFERENCE TIME PER FRAME"),
          H2("B", "Distance Accuracy"),
          P("Table III and Fig. 4 give the estimated distance of an object placed straight ahead. " + DIST_NOTE),
          table([["True (m)", "Camera (m)", "Ultrasonic (m)", "Detected"]] +
                [[f"{d:.1f}", (f"{c:.2f}" if not projected else f"{c * 0.9:.2f}–{c * 1.1:.2f}"),
                  (f"{u:.2f}" if u is not None else "out of range") if not projected else f"{u:.3f} ± 0.003",
                  f"{int(rate * 100)}%"] for d, c, u, rate in DIST],
                [0.6 * inch, 0.95 * inch, 1.0 * inch, 0.65 * inch],
                "TABLE III<br/>DISTANCE ESTIMATION" + (" (PROJECTED)" if projected else "")),
          figure(FIG / "distance.png", "Fig. 4. Estimated vs. true distance." + (" Projected bands; see Table III." if projected else "")),
          H2("C", "Alert Classification"),
          P(f"On 4,000 held-out samples the fusion MLP reaches accuracy {ACC} and urgent-class recall {URGENT_RECALL} "
            "(Fig. 3). Most errors are between neighbouring levels; only 2 of 508 urgent cases were predicted as caution "
            "and none as safe."),
          H2("D", "Early Warning from Memory"),
          P(f"In the app's route simulation (walking speed 1.2 m/s), a remembered hazard was announced {EARLY_M} m "
            f"before reaching it — about {EARLY_S} s of lead time — against about {CAMERA_M:.0f} m for camera-only "
            "detection within the announcement range (Fig. 5). On the simulated block with a hazard on the shortcut, "
            "risk-aware A* chose a 218 m route with 4% accumulated risk over the 195 m shortest route with 10%."),
          figure(FIG / "early.png", "Fig. 5. Warning distance before a known hazard."),
          H2("E", "Functional Tests"),
          P("Voice alerts were verified in all four languages, including live language switching from the app; the "
            "hand gesture paused the cane after 2 s without toggling repeatedly while the hand remained; places saved "
            "in the app were persisted on the Pi and reloaded by a second browser.")]

story += [figure(HERE / "img" / "cane_side.jpg", "Fig. 6. Side view: Raspberry Pi 4 on the shaft with power and "
                 "webcam cables; the breadboard carries the sensor wiring.", width=COLW * 0.6),
          H("V", "Discussion and Limitations"),
          P("The COCO detector recognizes 80 everyday classes; walls, doors and arbitrary boxes are caught only by "
            "the ultrasonic sensor, and potholes and open drains need the custom model described below. Monocular "
            "distance depends on the assumed object height. Consumer GPS is accurate to about 5–10 m and unavailable "
            "indoors, so indoor demonstrations use a recorded route. The fusion network was trained on synthetic "
            "data; retraining on labelled field walks (the app has a labelling mode) is required before deployment, "
            "as is evaluation with visually impaired users.")]

story += [H("VI", "Future Work"),
          P("<b>Cane.</b> Fine-tune YOLOv8 on potholes, open drains, stairs and curbs (a Colab pipeline with dataset "
            "merging and pseudo-labelling is included); add a downward ultrasonic sensor for drop detection, haptic "
            "motors, and a shared multi-user hazard map. <b>Smart glasses.</b> Move the camera to glasses for a stable "
            "head-level view and bone-conduction audio, keeping the cane for ground hazards; add scene description, "
            "sign and bus-number reading, and face-free person detection. <b>Learning.</b> Replace the hand-set risk "
            "formula with a model learned from recorded walks, and quantize the detector (INT8) for higher frame rates.")]

story += [H("VII", "Conclusion"),
          P("AURALIS shows that a low-cost cane can do more than react: an on-device neural detector names and "
            "locates obstacles, speaks them in the user's language, and turns them into a decaying memory of the route "
            "that warns about 25 m early and steers route choice. The complete hardware list, code, models and "
            "training pipelines are open source.")]

refs = [
    "World Health Organization, <i>World Report on Vision</i>. Geneva: WHO, 2019.",
    "J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, “You only look once: Unified, real-time object detection,” in <i>Proc. IEEE CVPR</i>, 2016, pp. 779–788.",
    "G. Jocher, A. Chaurasia, and J. Qiu, “Ultralytics YOLOv8,” 2023. [Online]. Available: github.com/ultralytics/ultralytics",
    "T.-Y. Lin <i>et al.</i>, “Microsoft COCO: Common objects in context,” in <i>Proc. ECCV</i>, 2014, pp. 740–755.",
    "P. Slade, A. Tambe, and M. J. Kochenderfer, “Multimodal sensing and intuitive steering assistance improve navigation and mobility for people with impaired vision,” <i>Science Robotics</i>, vol. 6, no. 59, 2021.",
    "WeWALK, “WeWALK Smart Cane 2,” 2025. [Online]. Available: wewalk.io",
    "“Low-cost smart cane for visually impaired people with pathway surface detection and distance estimation using weighted bounding boxes and depth mapping,” <i>Information</i>, vol. 16, no. 8, art. 707, 2025.",
    "R. Ranftl, K. Lasinger, D. Hafner, K. Schindler, and V. Koltun, “Towards robust monocular depth estimation: Mixing datasets for zero-shot cross-dataset transfer,” <i>IEEE Trans. Pattern Anal. Mach. Intell.</i>, vol. 44, no. 3, 2022.",
    "P. E. Hart, N. J. Nilsson, and B. Raphael, “A formal basis for the heuristic determination of minimum cost paths,” <i>IEEE Trans. Syst. Sci. Cybern.</i>, vol. 4, no. 2, pp. 100–107, 1968.",
    "D. P. Kingma and J. Ba, “Adam: A method for stochastic optimization,” in <i>Proc. ICLR</i>, 2015.",
    "ONNX Runtime developers, “ONNX Runtime,” 2024. [Online]. Available: onnxruntime.ai",
    "“A smart cane based on 2D LiDAR and RGB-D camera sensor — realizing navigation and obstacle recognition,” <i>Sensors</i>, vol. 24, no. 3, 2024.",
    "“A computer vision and depth sensor-powered smart cane for real-time obstacle detection and navigation assistance for the visually impaired,” arXiv:2508.16698, 2025.",
]
story += [H("", "References").__class__(" REFERENCES", S["h1"])]
story += [P(f"[{i}] {r}", "ref") for i, r in enumerate(refs, 1)]


# ---------------- layout: IEEE two columns ----------------
W, Hh = letter
M, G = 0.625 * inch, 0.25 * inch
cw = (W - 2 * M - G) / 2
title_h = 2.0 * inch


def footer(c, doc):
    c.setFont(T, 8); c.drawCentredString(W / 2, 0.45 * inch, str(doc.page))


first = PageTemplate("first", [
    Frame(M, Hh - M - title_h, W - 2 * M, title_h, id="title", leftPadding=0, rightPadding=0),
    Frame(M, M, cw, Hh - 2 * M - title_h, id="c1", leftPadding=0, rightPadding=0),
    Frame(M + cw + G, M, cw, Hh - 2 * M - title_h, id="c2", leftPadding=0, rightPadding=0)], onPage=footer)
later = PageTemplate("later", [
    Frame(M, M, cw, Hh - 2 * M, id="l1", leftPadding=0, rightPadding=0),
    Frame(M + cw + G, M, cw, Hh - 2 * M, id="l2", leftPadding=0, rightPadding=0)], onPage=footer)
doc = BaseDocTemplate(str(OUT), pagesize=letter, title="AURALIS — IEEE conference paper", author="Team AURALIS")
doc.addPageTemplates([first, later])
doc.build(story)
print(f"wrote {OUT}  ({'MEASURED' if not projected else 'projected'} distance values)")
