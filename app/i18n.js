// Multilingual phrase tables. Speech uses the phone's built-in TTS voices
// (Settings > Text-to-speech on Android: install the language pack once).
// Have a native speaker check each table before your demo.

export const LANGS = {
  en: { code: 'en-IN', name: 'English' },
  hi: { code: 'hi-IN', name: 'हिन्दी' },
  te: { code: 'te-IN', name: 'తెలుగు' },
  ta: { code: 'ta-IN', name: 'தமிழ்' },
};

const OBJECTS = {
  en: { person: 'person', bicycle: 'bicycle', car: 'car', motorcycle: 'motorbike', bus: 'bus', truck: 'truck',
        dog: 'dog', cow: 'cow', chair: 'chair', bench: 'bench', 'fire hydrant': 'pole', 'stop sign': 'sign board',
        'potted plant': 'plant pot', obstacle: 'obstacle', drop: 'step down or pit', 'traffic light': 'traffic signal' },
  hi: { person: 'व्यक्ति', bicycle: 'साइकिल', car: 'कार', motorcycle: 'मोटरसाइकिल', bus: 'बस', truck: 'ट्रक',
        dog: 'कुत्ता', cow: 'गाय', chair: 'कुर्सी', bench: 'बेंच', 'fire hydrant': 'खंभा', 'stop sign': 'बोर्ड',
        'potted plant': 'गमला', obstacle: 'रुकावट', drop: 'गड्ढा या सीढ़ी', 'traffic light': 'ट्रैफिक सिग्नल' },
  te: { person: 'వ్యక్తి', bicycle: 'సైకిల్', car: 'కారు', motorcycle: 'బైక్', bus: 'బస్సు', truck: 'లారీ',
        dog: 'కుక్క', cow: 'ఆవు', chair: 'కుర్చీ', bench: 'బెంచ్', 'fire hydrant': 'స్తంభం', 'stop sign': 'బోర్డు',
        'potted plant': 'కుండీ', obstacle: 'అడ్డంకి', drop: 'గుంత లేదా మెట్టు', 'traffic light': 'ట్రాఫిక్ సిగ్నల్' },
  ta: { person: 'நபர்', bicycle: 'சைக்கிள்', car: 'கார்', motorcycle: 'பைக்', bus: 'பேருந்து', truck: 'லாரி',
        dog: 'நாய்', cow: 'மாடு', chair: 'நாற்காலி', bench: 'பெஞ்ச்', 'fire hydrant': 'கம்பம்', 'stop sign': 'பலகை',
        'potted plant': 'தொட்டி', obstacle: 'தடை', drop: 'குழி அல்லது படி', 'traffic light': 'சிக்னல்' },
};

