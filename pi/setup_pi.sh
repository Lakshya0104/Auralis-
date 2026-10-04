#!/usr/bin/env bash
# One-time setup on Raspberry Pi OS (64-bit, Bookworm) for a Pi 4 + camera + HC-SR04.
#   cd auralis-/pi && bash setup_pi.sh
set -e
cd "$(dirname "$0")"

sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-gpiozero python3-lgpio python3-venv openssl

# venv that can still see the apt-installed camera / GPIO packages
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p models
# Stock COCO model until your custom model is trained (ml/train_yolo.py); NCNN is ~2x faster on a Pi 4
if [ ! -d models/yolov8n_ncnn_model ]; then
  (cd models && python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='ncnn', imgsz=320)")
fi
# Neural network 2: MiDaS small depth model (optional; geometry still works without it)
if [ ! -f models/midas_small.onnx ]; then
  wget -q -O models/midas_small.onnx https://github.com/isl-org/MiDaS/releases/download/v2_1/model-small.onnx \
    || { rm -f models/midas_small.onnx; echo "MiDaS download failed - continuing without depth network"; }
fi
echo "Done. Start with:  source venv/bin/activate && python server.py"
