import { LANGS, setLang, t, obj, speak } from './i18n.js';
import * as mem from './memory.js';
import { route } from './router.js';
import { loadFusion, fuse } from './fusion.js';

const $ = (id) => document.getElementById(id);
const SVC = '6e400001-b5a3-f393-e0a9-e50e24dcca9e';
const RX = '6e400002-b5a3-f393-e0a9-e50e24dcca9e';
const TX = '6e400003-b5a3-f393-e0a9-e50e24dcca9e';
const LEVEL_NAMES = ['Clear', 'Caution', 'Warning', 'STOP'];
const RELEVANT = new Set(['person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 'dog', 'cow', 'chair', 'bench',
  'fire hydrant', 'stop sign', 'potted plant', 'traffic light']);

const state = {
  front: 400, down: null, ground: null, frontHist: [], button: false,
  pos: null, heading: null, det: null, features: null,
  rx: null, model: null, guiding: null, training: [], lastAlert: 0, lastLevel: 0, lastMemWarn: new Map(),
};

function log(msg) {
  const el = $('log');
  el.textContent = `${new Date().toLocaleTimeString()} ${msg}\n` + el.textContent.slice(0, 4000);
}

// ---------- language ----------
for (const [k, v] of Object.entries(LANGS)) $('lang').add(new Option(v.name, k));
$('lang').value = localStorage.getItem('auralis-lang') || 'en';
setLang($('lang').value);
$('lang').onchange = () => { setLang($('lang').value); localStorage.setItem('auralis-lang', $('lang').value); speak(LANGS[$('lang').value].name); };

// ---------- cane over BLE ----------
$('btnCane').onclick = async () => {
  try {
    const dev = await navigator.bluetooth.requestDevice({ filters: [{ services: [SVC] }] });
    dev.addEventListener('gattserverdisconnected', () => { state.rx = null; speak(t('disconnected'), 1); log('cane disconnected'); });
    const svc = await (await dev.gatt.connect()).getPrimaryService(SVC);
    state.rx = await svc.getCharacteristic(RX);
    const tx = await svc.getCharacteristic(TX);
    tx.addEventListener('characteristicvaluechanged', (e) => onCanePacket(new TextDecoder().decode(e.target.value)));
    await tx.startNotifications();
    speak(t('connected'));
    log('cane connected');
  } catch (e) { log('BLE: ' + e.message); }
};

function onCanePacket(s) {
  const v = Object.fromEntries(s.split(',').map((p) => p.split(':')).map(([k, n]) => [k, +n]));
  state.front = v.F; state.down = v.D; state.ground = v.G;
  const btn = v.B === 1;
  if (btn && !state.button) whereAmI();       // cane button = "where am I"
  state.button = btn;
  state.frontHist.push({ t: performance.now(), f: v.F });
  if (state.frontHist.length > 10) state.frontHist.shift();
  $('sFront').textContent = v.F >= 400 ? '>4m' : (v.F / 100).toFixed(1) + 'm';
  $('sDown').textContent = v.D - v.G > 25 ? 'DROP' : 'ok';
}

let vibrateBusy = false;
async function vibrateCane(level) {
  if (navigator.vibrate) navigator.vibrate([0, [80], [150, 100, 150], [250, 80, 250, 80, 250]][level] || 0);
  if (!state.rx || vibrateBusy) return;
  vibrateBusy = true;
  try { await state.rx.writeValueWithoutResponse(new TextEncoder().encode('V' + level)); } catch {}
  vibrateBusy = false;
}

// ---------- camera + detector ----------
async function startCamera() {
  const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: 640, height: 480 }, audio: false });
  $('video').srcObject = stream;
  await $('video').play();
  state.model = await cocoSsd.load({ base: 'lite_mobilenet_v2' });
  log('detector ready');
  detectLoop();
}

