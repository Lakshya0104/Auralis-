// Multilingual phrase tables. Speech uses the phone's built-in TTS voices
// (Settings > Text-to-speech on Android: install the language pack once).
// Have a native speaker check each table before your demo.

export const LANGS = {
  en: { code: 'en-IN', name: 'English', english: 'English' },
  hi: { code: 'hi-IN', name: 'हिन्दी', english: 'Hindi' },
  te: { code: 'te-IN', name: 'తెలుగు', english: 'Telugu' },
  ta: { code: 'ta-IN', name: 'தமிழ்', english: 'Tamil' },
};

const OBJECTS = {
  en: {
        pothole: 'pothole', open_drain: 'open drain', stairs_down: 'stairs going down', curb: 'kerb edge',
        stairs_up: 'stairs going up', step_up: 'step up', speed_breaker: 'speed breaker', pole: 'pole', tree: 'tree',
        wall: 'wall', barrier: 'barrier', dustbin: 'dustbin', branch: 'branch', signboard: 'signboard',
        construction: 'construction work', auto_rickshaw: 'auto rickshaw',
        person: 'person', bicycle: 'bicycle', car: 'car', motorcycle: 'motorbike', bus: 'bus', truck: 'truck',
        dog: 'dog', cow: 'cow', chair: 'chair', bench: 'bench', 'fire hydrant': 'pole', 'stop sign': 'sign board',
        'potted plant': 'plant pot', obstacle: 'obstacle', drop: 'step down or pit', 'traffic light': 'traffic signal' },
  hi: {
        pothole: 'गड्ढा', open_drain: 'खुला नाला', stairs_down: 'नीचे जाती सीढ़ियाँ', curb: 'फुटपाथ का किनारा',
        stairs_up: 'ऊपर जाती सीढ़ियाँ', step_up: 'ऊँचा कदम', speed_breaker: 'स्पीड ब्रेकर', pole: 'खंभा', tree: 'पेड़',
        wall: 'दीवार', barrier: 'बैरियर', dustbin: 'कूड़ेदान', branch: 'डाली', signboard: 'साइनबोर्ड',
        construction: 'निर्माण कार्य', auto_rickshaw: 'ऑटो रिक्शा',
        person: 'व्यक्ति', bicycle: 'साइकिल', car: 'कार', motorcycle: 'मोटरसाइकिल', bus: 'बस', truck: 'ट्रक',
        dog: 'कुत्ता', cow: 'गाय', chair: 'कुर्सी', bench: 'बेंच', 'fire hydrant': 'खंभा', 'stop sign': 'बोर्ड',
        'potted plant': 'गमला', obstacle: 'रुकावट', drop: 'गड्ढा या सीढ़ी', 'traffic light': 'ट्रैफिक सिग्नल' },
  te: {
        pothole: 'గుంత', open_drain: 'తెరిచిన కాలువ', stairs_down: 'కిందికి మెట్లు', curb: 'ఫుట్‌పాత్ అంచు',
        stairs_up: 'పైకి మెట్లు', step_up: 'ఎత్తైన మెట్టు', speed_breaker: 'స్పీడ్ బ్రేకర్', pole: 'స్తంభం', tree: 'చెట్టు',
        wall: 'గోడ', barrier: 'అడ్డుకట్ట', dustbin: 'చెత్త డబ్బా', branch: 'కొమ్మ', signboard: 'బోర్డు',
        construction: 'నిర్మాణ పనులు', auto_rickshaw: 'ఆటో',
        person: 'వ్యక్తి', bicycle: 'సైకిల్', car: 'కారు', motorcycle: 'బైక్', bus: 'బస్సు', truck: 'లారీ',
        dog: 'కుక్క', cow: 'ఆవు', chair: 'కుర్చీ', bench: 'బెంచ్', 'fire hydrant': 'స్తంభం', 'stop sign': 'బోర్డు',
        'potted plant': 'కుండీ', obstacle: 'అడ్డంకి', drop: 'గుంత లేదా మెట్టు', 'traffic light': 'ట్రాఫిక్ సిగ్నల్' },
  ta: {
        pothole: 'பள்ளம்', open_drain: 'திறந்த கால்வாய்', stairs_down: 'கீழே இறங்கும் படிகள்', curb: 'நடைபாதை ஓரம்',
        stairs_up: 'மேலே ஏறும் படிகள்', step_up: 'உயரமான படி', speed_breaker: 'வேகத்தடை', pole: 'கம்பம்', tree: 'மரம்',
        wall: 'சுவர்', barrier: 'தடுப்பு', dustbin: 'குப்பைத் தொட்டி', branch: 'கிளை', signboard: 'பலகை',
        construction: 'கட்டுமானப் பணி', auto_rickshaw: 'ஆட்டோ',
        person: 'நபர்', bicycle: 'சைக்கிள்', car: 'கார்', motorcycle: 'பைக்', bus: 'பேருந்து', truck: 'லாரி',
        dog: 'நாய்', cow: 'மாடு', chair: 'நாற்காலி', bench: 'பெஞ்ச்', 'fire hydrant': 'கம்பம்', 'stop sign': 'பலகை',
        'potted plant': 'தொட்டி', obstacle: 'தடை', drop: 'குழி அல்லது படி', 'traffic light': 'சிக்னல்' },
};

const PHRASES = {
  en: {
    head: (o, m) => `${o} at head height, ${m} ${m === 1 ? 'metre' : 'metres'}`,
    approaching: (o) => `${o} coming towards you`,
    linkLost: 'Camera link lost. Use your cane carefully.',
    ahead: (o, m) => `${o} ahead, ${m} ${m === 1 ? 'metre' : 'metres'}`,
    left: (o, m) => `${o} on your left, ${m} ${m === 1 ? 'metre' : 'metres'}`,
    right: (o, m) => `${o} on your right, ${m} ${m === 1 ? 'metre' : 'metres'}`,
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
    head: (o, m) => `सिर की ऊँचाई पर ${o}, ${m} मीटर`,
    approaching: (o) => `${o} आपकी ओर आ रहा है`,
    linkLost: 'कैमरा से संपर्क टूट गया. छड़ी से सावधानी से चलिए.',
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
    head: (o, m) => `తల ఎత్తులో ${o}, ${m} మీటర్లు`,
    approaching: (o) => `${o} మీ వైపు వస్తోంది`,
    linkLost: 'కెమెరా కనెక్షన్ పోయింది. కర్రతో జాగ్రత్తగా నడవండి.',
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
    head: (o, m) => `தலை உயரத்தில் ${o}, ${m} மீட்டர்`,
    approaching: (o) => `${o} உங்களை நோக்கி வருகிறது`,
    linkLost: 'கேமரா இணைப்பு துண்டிக்கப்பட்டது. கைத்தடியுடன் கவனமாக நடக்கவும்.',
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

let rate = 1;
export const setRate = (r) => { rate = r; };
let lastSpoken = '';
let lastAt = 0;
// priority: 0 = info, 1 = warning, 2 = urgent (interrupts)
export function speak(text, priority = 0) {
  if (!('speechSynthesis' in window)) return;
  const now = Date.now();
  if (text === lastSpoken && now - lastAt < 4000) return;
  if (speechSynthesis.speaking) {
    if (priority < 2) return;
    speechSynthesis.cancel();
  }
  const u = new SpeechSynthesisUtterance(text);
  u.lang = LANGS[lang].code;
  u.rate = rate * (priority === 2 ? 1.15 : 1);
  speechSynthesis.speak(u);
  lastSpoken = text;
  lastAt = now;
}
