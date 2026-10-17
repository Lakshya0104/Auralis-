"""AURALIS presentation as a standard 16:9 PDF (13.333 x 7.5 in, PowerPoint size):
    python docs/slides/make_slides.py      -> docs/AURALIS_Presentation.pdf
"""
import pathlib

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = pathlib.Path(__file__).resolve().parent
DOCS = HERE.parent
OUT = DOCS / "AURALIS_Presentation.pdf"
IMG, PIMG, FIG = HERE / "img", DOCS / "paper" / "img", DOCS / "paper" / "fig"

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("SansB", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + "DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("MonoB", F + "DejaVuSansMono-Bold.ttf"))

W, H = 13.333 * inch, 7.5 * inch
M = 0.6 * inch                        # side margin
BG, INK, MUTED, LINE = HexColor("#FAFAF7"), HexColor("#12141A"), HexColor("#4A4F57"), HexColor("#E3E3DE")
DARK, DARK2, WHITE = HexColor("#12141A"), HexColor("#1F232C"), HexColor("#FFFFFF")
RED, ORANGE, GREEN, BLUE, PURPLE = (HexColor(c) for c in ("#E0383E", "#F08A00", "#16A05A", "#1E88E5", "#6B4EE6"))
PILL = {"red": ("#FDE2E4", "#B4232C"), "orange": ("#FFEBD2", "#A35A00"), "purple": ("#E6E3FB", "#4B3BB5"),
        "green": ("#DDF3E6", "#16733F"), "blue": ("#DCEBFB", "#1460A8")}
TEAM = "S Lakshya · Pallavi Naga · Madhumita S"
PAPER = "github.com/Lakshya0104/Auralis-/blob/main/docs/AURALIS_IEEE_Paper.pdf"

c = canvas.Canvas(str(OUT), pagesize=(W, H))
c.setTitle("AURALIS Smart Cane"); c.setAuthor("S Lakshya, Pallavi Naga, Madhumita S")
page = [0]


# ---------- drawing helpers (y measured from the top of the slide) ----------
def Y(y): return H - y


def text(x, y, s, font="Sans", size=14, color=INK, align="left"):
    c.setFont(font, size); c.setFillColor(color)
    {"left": c.drawString, "right": c.drawRightString, "center": c.drawCentredString}[align](x, Y(y), s)


def wrap(x, y, s, width, font="Sans", size=14, color=INK, lead=1.35):
    """Draw wrapped text from top y; returns the y below the last line."""
    words, line, lines = s.split(), "", []
    for w in words:
        t = (line + " " + w).strip()
        if pdfmetrics.stringWidth(t, font, size) <= width: line = t
        else: lines.append(line); line = w
    lines.append(line)
    for i, ln in enumerate(lines):
        text(x, y + size + i * size * lead, ln, font, size, color)
    return y + size + (len(lines) - 1) * size * lead + size * 0.45


def rect(x, y, w, h, fill=WHITE, stroke=LINE, r=12, lw=1):
    c.setFillColor(fill); c.setStrokeColor(stroke or fill); c.setLineWidth(lw)
    c.roundRect(x, Y(y + h), w, h, r, fill=1, stroke=1 if stroke else 0)


def pill(x, y, s, kind="red", size=12):
    bg, fg = PILL[kind]; w = pdfmetrics.stringWidth(s, "SansB", size) + 22
    rect(x, y, w, size + 12, HexColor(bg), None, r=(size + 12) / 2)
    text(x + 11, y + size + 3, s, "SansB", size, HexColor(fg)); return x + w + 8


def image(path, x, y, w, h, r=14, fit="cover"):
    im = PILImage.open(path); iw, ih = im.size
    if fit == "cover":
        s = max(w / iw, h / ih); cw, ch = w / s, h / s
        im = im.crop(((iw - cw) / 2, (ih - ch) / 2 * 0.6, (iw + cw) / 2, (ih - ch) / 2 * 0.6 + ch))
        dw, dh = w, h
    else:
        s = min(w / iw, h / ih); dw, dh = iw * s, ih * s
    c.saveState(); p = c.beginPath(); p.roundRect(x, Y(y + dh), dw, dh, r); c.clipPath(p, stroke=0)
    c.drawImage(ImageReader(im), x, Y(y + dh), dw, dh); c.restoreState()
    return dw, dh


def slide(eyebrow, title, dark=False, title_size=34):
    if page[0]: c.showPage()
    page[0] += 1
    c.setFillColor(DARK if dark else BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    text(M, 0.62 * inch, eyebrow.upper(), "MonoB", 13, HexColor("#FF6B70") if dark else RED)
    if title:
        y = 0.72 * inch
        for ln in title.split("\n"):
            text(M, y + title_size, ln, "SansB", title_size, WHITE if dark else INK); y += title_size * 1.15
    text(M, H - 0.32 * inch, f"{page[0]:02d} · AURALIS", "Mono", 10, HexColor("#8A8F98"))
    text(W - M, H - 0.32 * inch, TEAM, "Mono", 10, HexColor("#8A8F98"), "right")


def stat(x, y, num, label, color, size=40, width=2.6 * inch):
    text(x, y + size, num, "SansB", size, color); return wrap(x, y + size + 6, label, width, "Sans", 12, MUTED)


def card(x, y, w, h, head, body, tag=None, tagkind="red", dark=False, hsize=17, bsize=12.5):
    rect(x, y, w, h, DARK2 if dark else WHITE, None if dark else LINE, r=14)
    yy = y + 16
    if tag: pill(x + 16, yy, tag, tagkind, 11); yy += 34
    if head: text(x + 16, yy + hsize, head, "SansB", hsize, WHITE if dark else INK); yy += hsize + 10
    for para in body if isinstance(body, list) else [body]:
        yy = wrap(x + 16, yy, para, w - 32, "Sans", bsize, HexColor("#C4C8D0") if dark else MUTED) + 2
    return yy


def table(x, y, cols, rows, widths, size=11.5, rowh=24, hl_col=None):
    total = sum(widths); rect(x, y, total, rowh * (len(rows) + 1) + 6, WHITE, LINE, r=10)
    cx = x
    for i, h in enumerate(cols):
        text(cx + 10, y + rowh - 6, h, "SansB", size, GREEN if i == hl_col else INK); cx += widths[i]
    c.setStrokeColor(INK); c.setLineWidth(0.8); c.line(x + 8, Y(y + rowh + 2), x + total - 8, Y(y + rowh + 2))
    for r, row in enumerate(rows):
        ry = y + rowh * (r + 2) - 6
        if r % 2: c.setFillColor(HexColor("#F4F4F0")); c.rect(x + 4, Y(ry + 7), total - 8, rowh, fill=1, stroke=0)
        cx = x
        for i, cell in enumerate(row):
            text(cx + 10, ry, cell, "SansB" if i == hl_col else "Sans", size, GREEN if i == hl_col else INK); cx += widths[i]


def bullet(x, y, s, w, size=12.5, color=MUTED, dot=RED):
    text(x, y + size, "•", "SansB", size + 1, dot)
    return wrap(x + 16, y, s, w - 16, "Sans", size, color)


def arrow(x1, y, x2, color=MUTED):
    c.setStrokeColor(color); c.setFillColor(color); c.setLineWidth(2)
    c.line(x1, Y(y), x2 - 8, Y(y)); p = c.beginPath()
    p.moveTo(x2, Y(y)); p.lineTo(x2 - 10, Y(y) + 6); p.lineTo(x2 - 10, Y(y) - 6); p.close(); c.drawPath(p, fill=1, stroke=0)


# =============== 1. Title ===============
slide("Artificial & Neural Networks · Capstone", None)
text(M, 1.8 * inch, "AURALIS", "SansB", 88, INK)
wrap(M, 2.1 * inch, "The smart cane that sees obstacles, speaks your language, and remembers where hazards are.",
     6.9 * inch, "SansB", 24, INK, 1.25)
x = M
for s, k in [("On-device AI", "red"), ("Hazard memory", "orange"), ("4 Indian languages", "purple"), ("Hands-free", "green")]:
    x = pill(x, 3.7 * inch, s, k, 13)
rect(M, 4.4 * inch, 6.9 * inch, 2.15 * inch, WHITE, LINE, r=16)
text(M + 20, 4.4 * inch + 30, "TEAM", "MonoB", 12, RED)
for i, (n, r) in enumerate([("S Lakshya", "CH.SC.U4CYS24030"), ("Pallavi Naga", "CH.SC.U4CYS24067"), ("Madhumita S", "CH.SC.U4CYS24034")]):
    yy = 4.4 * inch + 64 + i * 38
    text(M + 20, yy, n, "SansB", 18, INK); text(M + 3.3 * inch, yy, r, "Mono", 15, MUTED)
image(PIMG / "cane_front.jpg", 8.3 * inch, 0.55 * inch, 4.43 * inch, 6.25 * inch, r=20)

# =============== 2. Problem + existing solutions ===============
slide("The problem · and what exists today", "A white cane feels only what it touches,\nand forgets it the moment it moves on.")
y0 = 2.1 * inch
stat(M, y0, "2.2 B", "people live with a vision impairment (WHO, 2019)", RED, 44)
stat(M + 2.9 * inch, y0, "43 M", "people are blind", ORANGE, 44)
cw = 1.85 * inch
for i, (tag, k, body) in enumerate([("Reach", "red", "Head-level boards, branches and fast bikes are outside the cane's sweep."),
                                    ("Memory", "orange", "The same pothole on the daily route is found again, by touch, every time."),
                                    ("Language", "purple", "Most aids speak only English; many users think in Hindi, Telugu or Tamil.")]):
    card(M + i * (cw + 0.15 * inch), 3.45 * inch, cw, 2.75 * inch, None, body, tag, k, bsize=13)
tx = 6.65 * inch
text(tx, 2.25 * inch, "EXISTING SMART CANES vs AURALIS", "MonoB", 12, RED)
table(tx, 2.4 * inch, ["Feature", "WeWALK", "Stanford", "YOLO canes", "AURALIS"],
      [["Detects obstacles", "Sensor", "LiDAR", "Camera", "Camera+sensor"],
       ["Names the object", "No", "Yes", "Yes", "Yes"],
       ["Indian languages", "No", "No", "No", "4, neural"],
       ["Remembers hazards", "No", "No", "No", "Yes + decay"],
       ["Safest route", "No", "No", "No", "Risk-aware A*"],
       ["Approx. cost", "High", "$400", "Varies", "Rs 8,300"]],
      [1.78 * inch, 0.85 * inch, 0.85 * inch, 1.0 * inch, 1.6 * inch], size=10.5, rowh=30, hl_col=4)
wrap(tx, 5.35 * inch, "Gap: existing canes are reactive. None turn what they detect into a memory of the route "
     "and use it to warn early.", 6.1 * inch, "SansB", 14, INK)

# =============== 3. Solution + how it works ===============
slide("Our solution · two pillars", "See it, say it, remember it.", dark=True)
for i, (tag, head, body, quote, qc) in enumerate([
        ("PILLAR 1", "AI hazard detection with voice",
         "A YOLOv8 neural network on the Raspberry Pi names each obstacle, finds its side and distance, and speaks it "
         "in the user's language through the Pi or the phone's headphones.", "“Chair detected ahead, 2 metres”", HexColor("#7EE2A8")),
        ("PILLAR 2", "Location intelligence",
         "Every confirmed hazard is stored with its GPS position on the cane. Repeated sightings strengthen it, time "
         "fades it, and the cane warns from memory before the hazard is in view.", "“Careful. Remembered pothole, 25 metres ahead”", HexColor("#7EB6FF"))]):
    x = M + i * 6.15 * inch
    rect(x, 1.55 * inch, 5.95 * inch, 2.75 * inch, DARK2, None, r=18)
    text(x + 22, 1.55 * inch + 32, tag, "MonoB", 13, HexColor("#FF6B70"))
    text(x + 22, 1.55 * inch + 66, head, "SansB", 22, WHITE)
    yy = wrap(x + 22, 1.55 * inch + 80, body, 5.5 * inch, "Sans", 13.5, HexColor("#C4C8D0"))
    text(x + 22, yy + 22, quote, "Mono", 13.5, qc)
text(M, 4.75 * inch, "HOW IT WORKS", "MonoB", 13, HexColor("#FF6B70"))
steps = [("Sense", "Webcam + ultrasonic + phone GPS"), ("Detect", "YOLOv8n on the Pi CPU"), ("Measure", "Size model + ultrasonic"),
         ("Decide", "Fusion MLP: 4 alert levels"), ("Speak", "Neural voice, 4 languages"), ("Remember", "Hazard map on the Pi")]
bw = 1.82 * inch
for i, (h, b) in enumerate(steps):
    x = M + i * (bw + 0.22 * inch)
    rect(x, 4.95 * inch, bw, 1.45 * inch, DARK2, None, r=14)
    text(x + 14, 4.95 * inch + 28, f"{i + 1}  {h}", "SansB", 15, WHITE)
    wrap(x + 14, 4.95 * inch + 40, b, bw - 28, "Sans", 11.5, HexColor("#C4C8D0"))
    if i < 5: arrow(x + bw + 2, 5.67 * inch, x + bw + 0.2 * inch, HexColor("#8A8F98"))

# =============== 4. Prototype ===============
slide("The prototype", "Built on a PVC pipe, in days.")
pw = 2.55 * inch
for i, (f, cap) in enumerate([("cane_front.jpg", "Front: Logitech webcam, HC-SR04 below"),
                              ("cane_side.jpg", "Side: Raspberry Pi 4 on the shaft"),
                              ("cane_top.jpg", "Wiring: 1 kΩ / 2 kΩ divider on breadboard")]):
    x = M + i * (pw + 0.18 * inch)
    image(PIMG / f, x, 1.45 * inch, pw, 4.55 * inch)
    wrap(x, 6.05 * inch, cap, pw, "Sans", 11.5, MUTED)
tx = M + 3 * (pw + 0.18 * inch) + 0.1 * inch
text(tx, 1.55 * inch, "WIRING (HC-SR04 → Pi 4)", "MonoB", 12, RED)
table(tx, 1.7 * inch, ["Sensor pin", "Pi pin"],
      [["VCC", "Pin 2 (5 V)"], ["GND", "Pin 6"], ["TRIG", "Pin 16 (GPIO23)"], ["ECHO", "1 kΩ → Pin 18 (GPIO24)"], ["divider", "2 kΩ GPIO24 → GND"]],
      [1.1 * inch, 2.2 * inch], size=12, rowh=28)
text(tx, 4.4 * inch, "MOUNTING", "MonoB", 12, RED)
y = 4.5 * inch
for s in ["Webcam at ≈ 0.9 m, facing forward, tilted slightly down",
          "Ultrasonic just below it, both 'eyes' clear",
          "Pi + power bank near the handle, ports open",
          "USB webcam, USB-C 5 V / 3 A power bank"]:
    y = bullet(tx, y, s, 3.3 * inch, 12) + 2

# =============== 5. Tech stack ===============
slide("Tech stack · hardware and software", "Four parts on the cane. Three software layers.")
text(M, 1.5 * inch, "HARDWARE", "MonoB", 13, RED)
hw = [("Raspberry Pi 4", "4-core ARM, 4 GB · runs the neural network, voice and memory", "Rs 6,000"),
      ("Logitech USB webcam", "640×480 · forward vision at handle height", "Rs 800"),
      ("HC-SR04 ultrasonic", "2–400 cm range · exact distance + hand gesture", "Rs 100"),
      ("Power bank", "5 V / 3 A over USB-C", "Rs 1,200"),
      ("PVC pipe, breadboard, wires", "The cane body", "Rs 200"),
      ("User's phone + headphones", "GPS, app, voice in the ear", "—")]
for i, (h, b, cost) in enumerate(hw):
    y = 1.65 * inch + i * 0.73 * inch
    rect(M, y, 5.9 * inch, 0.63 * inch, WHITE, LINE, r=10)
    text(M + 14, y + 22, h, "SansB", 14, INK); text(M + 14, y + 42, b, "Sans", 11, MUTED)
    text(M + 5.9 * inch - 14, y + 30, cost, "SansB", 14, GREEN, "right")
text(M, 6.2 * inch + 10, "Total ≈ Rs 8,300", "SansB", 20, INK)
sx = 7.0 * inch
text(sx, 1.5 * inch, "SOFTWARE", "MonoB", 13, RED)
layers = [("ON THE CANE (Pi)", "red", ["Python 3", "ONNX Runtime", "OpenCV", "gpiozero", "aiohttp WebSocket", "edge-tts + mpg123"]),
          ("PHONE APP", "blue", ["HTML + JavaScript PWA", "Leaflet + OpenStreetMap", "GPS geolocation", "Web Speech"]),
          ("TRAINING", "green", ["Ultralytics YOLOv8", "NumPy MLP (backprop + Adam)", "Google Colab GPU", "Roboflow datasets"])]
y = 1.65 * inch
for name, k, items in layers:
    rect(sx, y, 5.73 * inch, 1.45 * inch, WHITE, LINE, r=14)
    text(sx + 16, y + 26, name, "MonoB", 12, HexColor(PILL[k][1]))
    px, py = sx + 16, y + 40
    for it in items:
        wdt = pdfmetrics.stringWidth(it, "SansB", 11) + 30
        if px + wdt > sx + 5.73 * inch - 10: px, py = sx + 16, py + 30
        px = pill(px, py, it, k, 11)
    y += 1.6 * inch
wrap(sx, y + 4, "Pi → phone: obstacles over WebSocket ≈ 5×/s · phone → Pi: language, pause, saved places · memory on the Pi",
     5.73 * inch, "Sans", 11.5, MUTED)

# =============== 6. Neural networks ===============
slide("Artificial neural networks used", "Three networks, each with one job.")
nets = [("CNN · on the cane", "red", "YOLOv8n object detector", "3.2 M parameters", RED,
         ["Convolutional backbone + detection head, pre-trained on COCO (80 classes).",
          "Exported to ONNX at 480 px; runs with ONNX Runtime on the Pi CPU, no PyTorch.",
          "Class-aware NMS (IoU 0.45, conf 0.40); object must appear in 2 of 3 frames."]),
        ("MLP · trained by us", "green", "Sensor-fusion network", "8 → 16 → 16 → 4", GREEN,
         ["Inputs: distance, drop, class severity, confidence, box area, offset, memory risk, approach speed.",
          "ReLU hidden layers, softmax output: safe / caution / warning / urgent.",
          "Backpropagation with Adam on 20,000 samples; safety override for drops."]),
        ("Neural TTS", "purple", "Natural voices", "4 languages", PURPLE,
         ["Neural voices: English (India), Hindi, Telugu, Tamil.",
          "Every sentence cached as MP3 on the Pi; ≈160 common ones pre-generated at start-up.",
          "Plays instantly and offline; espeak-ng only as a last fallback."])]
cw = 3.95 * inch
for i, (tag, k, head, big, col, lines) in enumerate(nets):
    x = M + i * (cw + 0.12 * inch)
    rect(x, 1.45 * inch, cw, 3.3 * inch, WHITE, LINE, r=16)
    pill(x + 16, 1.45 * inch + 16, tag, k, 11)
    text(x + 16, 1.45 * inch + 74, head, "SansB", 17, INK)
    text(x + 16, 1.45 * inch + 112, big, "SansB", 26, col)
    yy = 1.45 * inch + 126
    for ln in lines: yy = wrap(x + 16, yy, "• " + ln, cw - 32, "Sans", 11.2, MUTED) + 1
image(FIG / "confusion.png", M, 4.9 * inch, 2.0 * inch, 1.85 * inch, r=8, fit="contain")
stat(M + 2.3 * inch, 4.95 * inch, "89.5%", "alert-level accuracy (4,000 test samples)", BLUE, 34, 2.4 * inch)
stat(M + 5.0 * inch, 4.95 * inch, "0.94", "urgent-alert recall", GREEN, 34, 2.0 * inch)
stat(M + 7.3 * inch, 4.95 * inch, "0 / 508", "urgent cases predicted as safe", RED, 34, 2.3 * inch)
stat(M + 9.9 * inch, 4.95 * inch, "27 ms", "YOLOv8 per frame, 4-core laptop CPU", ORANGE, 34, 2.2 * inch)

# =============== 7. Pillar 1 ===============
slide("Pillar 1 · AI hazard detection", "From a camera frame to a spoken warning.")
lx, lw = M, 5.6 * inch
rect(lx, 1.45 * inch, lw, 0.55 * inch, WHITE, LINE, r=12)
text(lx + 16, 1.45 * inch + 25, "640×480 webcam frame  +  ultrasonic 182 cm", "Sans", 13.5, INK)
text(lx + lw / 2, 2.35 * inch, "↓  YOLOv8 on the Pi reads it", "Sans", 13, MUTED, "center")
x = lx
for s, k in [("chair 0.81", "red"), ("static obstacle", "orange"), ("in path · ahead", "purple"), ("1.8 m", "green")]:
    x = pill(x, 2.55 * inch, s, k, 12.5)
text(lx + lw / 2, 3.3 * inch, "↓  neural voice, user's language", "Sans", 13, MUTED, "center")
text(lx, 3.7 * inch, "“Chair detected ahead, 2 metres”", "Mono", 15, GREEN)
text(lx, 4.05 * inch, "“Stop. Chair very close”  (under 0.8 m)", "Mono", 15, RED)
text(lx, 4.55 * inch, "DISTANCE MODEL", "MonoB", 12, RED)
rect(lx, 4.7 * inch, lw, 1.65 * inch, WHITE, LINE, r=12)
text(lx + 16, 4.7 * inch + 30, "d = H · f / h      f = (W/2) / tan(θ/2)", "MonoB", 15, INK)
wrap(lx + 16, 4.7 * inch + 44, "H = typical object height, h = box height in pixels, θ = webcam field of view (calibrated "
     "once with a person at 2 m). Straight-ahead objects take the ultrasonic distance instead. Side = which third of "
     "the image the object is in.", lw - 32, "Sans", 11.5, MUTED)
rx = 6.65 * inch
text(rx, 1.55 * inch, "HAZARD TAXONOMY", "MonoB", 12, RED)
table(rx, 1.7 * inch, ["Hazard type", "Examples", "Response"],
      [["Drop / pit", "pothole, drain, stairs down", "Always STOP"],
       ["Static", "chair, table, pole, bag", "Warn + remember"],
       ["Head height", "branch, signboard", "Warn + remember"],
       ["Moving", "person, bike, auto, dog", "Warn only"],
       ["Unknown", "wall, box (ultrasonic)", "Obstacle ahead"]],
      [1.45 * inch, 2.55 * inch, 1.73 * inch], size=11.5, rowh=28)
text(rx, 4.35 * inch, "ANNOUNCED ONLY IF", "MonoB", 12, RED)
y = 4.45 * inch
for s in ["inside the 1 m walking corridor (middle third of the view)", "closer than 3 m",
          "seen in at least 2 of the last 3 frames (no one-frame false alarms)",
          "cane is active: hand at the sensor for 2 s pauses / resumes, no buttons"]:
    y = bullet(rx, y, s, 6.0 * inch, 12.5) + 2

# =============== 8. Pillar 2 ===============
slide("Pillar 2 · Location intelligence", "Warn from memory, not from sight.")
lx = M
y = 1.5 * inch
for head, body in [("1  Remember", "Each warned static hazard is saved with its GPS position, type and time, on the Pi (memory.json)."),
                   ("2  Weigh", "Seen again → stronger. Not seen for a week → half as strong. The user can clear it."),
                   ("3  Learn the paths", "GPS breadcrumbs every 5 m build a walking graph from the user's own routes."),
                   ("4  Route safely", "A* finds the route with cost = length × (1 + 4 · risk) to a saved place.")]:
    text(lx, y + 16, head, "SansB", 16, INK); y = wrap(lx, y + 22, body, 5.6 * inch, "Sans", 12.5, MUTED) + 8
rect(lx, y + 4, 5.6 * inch, 0.55 * inch, WHITE, LINE, r=10)
text(lx + 14, y + 4 + 25, "risk = severity × (1 − e^(−n/2)) × 0.5^(age/7d) × conf", "Mono", 11.5, INK)
rx = 6.65 * inch
image(FIG / "early.png", rx, 1.45 * inch, 6.0 * inch, 2.3 * inch, r=8, fit="contain")
stat(rx, 4.0 * inch, "8.3×", "earlier warning (25 m vs 3 m)", GREEN, 40, 1.8 * inch)
stat(rx + 2.05 * inch, 4.0 * inch, "21 s", "extra reaction time at 1.2 m/s", BLUE, 40, 1.8 * inch)
stat(rx + 4.1 * inch, 4.0 * inch, "−60%", "route risk for +12% length", ORANGE, 40, 1.9 * inch)
wrap(rx, 5.55 * inch, "Route test: shortest 195 m at 10% risk vs safest 218 m at 4% risk. Measured in the app's route "
     "simulation; outdoors the phone's GPS (±5–10 m) is used.", 6.0 * inch, "Sans", 11.5, MUTED)

# =============== 9. App + results ===============
slide("The phone app · and results", "Headphones on, nothing to press.")
sw = 1.62 * inch
for i, (f, cap) in enumerate([("app_walk.png", "Walk: live status + radar"), ("app_map.png", "Places: map + memory"),
                              ("app_memory_hi.png", "Memory, in Hindi")]):
    x = M + i * (sw + 0.15 * inch)
    image(IMG / f, x, 1.45 * inch, sw, 3.6 * inch, r=12)
    wrap(x, 5.1 * inch, cap, sw, "Sans", 11, MUTED)
x = M
for s, k in [("English", "red"), ("Hindi", "orange"), ("Telugu", "purple"), ("Tamil", "green")]:
    x = pill(x, 5.75 * inch, s, k, 12)
wrap(M, 6.2 * inch, "Every screen and every voice alert in 4 languages; voice through phone headphones.",
     5.2 * inch, "Sans", 11.5, MUTED)
rx = 6.65 * inch
text(rx, 1.55 * inch, "RESULTS", "MonoB", 12, RED)
table(rx, 1.7 * inch, ["Test", "Result"],
      [["Detector vs reference YOLOv8", "Identical classes and boxes"],
       ["Detector speed, laptop CPU", "13 ms (320 px) · 27 ms (480 px)"],
       ["Fusion MLP, 4,000 test rows", "Accuracy 89.5% · urgent recall 0.94"],
       ["Early warning from memory", "25 m ahead vs ≈ 3 m camera-only"],
       ["Safest vs shortest route", "4% vs 10% risk, +23 m"],
       ["Languages", "EN / HI / TE / TA, switch live"],
       ["Hands-free pause", "2 s hand hold, no false toggles"]],
      [2.55 * inch, 3.5 * inch], size=11, rowh=29)
wrap(rx, 5.95 * inch, "Distance accuracy and Pi 4 speed: measured on the cane with pi/measure.py and reported in the IEEE paper.",
     6.0 * inch, "Sans", 11.5, MUTED)

# =============== 10. Future + links ===============
slide("Future implementations · and thank you", "From a cane to a full wearable.", dark=True)
cols = [("SMART CANE 2.0", HexColor("#7EE2A8"), ["Custom YOLO: potholes, open drains, stairs, curbs", "Downward sensor for drops and steps",
                                                   "Haptic handle: left / right / stop", "Shared hazard map across many canes"]),
        ("SMART GLASSES", HexColor("#7EB6FF"), ["Camera at eye level for head-height hazards", "Bone-conduction audio, ears stay free",
                                                  "Read signs, bus numbers, currency", "Scene description on demand"]),
        ("LEARNING", HexColor("#FFB35C"), ["Retrain fusion on real labelled walks", "Learned risk model instead of a formula",
                                            "INT8 model for faster frames", "Field trials with blind users"])]
cw = 3.95 * inch
for i, (h, col, items) in enumerate(cols):
    x = M + i * (cw + 0.12 * inch)
    rect(x, 1.45 * inch, cw, 2.75 * inch, DARK2, None, r=16)
    text(x + 18, 1.45 * inch + 30, h, "MonoB", 13, col)
    yy = 1.45 * inch + 44
    for it in items: yy = wrap(x + 18, yy, "• " + it, cw - 36, "Sans", 13, HexColor("#C4C8D0")) + 4
text(M, 4.65 * inch, "READ MORE", "MonoB", 13, HexColor("#FF6B70"))
links = [("IEEE paper", "https://" + PAPER), ("Code", "https://github.com/Lakshya0104/Auralis-"),
         ("App demo", "https://claude.ai/artifact/8sLp1jaMJCcjauKUYCU8F8")]
for i, (k, url) in enumerate(links):
    y = 4.85 * inch + i * 0.42 * inch
    text(M, y + 18, k, "SansB", 15, WHITE)
    shown = {"IEEE paper": "AURALIS_IEEE_Paper.pdf  (GitHub)", "Code": "github.com/Lakshya0104/Auralis-",
             "App demo": "claude.ai/artifact/8sLp1jaMJCcjauKUYCU8F8"}[k]
    text(M + 1.5 * inch, y + 18, shown, "Mono", 13, HexColor("#7EB6FF"))
    c.linkURL(url, (M + 1.5 * inch, Y(y + 22), M + 7 * inch, Y(y)), relative=0)
text(W - M, 5.55 * inch, "Thank you", "SansB", 44, WHITE, "right")
text(W - M, 5.95 * inch, TEAM, "Sans", 14, HexColor("#C4C8D0"), "right")

c.save()
print(f"wrote {OUT} ({page[0]} slides)")
