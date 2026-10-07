import { LANGS, setLang, getLang, setRate, t, obj, speak, hasVoice } from './i18n.js';
import { u, ago } from './ui-strings.js';
import * as mem from './memory.js';
import { route } from './router.js';
import { loadFusion, fuse } from './fusion.js';
import * as demo from './demo.js';
// Opened on a phone (not on the Pi's own screen): speak through the phone, so headphones work
const ON_PHONE = !['localhost', '127.0.0.1'].includes(location.hostname) && /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent);

// The Pi (pi/server.py) serves this page and streams obstacles on /ws. The phone adds GPS, compass,
// voice, vibration, memory and routing. Without a Pi, demo mode feeds simulated data in the same format.

const $ = (id) => document.getElementById(id);
const VIBRATION = [0, [80], [150, 100, 150], [250, 80, 250, 80, 250]];
const CATS = ['drop', 'raised', 'static', 'head', 'moving', 'zone'];

const store = {
  get(k, d) { try { const v = localStorage.getItem('auralis-' + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem('auralis-' + k, JSON.stringify(v)); } catch {} },
};

const state = {
  mode: 'connecting', walking: false, pos: null, heading: null, frame: null, primary: null, features: null,
  level: 0, lastAlert: 0, lastLevel: 0, alerts: [], guiding: null, training: [], lastMemWarn: new Map(),
  lastFrameAt: 0, demoStart: Date.now(), walkStart: 0, walkOffset: 0, fusionOn: false,
  vib: store.get('vib', true), simWalk: store.get('simwalk', false), phoneVoice: store.get('phonevoice', ON_PHONE), lead: null, walkTimer: null,
};

// ---------- text ----------
function applyTexts() {
  document.documentElement.lang = getLang();
  $('tagline').textContent = u('tagline');
  $('langBtn').textContent = LANGS[getLang()].name.slice(0, 2);
  $('demoBanner').textContent = u('demoBanner');
  $('btnStart').querySelector('span').textContent = state.walking ? u('stop') : u('start');
  $('btnWhere').querySelector('span').textContent = u('whereAmI');
  $('btnSave').querySelector('span').textContent = u('savePlace');
  $('btnGone').querySelector('span').textContent = u('hazardGone');
  $('corridorTitle').textContent = u('corridor');
  $('corridorHint').textContent = u('corridorHint');
  $('handHint').textContent = u('handHint');
  $('alertsTitle').textContent = u('recentAlerts');
  $('helperTitle').textContent = u('helperView');
  u('tabs').forEach((name, i) => { $('t' + i).querySelector('span').textContent = name; });
  $('placesTitle').textContent = u('placesTitle');
  $('placeInput').placeholder = u('placeName');
  $('placeInputLbl').textContent = u('placeName');
  $('btnSavePlace').textContent = u('save');
  $('guidingLbl').textContent = u('guiding');
  $('btnStopGuide').textContent = u('stopGuide');
  $('memoryTitle').textContent = u('memoryTitle');
  $('nHazL').textContent = u('hazardsN'); $('nPlacesL').textContent = u('placesN'); $('nNodesL').textContent = u('pathPoints');
  $('settingsTitle').textContent = u('settingsTitle');
  $('langTitle').textContent = u('language');
  $('rateL').textContent = u('speechRate');
  $('vibL').textContent = u('vibration');
  $('demoL').textContent = u('demoMode'); $('demoHint').textContent = u('demoHint');
  $('simwalkL').textContent = u('simwalk'); $('simwalkHint').textContent = u('simwalkHint');
  $('phonevoiceL').textContent = u('phoneVoice'); $('phonevoiceHint').textContent = u('phoneVoiceHint');
  $('mapTitle').textContent = u('mapTitle');
  const lg = u('mapLegend');
  $('mapLegend').innerHTML = `<span><i style="background:var(--accent)"></i>${lg[0]}</span><span><i style="background:var(--accent);border-radius:3px"></i>${lg[1]}</span>`
    + `<span><i style="background:var(--cat-drop)"></i>${lg[2]}</span><span><i style="background:var(--muted);height:3px;border-radius:2px"></i>${lg[3]}</span>`;
  $('leadTitle').textContent = u('leadTitle'); $('leadCamL').textContent = u('leadCam'); $('leadMemL').textContent = u('leadMem');
  $('leadHint').textContent = u('leadHint'); $('leadCamS').textContent = u('cameraRange');
  $('researchTitle').textContent = u('research'); $('researchHint').textContent = u('researchHint');
  $('btnExport').textContent = u('exportCsv'); $('btnExportMem').textContent = u('exportMem');
  $('connTitle').textContent = u('connection');
  $('btnReset').textContent = u('resetMemory');
  $('btnCancel').textContent = u('cancel'); $('btnConfirm').textContent = u('confirmErase');
  $('legend').innerHTML = CATS.slice(0, 5).map((c) => `<span><i style="background:var(--cat-${c})"></i>${u('cat')[c]}</span>`).join('');
  $('labelGrid').innerHTML = u('labels').map((l, i) =>
    `<button data-label="${i}" style="background:var(--${['clear', 'caution', 'warning', 'stop'][i]}-soft);color:var(--${['clear', 'caution', 'warning', 'stop'][i]})">${l}</button>`).join('');
  $('labelGrid').querySelectorAll('button').forEach((b) => b.onclick = () => label(+b.dataset.label));
  renderLangs($('langs'));
  renderConn(); renderStatus(); renderAlerts(); renderPlaces(); renderMemory(); renderSettings();
}

function renderLangs(box, onPick) {
  box.innerHTML = '';
  for (const [k, v] of Object.entries(LANGS)) {
    const b = document.createElement('button');
    b.className = 'lang'; b.setAttribute('role', 'radio'); b.setAttribute('aria-checked', k === getLang());
    b.lang = k;
    b.innerHTML = `<b>${v.name}</b><span>${v.english}</span>`;
    b.onclick = () => { chooseLang(k); onPick?.(); };
    box.append(b);
  }
}

function sendLang() { try { if (ws && ws.readyState === 1) ws.send(JSON.stringify({ lang: getLang() })); } catch {} }
function chooseLang(k) {
  setLang(k); store.set('lang', k); sendLang();
  if (!hasVoice(k)) toast(`No ${LANGS[k].english} voice on this device: Settings → Text-to-speech → Google → install ${LANGS[k].english}`);
  applyTexts();
  speak(LANGS[k].name);
}

// ---------- one voice for everything the app says ----------
function say(text, priority = 1) {
  const piVoice = state.mode === 'pi' && state.frame?.piVoice;
  if (piVoice) { try { ws.send(JSON.stringify({ say: text, urgent: priority === 2 })); } catch {} }
  if (!piVoice || state.phoneVoice) speak(text, priority);
}

// ---------- the cane's memory lives on the Pi (pi/memory.json) ----------
let pushTimer = null;
function pushMemory(db) {
  clearTimeout(pushTimer);
  pushTimer = setTimeout(() => fetch('/memory', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(db) }).catch(() => {}), 800);
}
async function pullMemory() {
  try {
    const d = await (await fetch('/memory')).json();
    if (d && (d.places?.length || d.hazards?.length || d.nodes?.length)) mem.importDump(d);
    else pushMemory(mem.dump());       // first run: give the Pi what this browser already knows
  } catch {}
  mem.setPersist(pushMemory);
  renderPlaces(); renderMemory();
}

