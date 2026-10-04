// Demo mode: simulated cane data in exactly the format pi/server.py sends, plus a simulated
// GPS walk, so the app can be tried (and presented) without the hardware.
import * as mem from './memory.js';

const BASE = { lat: 13.0108, lon: 80.2354 };
// A loop around a campus block (metres east, north of BASE)
const LOOP = [[0, 0], [0, 120], [90, 120], [90, 0], [0, 0]];
const SPEED = 1.2; // m/s walking

function toLatLon([e, n]) {
  return { lat: BASE.lat + n / 111320, lon: BASE.lon + e / (111320 * Math.cos(BASE.lat * Math.PI / 180)) };
}

const ob = (cls, category, severity, dist, lateral, approach = 0, conf = 0.86) => ({
  cls, category, severity, conf, dist: +dist.toFixed(2), lateral,
  side: Math.abs(lateral) < 0.25 ? 'ahead' : lateral < 0 ? 'left' : 'right',
  approach, inCorridor: Math.abs(lateral) <= 0.5 && dist <= 4, area: Math.min(1, 0.6 / (dist * dist)),
  offset: Math.min(1, Math.abs(lateral) / 2), remember: category !== 'moving', box: null,
});

// A 32-second script that cycles through the obstacle categories
export function frame(t) {
  const s = t % 32;
  const obstacles = [];
  const ultra = { cm: 70 + Math.sin(t * 3), baseline: 70, drop: false, raised: false };
  if (s < 9) {
    obstacles.push(ob('pole', 'static', 0.6, 4.2 - s * 0.38, 0.05));
    obstacles.push(ob('person', 'moving', 0.3, 2.8, 1.1 - s * 0.05, 0.1, 0.92));
  } else if (s >= 12 && s < 17) {
    obstacles.push(ob('auto_rickshaw', 'moving', 0.9, 4 - (s - 12) * 0.6, -0.9 + (s - 12) * 0.12, 1.5));
  } else if (s >= 19 && s < 24) {
    obstacles.push(ob('pothole', 'drop', 1.0, 3 - (s - 19) * 0.5, -0.1, 0, 0.81));
    if (s > 22) {
      ultra.cm = 98; ultra.drop = true;
      obstacles.push(ob('drop', 'drop', 1.0, 0.5, 0, 0, 0.95));
    }
  } else if (s >= 26 && s < 31) {
    obstacles.push(ob('branch', 'head', 0.8, 3.2 - (s - 26) * 0.4, 0.15, 0, 0.77));
  }
  obstacles.sort((a, b) => (!a.inCorridor - !b.inCorridor) || a.dist - b.dist);
  return { obstacles, ultra, fps: 5.0, t: Date.now() / 1000 };
}

// Position along the loop after walking for t seconds
export function position(t) {
  let d = (t * SPEED) % 420;
  for (let i = 1; i < LOOP.length; i++) {
    const [a, b] = [LOOP[i - 1], LOOP[i]];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (d <= len) {
      const f = d / len;
      const p = toLatLon([a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]);
      return { ...p, accuracy: 6, heading: (Math.atan2(b[0] - a[0], b[1] - a[1]) * 180 / Math.PI + 360) % 360 };
    }
    d -= len;
  }
  return { ...toLatLon(LOOP[0]), accuracy: 6, heading: 0 };
}

// Example memory: a walked loop, three places and a few hazards of different ages
export function seed() {
  mem.useStore('auralis-demo-memory-v1');
  if (mem.dump().places.length) return;
  for (let t = 0; t <= 420 / SPEED; t += 3) mem.addBreadcrumb(position(t));
  // a short-cut path across the middle of the block, with hazards on it
  for (let e = 0; e <= 90; e += 5) mem.addBreadcrumb({ ...toLatLon([e, 60]), accuracy: 6 });
  const day = 86400000;
  const hz = [
    ['open_drain', 'drop', 1.0, [45, 60], 4, 1 * day],
    ['pothole', 'drop', 1.0, [60, 60], 3, 2 * day],
    ['pole', 'static', 0.6, [0, 40], 6, 0.2 * day],
    ['speed_breaker', 'raised', 0.5, [90, 80], 2, 9 * day],
    ['branch', 'head', 0.8, [30, 120], 1, 0.05 * day],
  ];
  for (const [cls, category, sev, en, count, age] of hz) {
    const h = mem.recordHazard(toLatLon(en), cls, 0.85, 1.5, sev, category);
    h.count = count; h.lastSeen = Date.now() - age; h.firstSeen = h.lastSeen - count * day; h.example = true;
  }
  mem.savePlace(toLatLon([0, 0]), 'Hostel gate');
  mem.savePlace(toLatLon([90, 60]), 'Library');
  mem.savePlace(toLatLon([90, 120]), 'Canteen');
  for (const p of mem.places()) p.example = true;
  mem.importDump(mem.dump()); // persist flags
}
