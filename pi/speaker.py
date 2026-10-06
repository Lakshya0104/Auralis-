"""Voice on the Pi itself (espeak-ng), so the cane talks even with no phone connected.
Audio goes to whatever the Pi outputs to: HDMI (projector speakers), the 3.5 mm jack, or a
Bluetooth speaker / earphones paired to the Pi.

    sudo apt install espeak-ng      (done by setup_pi.sh)
"""
import queue
import shutil
import subprocess
import threading
import time

NAMES = {
    "en": {"person": "person", "chair": "chair", "backpack": "bag", "handbag": "bag", "suitcase": "suitcase",
           "bottle": "bottle", "cup": "cup", "laptop": "laptop", "cell phone": "mobile phone", "book": "book",
           "dining table": "table", "couch": "sofa", "bed": "bed", "tv": "television", "umbrella": "umbrella",
           "cat": "cat", "dog": "dog", "cow": "cow", "bench": "bench", "potted plant": "plant pot",
           "bicycle": "bicycle", "motorcycle": "motorbike", "car": "car", "bus": "bus", "truck": "truck",
           "fire hydrant": "pole", "stop sign": "sign board", "traffic light": "traffic signal",
           "obstacle": "obstacle", "drop": "pit or step down", "step_up": "step up",
           "pothole": "pothole", "open_drain": "open drain", "stairs_down": "stairs going down", "curb": "kerb",
           "stairs_up": "stairs going up", "speed_breaker": "speed breaker", "pole": "pole", "tree": "tree",
           "wall": "wall", "barrier": "barrier", "dustbin": "dustbin", "branch": "branch", "signboard": "signboard",
           "construction": "construction work", "auto_rickshaw": "auto rickshaw"},
    "hi": {"person": "व्यक्ति", "chair": "कुर्सी", "backpack": "बैग", "handbag": "बैग", "suitcase": "सूटकेस",
           "bottle": "बोतल", "cup": "कप", "laptop": "लैपटॉप", "cell phone": "मोबाइल फोन", "book": "किताब",
           "dining table": "मेज़", "couch": "सोफ़ा", "bed": "बिस्तर", "tv": "टीवी", "umbrella": "छाता",
           "cat": "बिल्ली", "dog": "कुत्ता", "cow": "गाय", "bench": "बेंच", "potted plant": "गमला",
           "bicycle": "साइकिल", "motorcycle": "मोटरसाइकिल", "car": "कार", "bus": "बस", "truck": "ट्रक",
           "fire hydrant": "खंभा", "stop sign": "बोर्ड", "traffic light": "ट्रैफिक सिग्नल",
           "obstacle": "रुकावट", "drop": "गड्ढा या सीढ़ी", "step_up": "ऊँचा कदम",
           "pothole": "गड्ढा", "open_drain": "खुला नाला", "stairs_down": "नीचे जाती सीढ़ियाँ", "curb": "फुटपाथ का किनारा",
           "stairs_up": "ऊपर जाती सीढ़ियाँ", "speed_breaker": "स्पीड ब्रेकर", "pole": "खंभा", "tree": "पेड़",
           "wall": "दीवार", "barrier": "बैरियर", "dustbin": "कूड़ेदान", "branch": "डाली", "signboard": "साइनबोर्ड",
           "construction": "निर्माण कार्य", "auto_rickshaw": "ऑटो रिक्शा"},
    "te": {"person": "వ్యక్తి", "chair": "కుర్చీ", "backpack": "బ్యాగ్", "handbag": "బ్యాగ్", "suitcase": "సూట్‌కేస్",
           "bottle": "సీసా", "cup": "కప్పు", "laptop": "ల్యాప్‌టాప్", "cell phone": "మొబైల్ ఫోన్", "book": "పుస్తకం",
           "dining table": "బల్ల", "couch": "సోఫా", "bed": "మంచం", "tv": "టీవీ", "umbrella": "గొడుగు",
           "cat": "పిల్లి", "dog": "కుక్క", "cow": "ఆవు", "bench": "బెంచ్", "potted plant": "కుండీ",
           "bicycle": "సైకిల్", "motorcycle": "బైక్", "car": "కారు", "bus": "బస్సు", "truck": "లారీ",
           "fire hydrant": "స్తంభం", "stop sign": "బోర్డు", "traffic light": "ట్రాఫిక్ సిగ్నల్",
           "obstacle": "అడ్డంకి", "drop": "గుంత లేదా మెట్టు", "step_up": "ఎత్తైన మెట్టు",
           "pothole": "గుంత", "open_drain": "తెరిచిన కాలువ", "stairs_down": "కిందికి మెట్లు", "curb": "ఫుట్‌పాత్ అంచు",
           "stairs_up": "పైకి మెట్లు", "speed_breaker": "స్పీడ్ బ్రేకర్", "pole": "స్తంభం", "tree": "చెట్టు",
           "wall": "గోడ", "barrier": "అడ్డుకట్ట", "dustbin": "చెత్త డబ్బా", "branch": "కొమ్మ", "signboard": "బోర్డు",
           "construction": "నిర్మాణ పనులు", "auto_rickshaw": "ఆటో"},
    "ta": {"person": "நபர்", "chair": "நாற்காலி", "backpack": "பை", "handbag": "கைப்பை", "suitcase": "சூட்கேஸ்",
           "bottle": "பாட்டில்", "cup": "கோப்பை", "laptop": "மடிக்கணினி", "cell phone": "கைபேசி", "book": "புத்தகம்",
           "dining table": "மேசை", "couch": "சோபா", "bed": "கட்டில்", "tv": "தொலைக்காட்சி", "umbrella": "குடை",
           "cat": "பூனை", "dog": "நாய்", "cow": "மாடு", "bench": "பெஞ்ச்", "potted plant": "தொட்டி",
           "bicycle": "சைக்கிள்", "motorcycle": "பைக்", "car": "கார்", "bus": "பேருந்து", "truck": "லாரி",
           "fire hydrant": "கம்பம்", "stop sign": "பலகை", "traffic light": "சிக்னல்",
           "obstacle": "தடை", "drop": "குழி அல்லது படி", "step_up": "உயரமான படி",
           "pothole": "பள்ளம்", "open_drain": "திறந்த கால்வாய்", "stairs_down": "கீழே இறங்கும் படிகள்", "curb": "நடைபாதை ஓரம்",
           "stairs_up": "மேலே ஏறும் படிகள்", "speed_breaker": "வேகத்தடை", "pole": "கம்பம்", "tree": "மரம்",
           "wall": "சுவர்", "barrier": "தடுப்பு", "dustbin": "குப்பைத் தொட்டி", "branch": "கிளை", "signboard": "பலகை",
           "construction": "கட்டுமானப் பணி", "auto_rickshaw": "ஆட்டோ"},
}