const PHRASES = {
  en: {
    ahead: (o, m) => `${o} ahead, ${m} metres`,
    left: (o, m) => `${o} on your left, ${m} metres`,
    right: (o, m) => `${o} on your right, ${m} metres`,
    stop: (o) => `Stop. ${o}`,
    remembered: (o, m) => `Careful. Remembered ${o}, ${m} metres ahead`,
    saved: (p) => `Saved ${p}`,
    toPlace: (p, m, dir) => `${p}, ${m} metres, ${dir}`,
    arrived: (p) => `You have arrived at ${p}`,
    dirs: ['straight ahead', 'slightly right', 'turn right', 'behind you', 'turn left', 'slightly left'],
    connected: 'Cane connected', disconnected: 'Cane disconnected',
    noRoute: 'No known path yet. Walk it once and I will learn it.',
    whereAmI: (p, m) => `Nearest saved place is ${p}, ${m} metres away`,
  },
  hi: {
    ahead: (o, m) => `आगे ${o}, ${m} मीटर`,
    left: (o, m) => `बाईं ओर ${o}, ${m} मीटर`,
    right: (o, m) => `दाईं ओर ${o}, ${m} मीटर`,
    stop: (o) => `रुकिए. ${o}`,
    remembered: (o, m) => `सावधान. ${m} मीटर आगे ${o} याद है`,
    saved: (p) => `${p} सेव हो गया`,
    toPlace: (p, m, dir) => `${p}, ${m} मीटर, ${dir}`,
    arrived: (p) => `आप ${p} पहुँच गए`,
    dirs: ['सीधे', 'थोड़ा दाएँ', 'दाएँ मुड़ें', 'पीछे', 'बाएँ मुड़ें', 'थोड़ा बाएँ'],
    connected: 'छड़ी जुड़ गई', disconnected: 'छड़ी का कनेक्शन टूट गया',
    noRoute: 'अभी रास्ता पता नहीं. एक बार चलिए, मैं सीख लूँगा.',
    whereAmI: (p, m) => `सबसे पास ${p} है, ${m} मीटर दूर`,
  },
  te: {
    ahead: (o, m) => `ముందు ${o}, ${m} మీటర్లు`,
    left: (o, m) => `ఎడమ వైపు ${o}, ${m} మీటర్లు`,
    right: (o, m) => `కుడి వైపు ${o}, ${m} మీటర్లు`,
    stop: (o) => `ఆగండి. ${o}`,
    remembered: (o, m) => `జాగ్రత్త. ${m} మీటర్ల ముందు ${o} ఉంది`,
    saved: (p) => `${p} సేవ్ అయింది`,
    toPlace: (p, m, dir) => `${p}, ${m} మీటర్లు, ${dir}`,
    arrived: (p) => `మీరు ${p} చేరుకున్నారు`,
    dirs: ['నేరుగా', 'కొంచెం కుడి', 'కుడికి తిరగండి', 'వెనుక', 'ఎడమకు తిరగండి', 'కొంచెం ఎడమ'],
    connected: 'కర్ర కనెక్ట్ అయింది', disconnected: 'కర్ర డిస్‌కనెక్ట్ అయింది',
    noRoute: 'ఈ దారి ఇంకా తెలియదు. ఒకసారి నడవండి, నేను నేర్చుకుంటాను.',
    whereAmI: (p, m) => `దగ్గరలో ${p}, ${m} మీటర్ల దూరం`,
  },
  ta: {
    ahead: (o, m) => `முன்னால் ${o}, ${m} மீட்டர்`,
    left: (o, m) => `இடது பக்கம் ${o}, ${m} மீட்டர்`,
    right: (o, m) => `வலது பக்கம் ${o}, ${m} மீட்டர்`,
    stop: (o) => `நில்லுங்கள். ${o}`,
    remembered: (o, m) => `கவனம். ${m} மீட்டர் முன்னால் ${o} உள்ளது`,
    saved: (p) => `${p} சேமிக்கப்பட்டது`,
    toPlace: (p, m, dir) => `${p}, ${m} மீட்டர், ${dir}`,
    arrived: (p) => `${p} வந்துவிட்டீர்கள்`,
    dirs: ['நேராக', 'சற்று வலது', 'வலது திரும்புங்கள்', 'பின்னால்', 'இடது திரும்புங்கள்', 'சற்று இடது'],
    connected: 'கைத்தடி இணைந்தது', disconnected: 'கைத்தடி துண்டிக்கப்பட்டது',
    noRoute: 'இந்த வழி இன்னும் தெரியாது. ஒருமுறை நடந்தால் கற்றுக்கொள்வேன்.',
    whereAmI: (p, m) => `அருகில் ${p}, ${m} மீட்டர் தூரம்`,
  },
};

let lang = 'en';
export const setLang = (l) => { lang = l; };
export const getLang = () => lang;
export const obj = (cls) => OBJECTS[lang][cls] || OBJECTS.en[cls] || cls;
export const t = (key, ...args) => {
  const p = PHRASES[lang][key] ?? PHRASES.en[key];
  return typeof p === 'function' ? p(...args) : p;
};

let lastSpoken = '';
let lastAt = 0;
// priority: 0 = info, 1 = warning, 2 = urgent (interrupts)
export function speak(text, priority = 0) {
  const now = Date.now();
  if (text === lastSpoken && now - lastAt < 4000) return;
  if (speechSynthesis.speaking) {
    if (priority < 2) return;
    speechSynthesis.cancel();
  }
  const u = new SpeechSynthesisUtterance(text);
  u.lang = LANGS[lang].code;
  u.rate = priority === 2 ? 1.25 : 1.1;
  speechSynthesis.speak(u);
  lastSpoken = text;
  lastAt = now;
}
