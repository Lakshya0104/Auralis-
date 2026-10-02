// Risk-aware A* over the self-built walk graph.
//   edge cost = length + LAMBDA * length * segmentRisk
// segmentRisk = sum of decayed hazard risks within RADIUS of the edge.
import { distM, hazardRisk, hazards } from './memory.js';

export const LAMBDA = 4;
const RADIUS = 10;

function pointSegDist(p, a, b) {
  // flat-earth approximation is fine at campus scale
  const k = 111320, kx = k * Math.cos(a.lat * Math.PI / 180);
  const ax = 0, ay = 0, bx = (b.lon - a.lon) * kx, by = (b.lat - a.lat) * k;
  const px = (p.lon - a.lon) * kx, py = (p.lat - a.lat) * k;
  const l2 = bx * bx + by * by || 1;
  const t = Math.max(0, Math.min(1, ((px - ax) * bx + (py - ay) * by) / l2));
  return Math.hypot(px - t * bx, py - t * by);
}

export function edgeRisk(a, b, hz = hazards()) {
  let r = 0;
  for (const h of hz) if (pointSegDist(h, a, b) < RADIUS) r += hazardRisk(h);
  return Math.min(r, 1.5);
}

export function route({ nodes, edges }, startId, goalId, lambda = LAMBDA) {
  const adj = new Map();
  const hz = hazards();
  for (const e of edges) {
    const a = nodes[e.a], b = nodes[e.b];
    const risk = edgeRisk(a, b, hz);
    const cost = e.len * (1 + lambda * risk);
    for (const [u, v] of [[e.a, e.b], [e.b, e.a]]) {
      if (!adj.has(u)) adj.set(u, []);
      adj.get(u).push({ v, cost, len: e.len, risk });
    }
  }
  const goal = nodes[goalId];
  const g = new Map([[startId, 0]]), prev = new Map();
  const open = new Set([startId]);
  const f = (id) => g.get(id) + distM(nodes[id], goal);
  while (open.size) {
    let cur = null;
    for (const id of open) if (cur === null || f(id) < f(cur)) cur = id;
    if (cur === goalId) break;
    open.delete(cur);
    for (const { v, cost } of adj.get(cur) || []) {
      const ng = g.get(cur) + cost;
      if (ng < (g.get(v) ?? Infinity)) { g.set(v, ng); prev.set(v, cur); open.add(v); }
    }
  }
  if (!g.has(goalId)) return null;
  const path = [goalId];
  while (path[0] !== startId) path.unshift(prev.get(path[0]));
  let length = 0, risk = 0;
  for (let i = 1; i < path.length; i++) {
    const e = adj.get(path[i - 1]).find((x) => x.v === path[i]);
    length += e.len; risk += e.risk * e.len;
  }
  return { path, length, risk: length ? risk / length : 0 };
}