// ---------- connection: Pi or demo ----------
let ws = null;
function connectPi() {
  let opened = false;
  try {
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  } catch { return notConnected(); }
  const giveUp = setTimeout(() => { if (!opened) ws.close(); }, 2500);
  ws.onopen = () => {
    opened = true; clearTimeout(giveUp);
    stopDemo(); state.mode = 'pi'; mem.useStore('auralis-memory-v1'); applySimWalk();
    if (!state.simWalk) pullMemory();
    startLocation();
    $('camera').src = '/video.mjpg';
    renderConn(); applyTexts(); sendLang();
    if (state.walking) speak(t('connected'));
  };
  ws.onmessage = (e) => { if (state.mode === 'pi') onFrame(JSON.parse(e.data)); };
  ws.onclose = () => {
    clearTimeout(giveUp);
    if (state.mode === 'pi' || (!opened && state.mode !== 'demo')) notConnected();
  };
}
// Opened from the Pi but the cane is not answering: say so and retry. Demo data only when the user
// turns on Demo mode in Settings (never silently, so fake objects are never mistaken for real ones).
function notConnected() {
  if (state.mode === 'demo') return;
  state.mode = 'offline'; state.primary = null; renderConn(); renderStatus();
  setTimeout(() => { if (state.mode === 'offline') connectPi(); }, 2000);
}

