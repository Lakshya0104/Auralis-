import { LANGS, setLang, t, obj, speak } from './i18n.js';
import * as mem from './memory.js';
import { route } from './router.js';
import { loadFusion, fuse } from './fusion.js';

// The Pi serves this page and streams obstacles from pi/server.py on /ws.
// The phone adds GPS, compass, voice, vibration, memory and routing.

const $ = (id) => document.getElementById(id);
const LEVEL_NAMES = ['Clear', 'Caution', 'Warning', 'STOP'];
const VIBRATION = [0, [80], [150, 100, 150], [250, 80, 250, 80, 250]];

const state = {
  pos: null, heading: null, frame: null, primary: null, features: null,
  guiding: null, training: [], lastAlert: 0, lastLevel: 0, lastMemWarn: new Map(), lastFrameAt: 0,
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

// ---------- link to the Pi ----------
function connectPi() {
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  ws.onopen = () => { $('sLink').textContent = 'on'; speak(t('connected')); log('Pi connected'); };
  ws.onmessage = (e) => onFrame(JSON.parse(e.data));
  ws.onclose = () => { $('sLink').textContent = 'off'; setTimeout(connectPi, 2000); };
}
// Safety: if perception stops (Pi crash, Wi-Fi drop), tell the user instead of going silent
setInterval(() => {
  if (state.lastFrameAt && Date.now() - state.lastFrameAt > 3000) {
    speak(t('linkLost'), 2);
    navigator.vibrate?.([400, 200, 400]);
    state.lastFrameAt = 0;
  }
}, 1000);

function onFrame(f) {
  state.frame = f;
  state.lastFrameAt = Date.now();
  $('sFps').textContent = f.fps;
  $('sDown').textContent = f.ultra.drop ? 'DROP' : f.ultra.raised ? 'STEP' : f.ultra.cm ? 'ok' : '–';
  // The most important obstacle: in the walking corridor, nearest first (the Pi sorts them)
  state.primary = f.obstacles.find((o) => o.inCorridor) || null;
  const p = state.primary;
  $('sFront').textContent = p ? p.dist.toFixed(1) + 'm' : '–';
  decide(f);
}

// ---------- fusion + alerts ----------
// Feature vector for the fusion network (must match ml/train_fusion.py)
function features(f) {
  const o = state.primary;
  const u = f.ultra;
  const drop = u.cm != null && u.baseline != null ? Math.max(-1, Math.min(1, (u.cm - u.baseline) / 100)) : 0;
  const memRisk = state.pos
    ? Math.min(1, mem.hazardsAhead(state.pos, state.heading, 15).reduce((s, x) => s + x.risk, 0)) : 0;
  return [o ? Math.min(o.dist, 4) / 4 : 1, drop, o ? o.severity : 0, o ? o.conf : 0,
          o ? Math.min(o.area, 1) : 0, o ? o.offset : 1, memRisk, o ? Math.max(0, Math.min(1, o.approach / 2)) : 0];
}

function phrase(o, level) {
  const name = obj(o.cls);
  const m = Math.max(1, Math.round(o.dist));
  if (level === 3) return t('stop', name);
  if (o.category === 'moving' && o.approach > 0.5) return t('approaching', name);
  if (o.category === 'head') return t('head', name, m);
  return t(o.side, name, m);
}

function decide(f) {
  const x = features(f);
  state.features = x;
  let { level } = fuse(x);
  const o = state.primary;
  // Safety override: a drop / pit is always STOP; the network may raise but never lower this
  if (o && o.category === 'drop' && o.dist < 1.5) level = 3;
  if (!o && x[6] < 0.3) level = Math.min(level, 1);

  const el = $('level');
  el.textContent = LEVEL_NAMES[level] + (o ? ` · ${o.cls} ${o.dist.toFixed(1)}m` : '');
  el.className = 'l' + level;

  const now = Date.now();
  const cooldown = [Infinity, 6000, 3000, 1500][level];
  if (o && level > 0 && (level > state.lastLevel || now - state.lastAlert > cooldown)) {
    speak(phrase(o, level), level === 3 ? 2 : 1);
    navigator.vibrate?.(VIBRATION[level]);
    state.lastAlert = now;
    // Remember static hazards where they are (ahead of the user), never people / moving traffic
    if (level >= 2 && o.remember && state.pos && state.pos.accuracy < 30) {
      const where = state.heading != null ? mem.offset(state.pos, state.heading, o.dist) : state.pos;
      mem.recordHazard(where, o.cls, o.conf, o.dist, o.severity, o.category);
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

// Feature 1: warn about remembered hazards long before the camera can see them
function warnRemembered() {
  for (const { h, d } of mem.hazardsAhead(state.pos, state.heading, 25)) {
    const last = state.lastMemWarn.get(h.id) || 0;
    if (Date.now() - last > 120000 && d > 4) {
      speak(t('remembered', obj(h.cls), Math.round(d)), 1);
      navigator.vibrate?.(VIBRATION[1]);
      state.lastMemWarn.set(h.id, Date.now());
      log(`memory: ${h.cls} seen ${h.count}x, ${Math.round(d)}m ahead`);
      return;
    }
  }
}

// Feature 2: guide to a saved place along the safest learned route
let lastGuide = 0;
function guide() {
  const g = state.guiding;
  if (!g || !state.pos || Date.now() - lastGuide < 6000) return;
  lastGuide = Date.now();
  const dest = g.place;
  const dist = mem.distM(state.pos, dest);
  if (dist < 8) { speak(t('arrived', dest.name), 1); navigator.vibrate?.(VIBRATION[1]); state.guiding = null; return; }
  const gr = mem.graph();
  const start = mem.nearestNode(state.pos);
  const r = start ? route(gr, start.id, dest.node) : null;
  let target = dest;
  if (r) target = r.path.map((id) => gr.nodes[id]).find((n) => mem.distM(state.pos, n) > 10) || dest;
  const rel = state.heading == null ? 0 : (mem.bearing(state.pos, target) - state.heading + 360) % 360;
  const idx = rel < 20 || rel > 340 ? 0 : rel < 60 ? 1 : rel < 150 ? 2 : rel < 210 ? 3 : rel < 300 ? 4 : 5;
  speak(t('toPlace', dest.name, Math.round(dist), t('dirs')[idx]));
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
  const box = $('places');
  box.innerHTML = '';
  for (const p of d.places) {
    const b = document.createElement('button');
    b.textContent = p.name;
    b.onclick = () => { state.guiding = { place: p }; lastGuide = 0; guide(); };
    box.append(b);
  }
}

$('btnStart').onclick = () => {
  speak('AURALIS');
  startLocation();
  connectPi();
  $('video').src = '/video.mjpg';
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
$('btnGone').onclick = () => { if (state.pos) { mem.clearHazardsNear(state.pos); refreshStats(); navigator.vibrate?.(60); } };

// Research mode: label real situations to train the fusion network on field data
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
  const start = state.pos && mem.nearestNode(state.pos);
  if (!p || !start) return log('need a saved place and a GPS fix');
  const g = mem.graph();
  const short = route(g, start.id, p.node, 0), safe = route(g, start.id, p.node);
  if (!short) return speak(t('noRoute'));
  log(`shortest: ${short.length.toFixed(0)} m, risk ${short.risk.toFixed(2)} | safest: ${safe.length.toFixed(0)} m, risk ${safe.risk.toFixed(2)}`);
};

loadFusion().then((ok) => log(ok ? 'neural fusion model loaded' : 'fusion weights missing — using rules'));
refreshStats();
// (fails harmlessly with the Pi's self-signed certificate; works when hosted with a real one)
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
