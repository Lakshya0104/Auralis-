"""Train the AURALIS sensor-fusion neural network (numpy only, no GPU needed).

The network fuses ultrasonic distances, the camera detection and the cane's
hazard memory into one alert level:
    0 = safe, 1 = caution, 2 = warning, 3 = urgent

Usage:
    python ml/train_fusion.py                       # synthetic bootstrap data
    python ml/train_fusion.py --real logs.csv       # + real labelled rows from the app

The app's "Export log" button writes CSV rows: the 8 features + the label you
gave while walking (tap Safe/Caution/Warning/Urgent). Real rows are weighted 5x.
Writes app/fusion_weights.json, which the phone app loads at start-up.
"""
import argparse
import csv
import json
import pathlib

import numpy as np

FEATURES = ["front", "drop", "severity", "conf", "area", "offset", "memory", "approach"]
CLASSES = ["safe", "caution", "warning", "urgent"]
rng = np.random.default_rng(42)


def expert_label(x):
    """Hand-written rules = the teacher for the synthetic bootstrap set."""
    front_m = x[0] * 4
    drop, sev, conf, area, off, mem, app = x[1:]
    in_path = off < 0.35
    threat = sev * conf * (1.0 if in_path else 0.3) + 0.6 * area * in_path
    if drop > 0.25 or front_m < 0.6 or (threat > 0.5 and front_m < 1.2) or (app > 0.6 and front_m < 1.5):
        return 3
    if front_m < 1.2 or threat > 0.45 or (mem > 0.6 and front_m < 3):
        return 2
    if front_m < 2.5 or threat > 0.2 or mem > 0.3 or app > 0.3:
        return 1
    return 0


def synthetic(n):
    X = np.zeros((n, 8))
    X[:, 0] = rng.beta(2, 1.3, n)                                   # front distance /4 m
    X[:, 1] = np.where(rng.random(n) < 0.08, rng.uniform(0.2, 1, n), rng.normal(0, 0.06, n))
    has_det = rng.random(n) < 0.6
    X[:, 2] = has_det * rng.choice([0.2, 0.4, 0.5, 0.6, 0.85, 0.9], n)
    X[:, 3] = has_det * rng.uniform(0.4, 1, n)
    # a near obstacle tends to look bigger to the camera
    X[:, 4] = has_det * np.clip((1 - X[:, 0]) ** 2 * rng.uniform(0.3, 1.2, n), 0, 1)
    X[:, 5] = np.where(has_det, rng.uniform(0, 1, n), 1)
    X[:, 6] = np.where(rng.random(n) < 0.2, rng.uniform(0, 1, n), 0)
    X[:, 7] = np.clip(rng.exponential(0.12, n), 0, 1)
    y = np.array([expert_label(r) for r in X])
    flip = rng.random(n) < 0.03                                     # label noise
    y[flip] = np.clip(y[flip] + rng.choice([-1, 1], flip.sum()), 0, 3)
    return X, y


def load_real(path):
    X, y = [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            if row.get("label", "") == "":
                continue
            X.append([float(row[k]) for k in FEATURES])
            y.append(int(row["label"]))
    return np.array(X), np.array(y)


class MLP:
    def __init__(self, sizes):
        self.W = [rng.normal(0, np.sqrt(2 / a), (a, b)) for a, b in zip(sizes, sizes[1:])]
        self.b = [np.zeros(b) for b in sizes[1:]]
        self.m = [np.zeros_like(p) for p in self.W + self.b]
        self.v = [np.zeros_like(p) for p in self.W + self.b]
        self.t = 0

    def forward(self, X):
        acts = [X]
        for i, (W, b) in enumerate(zip(self.W, self.b)):
            z = acts[-1] @ W + b
            acts.append(np.maximum(z, 0) if i < len(self.W) - 1 else z)
        return acts

    def predict_proba(self, X):
        z = self.forward(X)[-1]
        e = np.exp(z - z.max(1, keepdims=True))
        return e / e.sum(1, keepdims=True)

    def step(self, X, y, w, lr=3e-3, l2=1e-4):
        acts = self.forward(X)
        p = self.predict_proba(X)
        d = p.copy()
        d[np.arange(len(y)), y] -= 1
        d *= (w / w.sum())[:, None]
        gW, gb = [], []
        for i in reversed(range(len(self.W))):
            gW.insert(0, acts[i].T @ d + l2 * self.W[i])
            gb.insert(0, d.sum(0))
            if i:
                d = (d @ self.W[i].T) * (acts[i] > 0)
        self.t += 1
        for k, (p_, g) in enumerate(zip(self.W + self.b, gW + gb)):
            self.m[k] = 0.9 * self.m[k] + 0.1 * g
            self.v[k] = 0.999 * self.v[k] + 0.001 * g * g
            mh = self.m[k] / (1 - 0.9 ** self.t)
            vh = self.v[k] / (1 - 0.999 ** self.t)
            p_ -= lr * mh / (np.sqrt(vh) + 1e-8)


def report(name, y, pred):
    acc = (y == pred).mean()
    cm = np.zeros((4, 4), int)
    for a, b in zip(y, pred):
        cm[a, b] += 1
    # urgent recall is the safety-critical number
    urgent_recall = cm[3, 3] / max(cm[3].sum(), 1)
    print(f"{name}: accuracy={acc:.3f}  urgent-recall={urgent_recall:.3f}")
    print("  confusion (rows=true safe/caution/warning/urgent):")
    for r in cm:
        print("   ", r)
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", help="CSV exported from the app")
    ap.add_argument("--epochs", type=int, default=60)
    args = ap.parse_args()

    X, y = synthetic(20000)
    w = np.ones(len(y))
    if args.real:
        Xr, yr = load_real(args.real)
        print(f"loaded {len(yr)} real rows")
        X, y, w = np.vstack([X, Xr]), np.concatenate([y, yr]), np.concatenate([w, np.full(len(yr), 5.0)])

    idx = rng.permutation(len(y))
    split = int(0.8 * len(y))
    tr, te = idx[:split], idx[split:]

    net = MLP([8, 16, 16, 4])
    for epoch in range(args.epochs):
        order = rng.permutation(tr)
        for i in range(0, len(order), 64):
            bi = order[i:i + 64]
            net.step(X[bi], y[bi], w[bi])
        if epoch % 10 == 9:
            acc = (net.predict_proba(X[te]).argmax(1) == y[te]).mean()
            print(f"epoch {epoch + 1}: test accuracy {acc:.3f}")

    report("MLP test", y[te], net.predict_proba(X[te]).argmax(1))

    out = pathlib.Path(__file__).resolve().parent.parent / "app" / "fusion_weights.json"
    out.write_text(json.dumps({
        "features": FEATURES, "classes": CLASSES,
        "layers": [{"W": W.round(5).tolist(), "b": b.round(5).tolist()} for W, b in zip(net.W, net.b)],
    }))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