let demoTimer = null;
function startDemo() {
  if (state.mode === 'demo') return;
  state.mode = 'demo';
  demo.seed();
  state.demoStart = Date.now();
  if (!state.pos) setDemoPos(0);
  demoTimer = setInterval(() => {
    const t0 = (Date.now() - state.demoStart) / 1000;
    if (state.walking) setDemoPos(state.walkOffset + (Date.now() - state.walkStart) / 1000);
    onFrame(demo.frame(t0));
  }, 200);
  $('demo').checked = true;
  renderConn(); applyTexts();
}
function stopDemo() { clearInterval(demoTimer); demoTimer = null; }
function setDemoPos(sec) {
  const p = demo.position(sec);
  state.heading = p.heading;
  onPosition({ lat: p.lat, lon: p.lon, accuracy: p.accuracy });
}

// Safety: if perception stops while walking, say so instead of going silent
setInterval(() => {
  if (state.walking && state.lastFrameAt && Date.now() - state.lastFrameAt > 3000) {
    speak(t('linkLost'), 2); vibrate([400, 200, 400]); state.lastFrameAt = 0;
  }
}, 1000);

function renderConn() {
  const c = $('conn');
  c.className = 'pill ' + (state.mode === 'pi' ? 'on' : state.mode === 'demo' ? 'demo' : '');
  c.textContent = state.mode === 'pi' ? u('connected') : state.mode === 'demo' ? u('demo') : u('offline');
  $('demoBanner').hidden = state.mode !== 'demo';
  $('connInfo').textContent = state.mode === 'pi' ? `${location.host} · ${state.frame?.fps ?? '–'} ${u('fps')}` : c.textContent;
}

// ---------- perception frames -> fusion -> alerts ----------
function features(f) {
  const o = state.primary, us = f.ultra;
  const drop = us.cm != null && us.baseline != null ? Math.max(-1, Math.min(1, (us.cm - us.baseline) / 100)) : 0;
  const memRisk = state.pos ? Math.min(1, mem.hazardsAhead(state.pos, state.heading, 15).reduce((s, x) => s + x.risk, 0)) : 0;
  return [o ? Math.min(o.dist, 4) / 4 : 1, drop, o ? o.severity : 0, o ? o.conf : 0,
          o ? Math.min(o.area, 1) : 0, o ? o.offset : 1, memRisk, o ? Math.max(0, Math.min(1, o.approach / 2)) : 0];
}

function phrase(o, level) {
  const name = obj(o.cls), m = Math.max(1, Math.round(o.dist));
  if (level === 3) return t('stop', name);
  if (o.category === 'moving' && o.approach > 0.5) return t('approaching', name);
  if (o.category === 'head') return t('head', name, m);
  return t(o.side, name, m);
}

function onFrame(f) {
  state.frame = f;
  if (state.mode === 'pi' && typeof f.active === 'boolean' && f.active !== state.walking) setWalking(f.active, false);
  state.lastFrameAt = Date.now();
  state.primary = f.obstacles.find((o) => o.inCorridor) || null;
  const o = state.primary;
  const x = features(f);
  state.features = x;
  let { level } = fuse(x);
  // Safety override: a close drop is always STOP; the network may raise but never lower this
  if (o && o.category === 'drop' && o.dist < 1.5) level = 3;
  if (!o) level = Math.min(level, 1);
  state.level = level;

  // The Pi speaks obstacles itself (novelty 1). Show what it said; the phone only adds vibration.
  if (f.announced && f.announced.t !== state.lastPiSaid) {
    state.lastPiSaid = f.announced.t;
    state.alerts.unshift({ t: Date.now(), text: f.announced.text, level: f.announced.level });
    state.alerts.length = Math.min(state.alerts.length, 6);
    renderAlerts();
    if (state.walking) vibrate(VIBRATION[f.announced.level]);
  }
  if (state.walking && o && level > 0) {
    const now = Date.now();
    const cooldown = [Infinity, 6000, 3000, 1500][level];
    if (level > state.lastLevel || now - state.lastAlert > cooldown) {
      if (!f.piVoice || state.phoneVoice) {
        const text = phrase(o, level);
        speak(text, level === 3 ? 2 : 1);
        vibrate(VIBRATION[level]);
        state.alerts.unshift({ t: now, text, level });
        state.alerts.length = Math.min(state.alerts.length, 6);
        renderAlerts();
      }
      state.lastAlert = now;
      if (level >= 2 && o.remember && state.pos && state.pos.accuracy < 30) {
        const where = state.heading != null ? mem.offset(state.pos, state.heading, o.dist) : state.pos;
        mem.recordHazard(where, o.cls, o.conf, o.dist, o.severity, o.category);
        renderMemory();
      }
    }
  }
  state.lastLevel = level;
  renderStatus();
  drawRadar();
}

