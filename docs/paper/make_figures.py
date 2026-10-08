"""Figures and numbers for the AURALIS IEEE draft. Every number comes from the project's own code.

    node docs/paper/routing_eval.mjs > docs/paper/routing.json
    python docs/paper/make_figures.py            # writes docs/paper/figures/*.pdf and results.json
"""
import json
import math
import pathlib
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "ml"))
sys.path.insert(0, str(ROOT / "pi"))
import train_fusion as tf          # synthetic generator + expert teacher
import config as cfg                # camera geometry, thresholds

# Reference palette (dataviz skill): categorical slots 1-3, one-hue blue ramp, recessive ink
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "font.size": 8,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
    "legend.frameon": False, "legend.fontsize": 7, "figure.dpi": 200, "savefig.bbox": "tight",
})
W1 = 3.45   # IEEE single-column width, inches
results = {}


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=220)
    plt.close(fig)


# ---------- E2: fusion network vs rule baseline (synthetic held-out set) ----------
def mlp_predict(X, layers):
    a = X
    for i, L in enumerate(layers):
        a = a @ np.array(L["W"]) + np.array(L["b"])
        if i < len(layers) - 1:
            a = np.maximum(a, 0)
    return a.argmax(1)


def rules_predict(X):            # the app's fallback rules (app/fusion.js)
    out = []
    for x in X:
        front = x[0] * 4
        out.append(3 if x[1] > 0.25 or front < 0.6 else 2 if front < 1.2 else 1 if front < 2.5 or x[6] > 0.3 else 0)
    return np.array(out)


def metrics(y, p):
    cm = np.zeros((4, 4), int)
    for a, b in zip(y, p):
        cm[a, b] += 1
    rec = cm.diagonal() / np.maximum(cm.sum(1), 1)
    prec = cm.diagonal() / np.maximum(cm.sum(0), 1)
    f1 = 2 * prec * rec / np.maximum(prec + rec, 1e-9)
    return {"accuracy": float((y == p).mean()), "macro_f1": float(f1.mean()), "urgent_recall": float(rec[3]),
            "urgent_precision": float(prec[3]), "recall": rec.round(3).tolist(), "cm": cm.tolist()}


tf.rng = np.random.default_rng(2026)           # fresh test data, not the training draw
X, y = tf.synthetic(10000)
layers = json.loads((ROOT / "app" / "fusion_weights.json").read_text())["layers"]
t0 = time.perf_counter()
p_mlp = mlp_predict(X, layers)
mlp_us = (time.perf_counter() - t0) / len(X) * 1e6
results["fusion"] = {"n_test": len(y), "class_counts": np.bincount(y, minlength=4).tolist(),
                     "mlp": metrics(y, p_mlp), "rules": metrics(y, rules_predict(X)),
                     "params": int(sum(np.array(L["W"]).size + np.array(L["b"]).size for L in layers)),
                     "mlp_us_per_sample_numpy": mlp_us}

cm = np.array(results["fusion"]["mlp"]["cm"])
cmn = cm / cm.sum(1, keepdims=True)
fig, ax = plt.subplots(figsize=(W1 * 0.62, W1 * 0.55))
ax.grid(False)
ax.imshow(cmn, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("b", ["#f4f8fd", BLUE, "#103f78"]), vmin=0, vmax=1)
names = ["Safe", "Caution", "Warning", "Urgent"]
for i in range(4):
    for j in range(4):
        ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center", fontsize=7, color="white" if cmn[i, j] > 0.55 else INK)
ax.set_xticks(range(4), names, rotation=30)
ax.set_yticks(range(4), names)
ax.set_xlabel("Predicted level")
ax.set_ylabel("True level")
for s in ax.spines.values():
    s.set_visible(False)
save(fig, "fusion_confusion")

# ---------- E6: hazard risk decay (app/memory.js formula) ----------
days = np.linspace(0, 28, 200)
fig, ax = plt.subplots(figsize=(W1, 1.75))
for n, c in zip([1, 3, 5], [BLUE, ORANGE, AQUA]):
    r = (1 - np.exp(-n / 2)) * 0.5 ** (days / 7)
    ax.plot(days, r, color=c, label=f"seen {n}×")
ax.axhline(0.15, color=INK2, lw=0.9, ls=(0, (3, 2)))
ax.text(0.3, 0.165, "warning threshold (0.15)", fontsize=7, color=INK2)
ax.set_xlabel("Days since last sighting")
ax.set_ylabel("Hazard risk (severity = 1)")
ax.set_xlim(0, 28)
ax.set_ylim(0, 1)
ax.legend(loc="upper right", ncol=3)
save(fig, "risk_decay")
results["decay"] = {f"count{n}_days_to_threshold": float(7 * math.log2((1 - math.exp(-n / 2)) / 0.15)) for n in [1, 3, 5]}

# ---------- E1 (analytic): single-camera ground-plane distance sensitivity ----------
def ground(yb, h=cfg.CAM_HEIGHT_M, pitch=cfg.CAM_PITCH_DEG):
    a = math.radians(pitch) + math.atan((yb - cfg.FRAME_H / 2) / cfg.FOCAL_PX)
    return h / math.tan(a) if a > math.radians(2) else float("nan")


rows = np.arange(120, 480)
true = np.array([ground(r) for r in rows])
fig, ax = plt.subplots(figsize=(W1, 1.75))
for d_pitch, c, lab in [(2, BLUE, "tilt off by +2°"), (-2, ORANGE, "tilt off by −2°")]:
    est = np.array([ground(r, pitch=cfg.CAM_PITCH_DEG + d_pitch) for r in rows])
    ax.plot(true, 100 * (est - true) / true, color=c, label=lab)
