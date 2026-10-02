// Runs the sensor-fusion MLP trained by ml/train_fusion.py, on the phone.
// Falls back to simple distance rules if the weights file is missing.

let layers = null;
export async function loadFusion() {
  try { layers = (await (await fetch('fusion_weights.json')).json()).layers; } catch { layers = null; }
  return !!layers;
}

// features: [front, drop, severity, conf, area, offset, memory, approach] (see train_fusion.py)
export function fuse(x) {
  if (!layers) {
    const frontM = x[0] * 4;
    if (x[1] > 0.25 || frontM < 0.6) return { level: 3, probs: null };
    if (frontM < 1.2) return { level: 2, probs: null };
    if (frontM < 2.5 || x[6] > 0.3) return { level: 1, probs: null };
    return { level: 0, probs: null };
  }
  let a = x;
  layers.forEach(({ W, b }, i) => {
    const out = b.slice();
    for (let j = 0; j < W.length; j++) for (let k = 0; k < out.length; k++) out[k] += a[j] * W[j][k];
    a = i < layers.length - 1 ? out.map((v) => Math.max(v, 0)) : out;
  });
  const m = Math.max(...a), e = a.map((v) => Math.exp(v - m)), s = e.reduce((p, q) => p + q);
  const probs = e.map((v) => v / s);
  return { level: probs.indexOf(Math.max(...probs)), probs };
}