function renderStatus() {
  if (state.mode === 'pi' && !state.walking) {
    $('status').dataset.level = 0; $('statusIcon').setAttribute('href', '#i-check');
    $('statusHead').textContent = u('pausedState'); $('statusSub').textContent = u('handHint'); $('statusChip').textContent = u('pausedState');
    return;
  }
  const o = state.primary, lv = state.level;
  $('status').dataset.level = lv;
  $('statusIcon').setAttribute('href', lv === 3 ? '#i-stop' : lv > 0 ? '#i-alert' : '#i-check');
  $('statusHead').textContent = o && lv > 0 ? obj(o.cls).replace(/^./, (c) => c.toUpperCase()) : u('pathClear');
  $('statusSub').textContent = o && lv > 0 ? `${o.dist.toFixed(1)} ${u('metres')} · ${u(o.side)} · ${u('cat')[o.category]}` : u('corridorHint').split('.')[0];
  $('statusChip').textContent = u('levels')[lv];
}

function renderAlerts() {
  const colors = ['clear', 'caution', 'warning', 'stop'];
  $('alerts').innerHTML = state.alerts.length ? state.alerts.map((a) =>
    `<div class="alert-row"><time>${new Date(a.t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time><i class="lv" style="background:var(--${colors[a.level]})"></i><span>${esc(a.text)}</span></div>`).join('')
    : `<p class="empty">${u('noAlerts')}</p>`;
}

// ---------- corridor radar (top-down view, user at the bottom) ----------
function drawRadar() {
  const c = $('radar'), g = c.getContext('2d');
  const dpr = window.devicePixelRatio || 1, W = c.clientWidth, H = c.clientHeight;
  if (!W) return;
  if (c.width !== W * dpr) { c.width = W * dpr; c.height = H * dpr; }
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  const css = getComputedStyle(document.documentElement);
  const col = (n) => css.getPropertyValue('--' + n).trim();
  g.clearRect(0, 0, W, H);
  const pad = 26, range = 4.5, ppm = (H - pad - 14) / range;           // pixels per metre
  const X = (lat) => W / 2 + lat * ppm, Y = (d) => H - pad - d * ppm;
  // corridor band
  g.fillStyle = col('accent-soft');
  g.fillRect(X(-0.5), Y(4), ppm, 4 * ppm);
  // distance rings
  g.strokeStyle = col('line'); g.fillStyle = col('muted'); g.lineWidth = 1;
  g.font = '12px ' + col('font');
  for (let d = 1; d <= 4; d++) {
    g.beginPath(); g.arc(W / 2, Y(0), d * ppm, Math.PI, 2 * Math.PI); g.stroke();
    g.fillText(`${d} m`, W / 2 + 4, Y(d) - 4);
  }
  // remembered hazards ahead (hollow diamonds)
  if (state.pos && state.heading != null) {
    for (const { h, d, b } of mem.hazardsAhead(state.pos, state.heading, range)) {
      const a = ((b - state.heading + 540) % 360 - 180) * Math.PI / 180;
      const x = X(Math.sin(a) * d), y = Y(Math.cos(a) * d);
      g.strokeStyle = col('cat-' + (h.category || 'static')); g.lineWidth = 2.5;
      g.beginPath(); g.moveTo(x, y - 9); g.lineTo(x + 9, y); g.lineTo(x, y + 9); g.lineTo(x - 9, y); g.closePath(); g.stroke();
    }
  }
  // live obstacles (labels are nudged up or down so they never overlap)
  const placed = [];
  for (const o of state.frame?.obstacles || []) {
    if (o.dist > range) continue;
    const x = X(Math.max(-2.2, Math.min(2.2, o.lateral))), y = Y(o.dist);
    g.fillStyle = col('cat-' + o.category);
    g.beginPath(); g.arc(x, y, o.inCorridor ? 10 : 7, 0, 2 * Math.PI); g.fill();
    if (o.inCorridor) { g.strokeStyle = col('surface'); g.lineWidth = 2.5; g.stroke(); }
    g.fillStyle = col('ink'); g.font = '600 13px ' + col('font');
    const label = `${obj(o.cls)} ${o.dist.toFixed(1)}m`;
    const w = g.measureText(label).width;
    const tx = Math.min(W - w - 6, Math.max(6, x + 14));
    let ty = y + 4;
    for (const dy of [0, 18, -18, 36, -36]) {
      if (!placed.some((r) => tx < r.x + r.w && r.x < tx + w && Math.abs(r.y - (y + 4 + dy)) < 16)) { ty = y + 4 + dy; break; }
    }
    placed.push({ x: tx, y: ty, w });
    g.fillText(label, tx, ty);
  }
  // the user
  g.fillStyle = col('ink');
  g.beginPath(); g.moveTo(W / 2, Y(0) - 12); g.lineTo(W / 2 + 9, Y(0) + 6); g.lineTo(W / 2 - 9, Y(0) + 6); g.closePath(); g.fill();
}