est_h = np.array([ground(r, h=cfg.CAM_HEIGHT_M + 0.05) for r in rows])
ax.plot(true, 100 * (est_h - true) / true, color=AQUA, label="height off by +5 cm")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlim(0.5, 4)
ax.set_xlabel("True distance (m)")
ax.set_ylabel("Distance error (%)")
ax.set_ylim(-16, 22)
ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.18), handlelength=1.4, columnspacing=1)
save(fig, "distance_sensitivity")
results["distance"] = {f"err_pct_at_{d}m_pitch+2": float(np.interp(d, true[::-1], (100 * (np.array([ground(r, pitch=cfg.CAM_PITCH_DEG + 2) for r in rows]) - true) / true)[::-1])) for d in [1, 2, 3]}
results["distance"].update({f"err_pct_at_{d}m_pitch-2": float(np.interp(d, true[::-1], (100 * (np.array([ground(r, pitch=cfg.CAM_PITCH_DEG - 2) for r in rows]) - true) / true)[::-1])) for d in [1, 2, 3]})
results["camera"] = {"height_m": cfg.CAM_HEIGHT_M, "pitch_deg": cfg.CAM_PITCH_DEG, "hfov_deg": cfg.CAM_HFOV_DEG, "focal_px": cfg.FOCAL_PX,
                     "nearest_ground_m": ground(cfg.FRAME_H - 1)}

# ---------- E5: risk-aware routing (routing.json from routing_eval.mjs) ----------
R = json.loads((HERE / "routing.json").read_text())
results["routing"] = R["lambdas"]
nodes = np.array(R["nodes"])
fig, (ax, bx) = plt.subplots(1, 2, figsize=(W1 * 2.05, 2.1), gridspec_kw={"width_ratios": [1.15, 1]})
ax.grid(False)
for a, b in R["edges"]:
    ax.plot(*nodes[[a, b]].T, color=GRID, lw=3, solid_capstyle="round", zorder=1)
for lam, c, lab, ls in [("0", ORANGE, "shortest (λ = 0)", "-"), ("4", BLUE, "safest (λ = 4)", "-")]:
    pts = nodes[R["paths"][lam]]
    ax.plot(*pts.T, color=c, lw=2, label=lab, ls=ls, zorder=3)
for hz in R["hazards"]:
    ax.scatter(*hz["xy"], s=30 + 160 * hz["risk"], facecolor="none", edgecolor="#e34948", lw=1.4, zorder=4)
    off = {"open_drain": (-30, 9), "pothole": (2, 9), "pole": (7, -3), "branch": (-8, -12), "speed_breaker": (-22, 9)}.get(hz["cls"], (4, 4))
    ax.annotate(hz["cls"].replace("_", " "), hz["xy"], xytext=off, textcoords="offset points", fontsize=6.5, color=INK2)
ax.scatter(*nodes[R["start"]], s=26, color=INK, zorder=5)
ax.annotate("start", nodes[R["start"]], xytext=(-26, -3), textcoords="offset points", fontsize=7)
ax.set_xlim(-25, 115)
ax.scatter(*nodes[R["goal"]], s=26, color=INK, marker="s", zorder=5)
ax.annotate("goal", nodes[R["goal"]], xytext=(5, -9), textcoords="offset points", fontsize=7)
ax.set_aspect("equal")
ax.set_xlabel("East (m)")
ax.set_ylabel("North (m)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.2), ncol=2)
lams = [d["lambda"] for d in R["lambdas"]]
bx.plot(range(len(lams)), [d["length"] for d in R["lambdas"]], color=BLUE, marker="o", ms=3.5, label="length (m)")
bx.set_xticks(range(len(lams)), [str(l) for l in lams])
bx.set_xlabel("Risk weight λ")
bx.set_ylabel("Route length (m)")
bx.set_ylim(0, 230)
for i, d in enumerate(R["lambdas"]):
    if d["lambda"] in (0, 4):
        bx.annotate(f"risk {d['risk']:.2f}", (i, d["length"]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=6.5, color=INK2)
save(fig, "routing")

# ---------- Detector latency on this machine (ONNX Runtime CPU) ----------
try:
    import onnxruntime as ort
    lat = {}
    for name in ["yolov8n.onnx", "yolov8n_480.onnx"]:
        s = ort.InferenceSession(str(ROOT / "pi" / "models" / name), providers=["CPUExecutionProvider"])
        i = s.get_inputs()[0]
        size = i.shape[2]
        blob = np.random.rand(1, 3, size, size).astype(np.float32)
        for _ in range(3):
            s.run(None, {i.name: blob})
        t0 = time.perf_counter()
        for _ in range(20):
            s.run(None, {i.name: blob})
        lat[f"{size}px_ms"] = (time.perf_counter() - t0) / 20 * 1000
    import platform
    results["detector_latency_dev_machine"] = {**lat, "cpu": platform.processor() or platform.machine()}
except Exception as e:
    results["detector_latency_dev_machine"] = {"error": str(e)}

(HERE / "results.json").write_text(json.dumps(results, indent=1))
print(json.dumps({k: v for k, v in results.items() if k != "fusion"}, indent=1))
f = results["fusion"]
print("fusion params", f["params"], "counts", f["class_counts"])
for k in ["mlp", "rules"]:
    print(k, {m: round(f[k][m], 3) for m in ["accuracy", "macro_f1", "urgent_recall", "urgent_precision"]}, f[k]["recall"])
