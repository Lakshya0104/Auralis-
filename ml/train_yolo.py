"""Neural network 1: fine-tune YOLOv8n on the AURALIS obstacle classes. Run on Google Colab (free GPU).

Steps:
  1. Get images (Roboflow Universe / Kaggle pothole, stairs, drain, pole datasets + 100-200 of your own
     photos taken from cane height). Put them in YOLO format under datasets/auralis/{train,valid}/{images,labels}.
     Label ids must follow the `names` list in ml/data.yaml (remap downloaded datasets to these ids).
  2. python ml/train_yolo.py pseudo   # adds person / car / dog ... boxes using the stock COCO model,
                                      # so the new model does not forget those classes
  3. python ml/train_yolo.py train [epochs]   # ~1 h on a Colab T4 for ~2k images
  4. python ml/train_yolo.py export   # writes pi/models/auralis_yolo.pt + NCNN version for the Pi 4

Colab:  !pip install ultralytics  then  !git clone <this repo> && cd <repo> && run the steps.
"""
import pathlib
import shutil
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "ml" / "data.yaml"
NAMES = yaml.safe_load(DATA.read_text())["names"]
# COCO ids of the classes we keep from the stock model -> our ids
COCO_KEEP = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck", 16: "dog", 19: "cow",
             13: "bench", 56: "chair", 10: "fire hydrant", 11: "stop sign", 58: "potted plant"}


def pseudo_label():
    """Add stock-YOLO detections of COCO classes to every label file (keeps existing custom labels)."""
    from ultralytics import YOLO
    model = YOLO("yolov8m.pt")  # a bigger teacher model gives cleaner pseudo-labels
    our_id = {n: i for i, n in enumerate(NAMES)}
    data_root = ROOT / yaml.safe_load(DATA.read_text())["path"]
    for split in ("train", "valid"):
        img_dir = data_root / split / "images"
        for img in sorted(img_dir.glob("*")):
            lbl = data_root / split / "labels" / (img.stem + ".txt")
            lines = lbl.read_text().splitlines() if lbl.exists() else []
            r = model.predict(str(img), conf=0.5, verbose=False)[0]
            for b in r.boxes:
                c = int(b.cls)
                if c in COCO_KEEP:
                    x, y, w, h = b.xywhn[0].tolist()
                    lines.append(f"{our_id[COCO_KEEP[c]]} {x:.5f} {y:.5f} {w:.5f} {h:.5f}")
            lbl.parent.mkdir(parents=True, exist_ok=True)
            lbl.write_text("\n".join(lines) + "\n")
        print(f"pseudo-labelled {split}")


def resolved_data_yaml():
    """data.yaml with an absolute dataset path (Ultralytics otherwise looks in its own datasets folder)."""
    cfg = yaml.safe_load(DATA.read_text())
    cfg["path"] = str(ROOT / cfg["path"])
    out = ROOT / "runs" / "data_resolved.yaml"
    out.parent.mkdir(exist_ok=True)
    out.write_text(yaml.safe_dump(cfg, allow_unicode=True))
    return str(out)


def train(epochs=60):
    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")  # start from COCO weights (transfer learning)
    model.train(data=resolved_data_yaml(), imgsz=320, epochs=int(epochs), batch=32, patience=15,
                # augmentations that match cane footage: brightness, blur from walking, small rotations
                hsv_v=0.5, degrees=8, translate=0.1, scale=0.4, fliplr=0.5, mosaic=1.0,
                project=str(ROOT / "runs"), name="auralis", exist_ok=True)
    metrics = model.val()
    print(f"mAP50={metrics.box.map50:.3f}  mAP50-95={metrics.box.map:.3f}")


def export():
    from ultralytics import YOLO
    best = ROOT / "runs" / "auralis" / "weights" / "best.pt"
    dest = ROOT / "pi" / "models"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(best, dest / "auralis_yolo.pt")
    YOLO(str(dest / "auralis_yolo.pt")).export(format="ncnn", imgsz=320)
    print(f"exported to {dest}")


if __name__ == "__main__":
    {"pseudo": pseudo_label, "train": train, "export": export}[sys.argv[1]](*sys.argv[2:])
