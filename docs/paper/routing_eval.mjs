// E5: shortest vs safest route for several lambda values, using the app's own code
// (app/memory.js, app/router.js, app/demo.js example campus). Run: node docs/paper/routing_eval.mjs > docs/paper/routing.json
const mem = new Map();
globalThis.localStorage = { getItem: (k) => mem.get(k) ?? null, setItem: (k, v) => mem.set(k, String(v)), removeItem: (k) => mem.delete(k) };
const M = await import('../../app/memory.js');
const { route } = await import('../../app/router.js');
const demo = await import('../../app/demo.js');
demo.setBase(13.0, 80.0);   // any origin; results are reported in metres
demo.seed();
const g = M.graph(), base = { lat: 13.0, lon: 80.0 };
const xy = (p) => [M.distM(base, { lat: base.lat, lon: p.lon }) * Math.sign(p.lon - base.lon), M.distM(base, { lat: p.lat, lon: base.lon }) * Math.sign(p.lat - base.lat)];
const places = Object.fromEntries(M.places().map((p) => [p.name, p]));
// From the west side of the block (0 m E, 60 m N) to the Library: the straight short-cut crosses the drain and the pothole
const start = M.nearestNode({ lat: base.lat + 60 / 111320, lon: base.lon }).id, goal = places['Library'].node;
const out = { lambdas: [], nodes: g.nodes.map(xy), edges: g.edges.map((e) => [e.a, e.b]),
  hazards: M.hazards().map((h) => ({ xy: xy(h), cls: h.cls, risk: M.hazardRisk(h) })), start, goal, paths: {} };
for (const lam of [0, 0.5, 1, 2, 4, 8, 16]) {
  const r = route(g, start, goal, lam);
  out.lambdas.push({ lambda: lam, length: r.length, risk: r.risk });
  out.paths[lam] = r.path;
}
console.log(JSON.stringify(out));
