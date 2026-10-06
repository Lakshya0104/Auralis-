#!/usr/bin/env bash
# One-time setup on Raspberry Pi OS 64-bit (Bookworm) for Pi 4 + camera + HC-SR04. Takes ~5-10 min.
#   cd Auralis-/pi && bash setup_pi.sh
set -e
cd "$(dirname "$0")"

sudo apt update
sudo apt install -y python3-picamera2 python3-opencv python3-gpiozero python3-lgpio python3-venv \
                    espeak-ng openssl

# venv that can still see the apt-installed camera / OpenCV / GPIO packages
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt

# The detector model (models/yolov8n.onnx) is already in the repo - nothing to download.
# Optional depth network (MiDaS). Off by default: it costs ~0.4 s per run on a Pi 4, and the front
# ultrasonic already gives exact distance in the classroom. To enable:
#   wget -O models/midas_small.onnx https://github.com/isl-org/MiDaS/releases/download/v2_1/model-small.onnx

espeak-ng "AURALIS setup complete" || true
echo
echo "Done. Test:   source venv/bin/activate && python check.py"
echo "Run:          source venv/bin/activate && python server.py"
