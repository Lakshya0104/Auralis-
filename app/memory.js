// Spatio-temporal memory: hazards, saved places, and a walk graph that the
// cane builds by itself from the paths the user actually walks.
// Everything is stored on the phone (localStorage) — works offline.

let KEY = 'auralis-memory-v1';
const HAZARD_MERGE_M = 8;     // detections closer than this are one hazard
const NODE_MERGE_M = 6;       // breadcrumbs closer than this are one graph node
const BREADCRUMB_M = 5;       // record a breadcrumb every N metres walked
export const HALF_LIFE_DAYS = 7;


let db = load();
// Demo mode keeps its own memory so example data never mixes with real hazards
export function useStore(name) { KEY = name; db = load(); lastCrumb = null; }
function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || fresh(); } catch { return fresh(); }
}
function fresh() { return { hazards: [], places: [], nodes: [], edges: [], log: [] }; }
// persist: optional extra copy (the Pi stores the cane's memory in pi/memory.json)
let persist = null;
export const setPersist = (fn) => { persist = fn; };
function save() { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch {} persist?.(db); }
export const dump = () => db;
export function importDump(d) { db = { ...fresh(), ...d }; save(); }
export function clearAll() { db = fresh(); save(); }

export function distM(a, b) {
  const R = 6371000, r = Math.PI / 180;
  const dLat = (b.lat - a.lat) * r, dLon = (b.lon - a.lon) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
export function bearing(a, b) {
  const r = Math.PI / 180;
  const y = Math.sin((b.lon - a.lon) * r) * Math.cos(b.lat * r);
  const x = Math.cos(a.lat * r) * Math.sin(b.lat * r) - Math.sin(a.lat * r) * Math.cos(b.lat * r) * Math.cos((b.lon - a.lon) * r);
  return (Math.atan2(y, x) / r + 360) % 360;
}

// ---- Hazards: repeated evidence + temporal decay -------------------------
export function hazardRisk(h, now = Date.now()) {
  const ageDays = (now - h.lastSeen) / 86400000;
  const recency = 0.5 ** (ageDays / HALF_LIFE_DAYS);
  const evidence = 1 - Math.exp(-h.count / 2);          // 1 sighting ~0.39, 3 ~0.78, 5 ~0.92
  return h.severity * evidence * recency * h.confidence;
}

// Point `distM` metres from `pos` in direction `deg` (the hazard is ahead of the user, not under them)
export function offset(pos, deg, dist) {
  const r = Math.PI / 180;
  return { lat: pos.lat + (dist * Math.cos(deg * r)) / 111320,
           lon: pos.lon + (dist * Math.sin(deg * r)) / (111320 * Math.cos(pos.lat * r)) };
}

// severity comes from the obstacle taxonomy on the Pi (pi/config.py)
export function recordHazard(pos, cls, confidence, distanceM, severity = 0.5, category = '') {
  const now = Date.now();
  db.log.push({ t: now, lat: pos.lat, lon: pos.lon, cls, confidence, distanceM });
  if (db.log.length > 5000) db.log.shift();
  let h = db.hazards.find((x) => x.cls === cls && distM(x, pos) < HAZARD_MERGE_M);
  if (h) {
    // Count a new sighting at most once per minute so standing still does not inflate it
    if (now - h.lastSeen > 60000) h.count += 1;
    h.lat = (h.lat * 3 + pos.lat) / 4;
    h.lon = (h.lon * 3 + pos.lon) / 4;
    h.confidence = Math.max(h.confidence * 0.8 + confidence * 0.2, confidence * 0.5);
    h.lastSeen = now;
  } else {
    h = { id: crypto.randomUUID(), lat: pos.lat, lon: pos.lon, cls, category, severity,
          confidence, count: 1, firstSeen: now, lastSeen: now };
    db.hazards.push(h);
  }
  save();
  return h;
}

export function removeHazard(id) { db.hazards = db.hazards.filter((h) => h.id !== id); save(); }

// User says "it's gone" near a hazard -> strong negative evidence
export function clearHazardsNear(pos, radius = 10) {
  db.hazards = db.hazards.filter((h) => distM(h, pos) > radius);
  save();
}

export function hazardsAhead(pos, headingDeg, lookM = 25) {
  return db.hazards
    .map((h) => ({ h, d: distM(pos, h), b: bearing(pos, h), risk: hazardRisk(h) }))
    .filter((x) => x.d < lookM && x.risk > 0.15 &&
      (headingDeg == null || angleDiff(x.b, headingDeg) < 45))
    .sort((a, b) => a.d - b.d);
}
export const angleDiff = (a, b) => Math.abs(((a - b + 540) % 360) - 180);

// ---- Places ----------------------------------------------------------------
export function savePlace(pos, name) {
  db.places.push({ id: crypto.randomUUID(), name, lat: pos.lat, lon: pos.lon, t: Date.now(), node: nodeFor(pos).id });
  save();
}
export const places = () => db.places;
export function nearestPlace(pos) {
  return db.places.map((p) => ({ p, d: distM(pos, p) })).sort((a, b) => a.d - b.d)[0];
}

// ---- Self-built walk graph -------------------------------------------------
let lastCrumb = null;
function nodeFor(pos) {
  let best = null, bestD = Infinity;
  for (const n of db.nodes) { const d = distM(n, pos); if (d < bestD) { best = n; bestD = d; } }
  if (best && bestD < NODE_MERGE_M) return best;
  const n = { id: db.nodes.length, lat: pos.lat, lon: pos.lon };
  db.nodes.push(n);
  return n;
}
export function addBreadcrumb(pos) {
  if (pos.accuracy && pos.accuracy > 25) return;   // ignore poor GPS fixes
  if (lastCrumb && distM(lastCrumb, pos) < BREADCRUMB_M) return;
  const n = nodeFor(pos);
  // a jump > 30 m is a GPS glitch or app restart, not a walkable segment
  if (lastCrumb && lastCrumb.id !== n.id && distM(lastCrumb, n) < 30) {
    const exists = db.edges.some((e) => (e.a === lastCrumb.id && e.b === n.id) || (e.a === n.id && e.b === lastCrumb.id));
    if (!exists) db.edges.push({ a: lastCrumb.id, b: n.id, len: distM(lastCrumb, n) });
  }
  lastCrumb = n;
  save();
}
export const graph = () => ({ nodes: db.nodes, edges: db.edges });
export const hazards = () => db.hazards;
export { nodeFor };
export function nearestNode(pos) {
  let best = null, bestD = Infinity;
  for (const n of db.nodes) { const d = distM(n, pos); if (d < bestD) { best = n; bestD = d; } }
  return best;
}
