"""Merge several YOLO-format datasets (Roboflow exports, your own labelled photos) into
datasets/auralis/ with AURALIS class ids (ml/data.yaml).

Different datasets name the same thing differently ("Pothole", "potholes", "manhole") - SYNONYMS
maps them. Classes that map to nothing are dropped.

    python ml/merge_datasets.py path/to/pothole-dataset path/to/stairs-dataset path/to/our-photos
"""
import pathlib
import shutil
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAMES = yaml.safe_load((ROOT / "ml" / "data.yaml").read_text())["names"]
OUT = ROOT / "datasets" / "auralis"

SYNONYMS = {
    "pothole": ["pothole", "potholes", "pot hole", "pit", "hole"],
    "open_drain": ["open_drain", "drain", "open drain", "manhole", "open manhole", "gutter", "sewer"],
    "stairs_down": ["stairs_down", "stairs down", "downstairs", "descending stairs", "down stairs"],
    "stairs_up": ["stairs_up", "stairs up", "upstairs", "ascending stairs", "stairs", "staircase", "steps"],
    "curb": ["curb", "kerb", "curb edge", "footpath edge", "sidewalk edge"],
    "speed_breaker": ["speed_breaker", "speed breaker", "speed bump", "speedbump", "hump"],
    "pole": ["pole", "poles", "lamp post", "street light", "electric pole", "post", "bollard"],
    "tree": ["tree", "trees", "tree trunk"],
    "wall": ["wall"],
    "barrier": ["barrier", "barricade", "traffic cone", "cone", "fence", "gate"],
    "dustbin": ["dustbin", "trash can", "garbage bin", "bin", "trash bin", "waste bin"],
    "branch": ["branch", "low branch", "tree branch"],
    "signboard": ["signboard", "sign board", "sign", "board", "hoarding"],
    "construction": ["construction", "construction site", "road work", "roadwork"],
    "auto_rickshaw": ["auto_rickshaw", "auto rickshaw", "autorickshaw", "rickshaw", "auto", "tuk tuk", "tuktuk"],
    "person": ["person", "people", "pedestrian", "human"],
    "bicycle": ["bicycle", "bike", "cycle"],
    "motorcycle": ["motorcycle", "motorbike", "scooter", "two wheeler", "two-wheeler"],
    "car": ["car", "cars", "vehicle"],
    "bus": ["bus"], "truck": ["truck", "lorry"], "dog": ["dog"], "cow": ["cow", "cattle"],
    "bench": ["bench"], "chair": ["chair"],
}
LOOKUP = {s.lower(): NAMES.index(k) for k, syns in SYNONYMS.items() for s in syns}


def merge(sources, valid_frac=0.15):
    for split in ("train", "valid"):
        for sub in ("images", "labels"):
            (OUT / split / sub).mkdir(parents=True, exist_ok=True)
    counts = [0] * len(NAMES)
    every = max(2, round(1 / valid_frac))  # every Nth image goes to validation (never empty)
    n_img = 0
    for si, src in enumerate(map(pathlib.Path, sources)):
        names = yaml.safe_load((src / "data.yaml").read_text())["names"]
        if isinstance(names, dict):
            names = [names[i] for i in sorted(names)]
        remap = {i: LOOKUP.get(str(n).lower().strip()) for i, n in enumerate(names)}
        print(f"{src.name}: " + ", ".join(f"{n}->{NAMES[remap[i]] if remap[i] is not None else 'DROPPED'}"
                                          for i, n in enumerate(names)))
        for img in src.rglob("images/*"):
            if img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            lbl = img.parent.parent / "labels" / (img.stem + ".txt")
            lines = []
            if lbl.exists():
                for line in lbl.read_text().splitlines():
                    parts = line.split()
                    if len(parts) < 5 or remap.get(int(parts[0])) is None:
                        continue
                    xs, ys = [float(v) for v in parts[1::2]], [float(v) for v in parts[2::2]]
                    if len(parts) > 5:  # segmentation polygon -> bounding box
                        x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
                        box = [(x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1]
                    else:
                        box = [float(v) for v in parts[1:5]]
                    cid = remap[int(parts[0])]
                    counts[cid] += 1
                    lines.append(f"{cid} " + " ".join(f"{v:.5f}" for v in box))
            split = "valid" if n_img % every == 0 else "train"
            n_img += 1
            name = f"s{si}_{img.stem}"
            shutil.copy(img, OUT / split / "images" / (name + img.suffix.lower()))
            (OUT / split / "labels" / (name + ".txt")).write_text("\n".join(lines) + ("\n" if lines else ""))
    print("\nBoxes per class:")
    for n, c in zip(NAMES, counts):
        if c:
            print(f"  {n:15s} {c}")
    missing = [n for n, c in zip(NAMES[:15], counts[:15]) if c == 0]
    if missing:
        print(f"\nNo data yet for: {', '.join(missing)} (the model will not learn these)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    merge(sys.argv[1:])