// ---------- location ----------
let geoWatch = null;
function startGeo() {
  if (state.mode === 'demo' || state.simWalk || !navigator.geolocation) return;
  if (geoWatch !== null) return;
  geoWatch = navigator.geolocation.watchPosition((p) => {
    if (p.coords.speed > 0.5 && p.coords.heading != null && !isNaN(p.coords.heading)) state.heading = p.coords.heading;
    if (!state.gpsOk) {
      // First real GPS fix: stop the classroom route, centre the map and route on where we really are
      state.gpsOk = true;
      if (state.autoRoute) { state.autoRoute = false; clearInterval(state.walkTimer); state.walkTimer = null; }
      demo.setBase(p.coords.latitude, p.coords.longitude);
      toast(`GPS ±${Math.round(p.coords.accuracy)} m`);
      if (map) map.setView([p.coords.latitude, p.coords.longitude], 18);
    }
    onPosition({ lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy });
  }, () => {}, { enableHighAccuracy: true, maximumAge: 1000 });
  const onOrient = (e) => {
    const hdg = e.webkitCompassHeading ?? (e.absolute && e.alpha != null ? 360 - e.alpha : null);
    if (hdg != null) state.heading = hdg;
  };
  addEventListener('deviceorientationabsolute', onOrient);
  addEventListener('deviceorientation', onOrient);
}

let lastUiPos = 0;
function onPosition(p) {
  state.pos = p;
  if (state.walking) { mem.addBreadcrumb(p); warnRemembered(); guide(); }
  if (Date.now() - lastUiPos > 2000) { lastUiPos = Date.now(); renderPlaces(); renderMemory(); }
  updateMe();
}

// Feature 1: warn about remembered hazards long before the camera can see them
function warnRemembered() {
  for (const { h, d } of mem.hazardsAhead(state.pos, state.heading, 25)) {
    if (Date.now() - (state.lastMemWarn.get(h.id) || 0) > 120000 && d > 4) {
      const text = t('remembered', obj(h.cls), Math.round(d));
      say(text, 1); vibrate(VIBRATION[1]);
      state.lead = { d: Math.round(d), s: Math.round(d / 1.2) };   // walking speed ~1.2 m/s
      renderLead();
      state.lastMemWarn.set(h.id, Date.now());
      state.alerts.unshift({ t: Date.now(), text, level: 1 }); state.alerts.length = Math.min(state.alerts.length, 6);
      renderAlerts();
      return;
    }
  }
}

// Feature 2: guidance to a saved place along the safest learned route
let lastGuide = 0;
function guide(force) {
  const g = state.guiding;
  if (!g || !state.pos || (!force && Date.now() - lastGuide < 8000)) return;
  lastGuide = Date.now();
  const dest = g.place, dist = mem.distM(state.pos, dest);
  if (dist < 8) { say(t('arrived', dest.name), 1); vibrate(VIBRATION[1]); stopGuide(); return; }
  const gr = mem.graph(), start = mem.nearestNode(state.pos);
  const r = start ? route(gr, start.id, dest.node) : null;
  let target = dest;
  if (r) target = r.path.map((id) => gr.nodes[id]).find((n) => mem.distM(state.pos, n) > 10) || dest;
  const rel = state.heading == null ? 0 : (mem.bearing(state.pos, target) - state.heading + 360) % 360;
  const idx = rel < 20 || rel > 340 ? 0 : rel < 60 ? 1 : rel < 150 ? 2 : rel < 210 ? 3 : rel < 300 ? 4 : 5;
  say(t('toPlace', dest.name, Math.round(dist), t('dirs')[idx]));
}
function stopGuide() { state.guiding = null; renderPlaces(); }