async function detectLoop() {
  const v = $('video'), c = $('overlay'), g = c.getContext('2d');
  c.width = v.videoWidth; c.height = v.videoHeight;
  const preds = (await state.model.detect(v, 10, 0.45)).filter((p) => RELEVANT.has(p.class));
  g.clearRect(0, 0, c.width, c.height);
  let best = null, bestScore = 0;
  for (const p of preds) {
    const [x, y, w, h] = p.bbox;
    const area = (w * h) / (c.width * c.height);
    const cx = (x + w / 2) / c.width;
    const offset = Math.min(Math.abs(cx - 0.5) * 2, 1);
    const sev = mem.severityOf(p.class);
    const score = sev * p.score * (1 - offset * 0.7) + area;
    if (score > bestScore) { bestScore = score; best = { cls: p.class, conf: p.score, area, offset, side: cx < 0.4 ? 'left' : cx > 0.6 ? 'right' : 'ahead' }; }
    g.strokeStyle = '#ffd400'; g.lineWidth = 3; g.strokeRect(x, y, w, h);
    g.fillStyle = '#ffd400'; g.font = '18px sans-serif'; g.fillText(`${p.class} ${(p.score * 100) | 0}%`, x + 4, y + 20);
  }
  state.det = best;
  tick();
  setTimeout(detectLoop, 150);
}

// ---------- fusion + alerts ----------
function features() {
  const d = state.det;
  const drop = state.down != null && state.ground != null ? Math.max(-1, Math.min(1, (state.down - state.ground) / 100)) : 0;
  let approach = 0;
  const h = state.frontHist;
  if (h.length > 3) {
    const dt = (h.at(-1).t - h[0].t) / 1000;
    approach = Math.max(0, Math.min(1, ((h[0].f - h.at(-1).f) / dt) / 100));
  }
  const memRisk = state.pos ? Math.min(1, mem.hazardsAhead(state.pos, state.heading, 15).reduce((s, x) => s + x.risk, 0)) : 0;
  return [Math.min(state.front, 400) / 400, drop, d ? mem.severityOf(d.cls) : 0, d ? d.conf : 0,
          d ? Math.min(d.area, 1) : 0, d ? d.offset : 1, memRisk, approach];
}

function tick() {
  const x = features();
  state.features = x;
  const { level } = fuse(x);
  const el = $('level');
  el.textContent = LEVEL_NAMES[level] + (state.det ? ` · ${state.det.cls}` : '');
  el.className = 'l' + level;

  const now = Date.now();
  const cooldown = [Infinity, 6000, 3000, 1500][level];
  if (level > 0 && (level > state.lastLevel || now - state.lastAlert > cooldown)) {
    const isDrop = x[1] > 0.25;
    const name = obj(isDrop ? 'drop' : state.det ? state.det.cls : 'obstacle');
    const metres = state.front < 400 ? Math.max(1, Math.round(state.front / 100)) : 3;
    const side = state.det && !isDrop ? state.det.side : 'ahead';
    speak(level === 3 ? t('stop', name) : t(side, name, metres), level === 3 ? 2 : 1);
    vibrateCane(level);
    state.lastAlert = now;
    // Remember real hazards (not people walking past) with their location
    if (level >= 2 && state.pos && (isDrop || (state.det && state.det.cls !== 'person'))) {
      mem.recordHazard(state.pos, isDrop ? 'drop' : state.det ? state.det.cls : 'obstacle', state.det?.conf ?? 0.8, state.front / 100);
      refreshStats();
    }
  }
  state.lastLevel = level;
}

// ---------- location, compass, memory warnings, guidance ----------
function startLocation() {
  navigator.geolocation.watchPosition((p) => {
    state.pos = { lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy };
    if (p.coords.speed > 0.5 && p.coords.heading != null && !isNaN(p.coords.heading)) state.heading = p.coords.heading;
    $('sGps').textContent = '±' + Math.round(p.coords.accuracy) + 'm';
    mem.addBreadcrumb(state.pos);
    warnRemembered();
    guide();
    refreshStats();
  }, (e) => log('GPS: ' + e.message), { enableHighAccuracy: true, maximumAge: 1000 });

  const onOrient = (e) => {
    const hdg = e.webkitCompassHeading ?? (e.absolute && e.alpha != null ? 360 - e.alpha : null);
    if (hdg != null) state.heading = hdg;
  };
  addEventListener('deviceorientationabsolute', onOrient);
  addEventListener('deviceorientation', onOrient);
}

function warnRemembered() {
  for (const { h, d } of mem.hazardsAhead(state.pos, state.heading, 25)) {
    const last = state.lastMemWarn.get(h.id) || 0;
    if (Date.now() - last > 120000 && d > 3) {
      speak(t('remembered', obj(h.cls), Math.round(d)), 1);
      vibrateCane(1);
      state.lastMemWarn.set(h.id, Date.now());
      log(`memory: ${h.cls} seen ${h.count}x, ${Math.round(d)}m ahead`);
      return;
    }
  }
}