PHRASES = {
    "en": {"ahead": "{o} detected ahead, {d}", "left": "{o} detected on your left, {d}", "right": "{o} detected on your right, {d}",
           "stop": "Stop. {o} very close", "m": "{n} metres", "m1": "1 metre", "cm": "{n} centimetres", "ready": "AURALIS ready"},
    "hi": {"ahead": "आगे {o} पाया गया, {d}", "left": "बाईं ओर {o} पाया गया, {d}", "right": "दाईं ओर {o} पाया गया, {d}",
           "stop": "रुकिए. {o} बहुत पास है", "m": "{n} मीटर", "m1": "1 मीटर", "cm": "{n} सेंटीमीटर", "ready": "औरालिस तैयार है"},
    "te": {"ahead": "ముందు {o} గుర్తించబడింది, {d}", "left": "ఎడమ వైపు {o} గుర్తించబడింది, {d}", "right": "కుడి వైపు {o} గుర్తించబడింది, {d}",
           "stop": "ఆగండి. {o} చాలా దగ్గరగా ఉంది", "m": "{n} మీటర్లు", "m1": "1 మీటరు", "cm": "{n} సెంటీమీటర్లు", "ready": "ఆరాలిస్ సిద్ధంగా ఉంది"},
    "ta": {"ahead": "முன்னால் {o} கண்டறியப்பட்டது, {d}", "left": "இடது பக்கம் {o} கண்டறியப்பட்டது, {d}", "right": "வலது பக்கம் {o} கண்டறியப்பட்டது, {d}",
           "stop": "நில்லுங்கள். {o} மிக அருகில் உள்ளது", "m": "{n} மீட்டர்", "m1": "1 மீட்டர்", "cm": "{n} சென்டிமீட்டர்", "ready": "ஆராலிஸ் தயார்"},
}
VOICES = {"en": "en-gb", "hi": "hi", "te": "te", "ta": "ta"}


def distance_words(lang, metres):
    p = PHRASES[lang]
    if metres < 1:
        return p["cm"].format(n=max(10, int(round(metres * 10)) * 10))
    n = round(metres * 2) / 2                      # nearest half metre
    n = int(n) if n == int(n) else n
    return p["m1"] if n == 1 else p["m"].format(n=n)


def sentence(lang, obstacle, urgent=False):
    p, names = PHRASES[lang], NAMES[lang]
    name = names.get(obstacle["cls"], NAMES["en"].get(obstacle["cls"], obstacle["cls"].replace("_", " ")))
    if urgent:
        return p["stop"].format(o=name)
    return p[obstacle["side"]].format(o=name, d=distance_words(lang, obstacle["dist"]))


class Speaker:
    def __init__(self, lang="en", enabled=True):
        self.lang = lang
        self.enabled = enabled and shutil.which("espeak-ng") is not None
        if enabled and not self.enabled:
            print("[voice] espeak-ng not installed: sudo apt install espeak-ng")
        self.q = queue.Queue()
        self.proc = None
        threading.Thread(target=self._run, daemon=True).start()

    def say(self, text, urgent=False):
        if not self.enabled:
            return
        if urgent:                     # interrupt whatever is being said
            while not self.q.empty():
                self.q.get_nowait()
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
        self.q.put(text)

    def busy(self):
        return (self.proc is not None and self.proc.poll() is None) or not self.q.empty()

    def _run(self):
        while True:
            text = self.q.get()
            self.proc = subprocess.Popen(["espeak-ng", "-v", VOICES.get(self.lang, "en"), "-s", "155", text],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.proc.wait()


class Announcer:
    """Decides what to say: the nearest obstacle in the walking corridor, without repeating itself."""

    def __init__(self, speaker, within_m, repeat_s):
        self.sp, self.within, self.repeat = speaker, within_m, repeat_s
        self.last = {}           # cls -> (time, distance)
        self.last_text = None

    def update(self, obstacles):
        target = next((o for o in obstacles if o["inCorridor"] and o["dist"] <= self.within), None)
        if not target:
            return None
        now = time.time()
        urgent = target["dist"] < 0.8 or (target["category"] == "drop")
        t_prev, d_prev = self.last.get(target["cls"], (0, 99))
        closer = d_prev - target["dist"] > 1.0
        if urgent and now - t_prev > 2.5 or (not urgent and (now - t_prev > self.repeat or closer)):
            if not urgent and self.sp.busy():
                return None
            text = sentence(self.sp.lang, target, urgent)
            self.sp.say(text, urgent)
            self.last[target["cls"]] = (now, target["dist"])
            self.last_text = text
            return {"text": text, "level": 3 if urgent else 2 if target["dist"] < 1.5 else 1, "t": now}
        return None