// ---------- places ----------
function renderPlaces() {
  const list = $('placesList'), places = mem.places();
  $('guideBox').hidden = !state.guiding;
  if (state.guiding) $('guideName').textContent = state.guiding.place.name;
  if (!places.length) { list.innerHTML = `<p class="empty">${u('placesEmpty')}</p>`; $('routeCard').hidden = true; return; }
  const rows = places.map((p) => ({ p, d: state.pos ? mem.distM(state.pos, p) : null })).sort((a, b) => (a.d ?? 0) - (b.d ?? 0));
  list.innerHTML = rows.map(({ p, d }) => `
    <div class="row">
      <div class="dot" style="background:var(--accent)"><svg width="20" height="20"><use href="#i-pin"/></svg></div>
      <div style="min-width:0"><div class="t">${esc(p.name)}${p.example ? `<span class="tag">${u('example')}</span>` : ''}</div>
        <div class="m">${d != null ? u('away', Math.round(d)) : ''}</div></div>
      <button class="small-btn" data-place="${p.id}">${u('guideMe')}</button>
    </div>`).join('');
  list.querySelectorAll('[data-place]').forEach((b) => b.onclick = () => {
    state.guiding = { place: places.find((p) => p.id === b.dataset.place) };
    renderPlaces(); guide(true);
    if (!state.walking) toggleWalking();
  });
  renderRoute(state.guiding?.place || rows[rows.length - 1].p);
}

// Shortest vs safest route on the self-learned path graph (risk-aware A*)
function renderRoute(dest) {
  const start = state.pos && mem.nearestNode(state.pos), g = mem.graph();
  const short = start && route(g, start.id, dest.node, 0), safe = start && route(g, start.id, dest.node);
  $('routeCard').hidden = !short;
  if (!short) return;
  $('routeTitle').textContent = `${u('routeTitle')} ${dest.name}`;
  const cell = (name, r, best) => `<div class="${best ? 'best' : ''}"><span>${name}</span><b>${Math.round(r.length)} ${u('metres')}</b><span>${u('risk')} ${(r.risk * 100).toFixed(0)}%</span></div>`;
  $('compare').innerHTML = cell(u('shortest'), short, false) + cell(u('safest'), safe, true);
}

$('saveForm').onsubmit = (e) => {
  e.preventDefault();
  const name = $('placeInput').value.trim();
  if (!name) { toast(u('needName')); $('placeInput').focus(); return; }
  if (!state.pos) useRouteLocation();
  mem.savePlace(state.pos, name);
  $('placeInput').value = '';
  say(t('saved', name)); toast(t('saved', name));
  renderPlaces(); renderMemory();
};

// ---------- map (Leaflet + OpenStreetMap; vectors still draw offline) ----------
const CHENNAI = [13.0108, 80.2354];
let map = null, layers = null, meMarker = null;
async function initMap() {
  if (!window.L) return;
  if (!map) {
    try { const css = await (await fetch('vendor/leaflet.css')).text(); const st = document.createElement('style'); st.textContent = css; document.head.prepend(st); } catch {}
    map = L.map('map', { zoomControl: true, attributionControl: true }).setView(state.pos ? [state.pos.lat, state.pos.lon] : CHENNAI, 17);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap' }).addTo(map);
    layers = L.layerGroup().addTo(map);
  }
  setTimeout(() => map.invalidateSize(), 50);
  drawMapLayers();
}
function resetMapLayers() { if (layers) drawMapLayers(); }
function drawMapLayers() {
  if (!map) return;
  layers.clearLayers();
  const css = getComputedStyle(document.documentElement), col = (n) => css.getPropertyValue('--' + n).trim();
  const g = mem.graph();
  for (const e of g.edges) {
    const a = g.nodes[e.a], b = g.nodes[e.b];
    L.polyline([[a.lat, a.lon], [b.lat, b.lon]], { color: col('muted'), weight: 4, opacity: 0.55 }).addTo(layers);
  }
  for (const h of mem.hazards()) {
    const r = mem.hazardRisk(h), c = col('cat-' + (h.category || 'static'));
    L.circleMarker([h.lat, h.lon], { radius: 6 + r * 10, color: c, fillColor: c, fillOpacity: 0.35, weight: 2 })
      .bindPopup(`<b>${esc(obj(h.cls))}</b><br>${u('seen', h.count)} · ${ago(h.lastSeen)}<br>${u('risk')} ${(r * 100).toFixed(0)}%`).addTo(layers);
  }
  for (const p of mem.places()) {
    L.marker([p.lat, p.lon], { icon: L.divIcon({ className: '', html: `<span class="place-pin">${esc(p.name)}</span>`, iconAnchor: [10, 10] }) }).addTo(layers);
  }
  meMarker = null;
  updateMe(true);
}
function updateMe(recenter) {
  if (!map || !state.pos) return;
  const ll = [state.pos.lat, state.pos.lon];
  if (!meMarker) meMarker = L.marker(ll, { icon: L.divIcon({ className: '', html: '<div class="me-dot"></div>', iconSize: [18, 18], iconAnchor: [9, 9] }), zIndexOffset: 1000 }).addTo(layers);
  else meMarker.setLatLng(ll);
  if (recenter || state.walking) map.panTo(ll, { animate: false });
}
function renderLead() {
  $('leadMem').textContent = state.lead ? `${state.lead.d} m` : '15–25 m';
  $('leadMemS').textContent = state.lead ? u('secondsEarly', state.lead.s) : u('secondsEarly', '12–20');
}