let lastGuide = 0;
function guide() {
  const g = state.guiding;
  if (!g || !state.pos || Date.now() - lastGuide < 6000) return;
  lastGuide = Date.now();
  const dest = g.place;
  const dist = mem.distM(state.pos, dest);
  if (dist < 8) { speak(t('arrived', dest.name), 1); vibrateCane(4); state.guiding = null; return; }
  // follow the safest learned route; aim for the next waypoint ~10 m ahead
  const gr = mem.graph();
  const r = route(gr, mem.nearestNode(state.pos)?.id ?? dest.node, dest.node);
  let target = dest;
  if (r) {
    target = r.path.map((id) => gr.nodes[id]).find((n) => mem.distM(state.pos, n) > 10) || dest;
  }
  const rel = state.heading == null ? 0 : (mem.bearing(state.pos, target) - state.heading + 360) % 360;
  const dirs = t('dirs');
  const idx = rel < 20 || rel > 340 ? 0 : rel < 60 ? 1 : rel < 150 ? 2 : rel < 210 ? 3 : rel < 300 ? 4 : 5;
  speak(t('toPlace', dest.name, Math.round(dist), dirs[idx]));
}

function whereAmI() {
  if (!state.pos) return;
  const n = mem.nearestPlace(state.pos);
  if (n) speak(t('whereAmI', n.p.name, Math.round(n.d)));
}

// ---------- UI ----------
function refreshStats() {
  const d = mem.dump();
  $('sHaz').textContent = d.hazards.length;
  $('sPlaces').textContent = d.places.length;
  $('sNodes').textContent = d.nodes.length;
  const box = $('places');
  box.innerHTML = '';
  for (const p of d.places) {
    const b = document.createElement('button');
    b.textContent = p.name;
    b.onclick = () => { state.guiding = { place: p }; lastGuide = 0; guide(); };
    box.append(b);
  }
}

$('btnStart').onclick = async () => {
  speak('AURALIS');
  startLocation();
  try { await startCamera(); } catch (e) { log('camera: ' + e.message + ' — running on cane sensors only'); setInterval(tick, 200); }
  $('btnStart').disabled = true;
};

$('btnSave').onclick = () => {
  if (!state.pos) return log('no GPS fix yet');
  const store = (name) => { if (!name) return; mem.savePlace(state.pos, name); speak(t('saved', name)); refreshStats(); };
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return store(prompt('Name this place'));
  const rec = new SR();
  rec.lang = LANGS[$('lang').value].code;
  rec.onresult = (e) => store(e.results[0][0].transcript);
  rec.onerror = () => store(prompt('Name this place'));
  rec.start();
};

$('btnWhere').onclick = whereAmI;
$('btnStop').onclick = () => { state.guiding = null; speechSynthesis.cancel(); };
$('btnGone').onclick = () => { if (state.pos) { mem.clearHazardsNear(state.pos); refreshStats(); vibrateCane(4); } };

document.querySelectorAll('[data-label]').forEach((b) => b.onclick = () => {
  if (!state.features) return;
  state.training.push([...state.features, +b.dataset.label]);
  log(`labelled ${b.textContent} (${state.training.length} rows)`);
});

function download(name, text) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text]));
  a.download = name;
  a.click();
}
$('btnExport').onclick = () => download('auralis_training.csv',
  'front,drop,severity,conf,area,offset,memory,approach,label\n' + state.training.map((r) => r.map((v) => +v.toFixed(4)).join(',')).join('\n'));
$('btnExportMem').onclick = () => download('auralis_memory.json', JSON.stringify(mem.dump(), null, 1));

$('btnRoutes').onclick = () => {
  const p = mem.places()[0];
  if (!p || !state.pos) return log('need a saved place and a GPS fix');
  const g = mem.graph(), start = mem.nearestNode(state.pos)?.id;
  if (start == null) return speak(t('noRoute'));
  const short = route(g, start, p.node, 0), safe = route(g, start, p.node);
  if (!short) return speak(t('noRoute'));
  log(`shortest: ${short.length.toFixed(0)} m, risk ${short.risk.toFixed(2)} | safest: ${safe.length.toFixed(0)} m, risk ${safe.risk.toFixed(2)}`);
};

loadFusion().then((ok) => log(ok ? 'neural fusion model loaded' : 'fusion weights missing — using rules'));
refreshStats();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