// ---------- memory ----------
function renderMemory() {
  const d = mem.dump();
  if (map && !$('tab-places').hidden) drawMapLayers();
  $('nHaz').textContent = d.hazards.length; $('nPlaces').textContent = d.places.length; $('nNodes').textContent = d.nodes.length;
  const list = $('hazList');
  if (!d.hazards.length) { list.innerHTML = `<p class="empty">${u('memEmpty')}</p>`; return; }
  const rows = d.hazards.map((h) => ({ h, r: mem.hazardRisk(h) })).sort((a, b) => b.r - a.r);
  list.innerHTML = rows.map(({ h, r }) => {
    const cat = h.category || 'static';
    return `<div class="row">
      <div class="dot" style="background:var(--cat-${cat})"><svg width="20" height="20"><use href="#i-alert"/></svg></div>
      <div style="min-width:0"><div class="t">${esc(obj(h.cls))}<span class="tag">${u('cat')[cat]}</span>${h.example ? `<span class="tag">${u('example')}</span>` : ''}</div>
        <div class="m">${u('seen', h.count)} · ${ago(h.lastSeen)}${state.pos ? ' · ' + u('away', Math.round(mem.distM(state.pos, h))) : ''}</div>
        <div class="riskbar" title="${u('risk')}"><span style="width:${Math.min(100, r * 100).toFixed(0)}%;background:var(--cat-${cat})"></span></div></div>
      <button class="small-btn" data-hz="${h.id}">${u('itsGone')}</button></div>`;
  }).join('');
  list.querySelectorAll('[data-hz]').forEach((b) => b.onclick = () => { mem.removeHazard(b.dataset.hz); renderMemory(); });
}

// ---------- settings ----------
function renderSettings() {
  $('rate').value = store.get('rate', 1); $('rateV').textContent = `${(+$('rate').value).toFixed(1)}×`;
  $('vib').checked = state.vib;
  $('simwalk').checked = state.simWalk;
  $('phonevoice').checked = state.phoneVoice;
  $('demo').checked = state.mode === 'demo';
  $('rowsCount').textContent = u('rows', state.training.length);
  $('modelInfo').textContent = `${u('model')}: ${state.fusionOn ? u('modelOn') : u('modelOff')}`;
}
$('rate').oninput = () => { const r = +$('rate').value; setRate(r); store.set('rate', r); $('rateV').textContent = `${r.toFixed(1)}×`; };
$('vib').onchange = () => { state.vib = $('vib').checked; store.set('vib', state.vib); };
$('phonevoice').onchange = () => {
  state.phoneVoice = $('phonevoice').checked; store.set('phonevoice', state.phoneVoice);
  if (state.phoneVoice) speak(t('connected'));   // also unlocks speech in the browser
};
$('simwalk').onchange = () => { state.simWalk = $('simwalk').checked; store.set('simwalk', state.simWalk); applySimWalk(); };
function applySimWalk() {
  if (state.mode === 'demo') return;
  if (state.simWalk) { demo.seed(); setDemoPos(state.walkOffset); }
  else { mem.useStore('auralis-memory-v1'); }
  resetMapLayers(); renderPlaces(); renderMemory();
}
$('demo').onchange = () => {
  if ($('demo').checked) { ws?.close(); startDemo(); }
  else { stopDemo(); state.mode = 'connecting'; mem.useStore('auralis-memory-v1'); state.pos = null; renderConn(); applyTexts(); connectPi(); }
};

function label(lv) {
  if (!state.features) return;
  state.training.push([...state.features, lv]);
  $('rowsCount').textContent = u('rows', state.training.length);
  vibrate(40);
}
function download(name, text) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text])); a.download = name; a.click();
}
$('btnExport').onclick = () => download('auralis_training.csv',
  'front,drop,severity,conf,area,offset,memory,approach,label\n' + state.training.map((r) => r.map((v) => +v.toFixed(4)).join(',')).join('\n'));
$('btnExportMem').onclick = () => download('auralis_memory.json', JSON.stringify(mem.dump(), null, 1));
$('btnReset').onclick = () => { $('confirmText').textContent = u('resetConfirm'); $('confirmSheet').hidden = false; $('btnCancel').focus(); };
$('btnCancel').onclick = () => { $('confirmSheet').hidden = true; };
$('btnConfirm').onclick = () => { mem.clearAll(); $('confirmSheet').hidden = true; renderPlaces(); renderMemory(); };

// ---------- walk screen actions ----------
function toggleWalking() { setWalking(!state.walking, true); }
// tellPi: false when the change came from the cane itself (hand gesture)
function setWalking(on, tellPi) {
  if (on === state.walking) return;
  state.walking = on;
  $('btnStart').setAttribute('aria-pressed', on);
  $('btnStart').querySelector('span').textContent = on ? u('stop') : u('start');
  if (tellPi && state.mode === 'pi') { try { ws.send(JSON.stringify({ active: on })); } catch {} }
  clearInterval(state.walkTimer); state.walkTimer = null;
  if (on) {
    state.walkStart = Date.now();
    if (state.mode !== 'pi') speak('AURALIS');
    if ((state.simWalk || state.autoRoute) && state.mode !== 'demo') {
      state.walkTimer = setInterval(() => setDemoPos(state.walkOffset + (Date.now() - state.walkStart) / 1000), 500);
    }
  } else {
    state.walkOffset += (Date.now() - state.walkStart) / 1000;
    if (state.mode !== 'pi') speechSynthesis?.cancel();
  }
  renderStatus();
}
$('btnStart').onclick = toggleWalking;

// Location: phone GPS when available; otherwise (Pi browser, indoors, http page) the classroom route,
// so saving places and remembering hazards always work.
function startLocation() {
  if (geoWatch === null) startGeo();
  setTimeout(() => { if (!state.gpsOk && !state.pos) { useRouteLocation(); toast(u('noGps')); } }, 5000);
}
function useRouteLocation() {
  if (state.gpsOk) return;           // real GPS always wins
  state.autoRoute = true;
  setDemoPos(state.walkOffset);
  if (state.walking && !state.walkTimer && state.mode !== 'demo') {
    state.walkStart = Date.now();
    state.walkTimer = setInterval(() => setDemoPos(state.walkOffset + (Date.now() - state.walkStart) / 1000), 500);
  }
}
$('btnWhere').onclick = () => {
  const n = state.pos && mem.nearestPlace(state.pos);
  if (!n) return;
  const text = t('whereAmI', n.p.name, Math.round(n.d));
  say(text); toast(text);
};
$('btnSave').onclick = () => {
  showTab('places'); $('placeInput').focus();
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  try {
    const rec = new SR(); rec.lang = LANGS[getLang()].code;
    rec.onresult = (e) => { $('placeInput').value = e.results[0][0].transcript; };
    rec.start();
  } catch {}
};
$('btnGone').onclick = () => {
  if (!state.pos) return;
  mem.clearHazardsNear(state.pos); renderMemory(); vibrate(60); toast(u('hazardGone'));
};
$('btnStopGuide').onclick = stopGuide;

// ---------- tabs, sheets, helpers ----------
function showTab(name) {
  document.querySelectorAll('[role=tab]').forEach((b) => b.setAttribute('aria-selected', b.dataset.tab === name));
  for (const s of ['walk', 'places', 'memory', 'settings']) $('tab-' + s).hidden = s !== name;
  if (name === 'walk') requestAnimationFrame(drawRadar);
  if (name === 'places') { renderPlaces(); initMap(); }
  if (name === 'memory') { renderMemory(); renderLead(); }
  if (name === 'settings') renderSettings();
  scrollTo(0, 0);
}
document.querySelectorAll('[role=tab]').forEach((b) => b.onclick = () => showTab(b.dataset.tab));
$('langBtn').onclick = () => showTab('settings');

function vibrate(p) { if (state.vib) navigator.vibrate?.(p); }
let toastTimer;
function toast(text) {
  const el = $('toast'); el.textContent = text; el.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 2600);
}
function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
addEventListener('resize', drawRadar);
matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', drawRadar);

// ---------- start ----------
setLang(store.get('lang', 'en'));
setRate(store.get('rate', 1));
applyTexts();
if (!store.get('lang', null)) {
  renderLangs($('langsFirst'), () => { $('langSheet').hidden = true; });
  $('langSheet').hidden = false;
}
loadFusion().then((ok) => { state.fusionOn = ok; renderSettings(); });
if (location.protocol.startsWith('http') && location.port) connectPi(); else startDemo();
// (fails harmlessly with the Pi's self-signed certificate; works when hosted with a real one)
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
