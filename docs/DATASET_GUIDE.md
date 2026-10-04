# How to collect the YOLO dataset

You need two kinds of images:
- **Public datasets** give you volume: hundreds of potholes, stairs, poles and so on.
- **Your own photos from the cane's camera** teach the model the real viewing angle, your campus, and Indian street conditions.

The two together work far better than either alone.

**Target:** at least 150 labelled boxes per class. Aim for 300 or more for the important classes: pothole, open_drain, stairs_down, curb and pole.

## Step 1: Download public datasets (30 min)

1. Create a free account at [Roboflow Universe](https://universe.roboflow.com).
2. Search for each class. Pick datasets with object detection, at least 300 images, and photos taken at street level rather than from drones or dashcams.

   | Search for | Our class |
   |---|---|
   | `pothole` | pothole |
   | `open manhole` / `drain` | open_drain |
   | `stairs` / `staircase` | stairs_up, stairs_down |
   | `curb` / `sidewalk` | curb |
   | `speed bump` | speed_breaker |
   | `pole` / `street light` | pole |
   | `auto rickshaw` / `indian vehicles` | auto_rickshaw |
   | `traffic cone` / `barricade` | barrier |

3. On each dataset, click **Download Dataset → YOLOv8 → show download code**, and copy the code snippet into the Colab notebook (Step 4). Also try Kaggle, for example "pothole detection", "Indian Driving Dataset" or "stairs detection".

## Step 2: Take your own photos from the cane (1–2 hours)

Mount the camera exactly as it will be used: about 90 cm high and tilted about 20° down. Then on the Pi:

```bash
cd Auralis-/pi && source venv/bin/activate
python capture.py --every 1 --only-moving
```

Walk slowly around campus and nearby streets. The script saves one photo per second into `pi/dataset_raw/`, and skips frames where you're standing still.

**What to photograph:**
- **Each obstacle from 0.5 m, 1 m, 2 m and 3 m,** walking towards it.
- **Different light:** morning, noon, evening and shadows. Shadows matter most, because a shadow looks a lot like a pothole.
- **Hard cases:**
  - dark patches and wet ground that are *not* potholes;
  - painted lines that are *not* curbs;
  - closed manhole covers versus open ones.
- **Stairs from both ends:** the top (stairs_down) and the bottom (stairs_up).
- **Head-level objects:** branches and signboards, which need the camera tilted up a bit.
- **Empty paths too,** about 10% of photos with nothing in them, so the model learns what "clear" looks like.

**Safety:** have a sighted friend walk with you, and photograph drop-offs from a safe distance.

**If you don't have the Pi with you,** record a video on your phone held at cane height. Then run `python capture.py --video walk.mp4` to extract frames from it.

## Step 3: Label your photos (1–2 hours for about 300 photos)

1. In Roboflow, create a project: **Object Detection**.
2. Upload `dataset_raw/`.
3. Add the class names **exactly** as in `ml/data.yaml`: `pothole`, `open_drain`, `stairs_down`, `curb`, `stairs_up`, `speed_breaker`, `pole`, `tree`, `wall`, `barrier`, `dustbin`, `branch`, `signboard`, `construction`, `auto_rickshaw`.
4. Draw tight boxes. Use Roboflow's *Label Assist* to speed this up after the first 50 photos.
5. **Generate** a version with no extra augmentation (our training adds its own), then **export as YOLOv8**.

You don't need to label people, cars, dogs and similar classes. The training step labels those automatically with a larger pre-trained model.

## Step 4: Train on Google Colab (about 1 hour, free GPU)

Open [`ml/AURALIS_train_yolo.ipynb`](../ml/AURALIS_train_yolo.ipynb) in Colab (File → Upload notebook). Set Runtime → Change runtime type → **T4 GPU**, and run the cells top to bottom. The notebook:
1. downloads your datasets;
2. merges them with consistent class names (`ml/merge_datasets.py`);
3. auto-labels people and vehicles;
4. trains and shows precision, recall and mAP for each class;
5. exports the model for the Pi 4.

Download `auralis_model.zip` at the end and unzip it into `pi/models/` on the Pi. On its next start, `server.py` picks up the new model automatically.

## Numbers to put in your paper

From the training output, record:
- **mAP@0.5 for each class, plus precision and recall.**
- **The confusion matrix** (`runs/auralis/confusion_matrix.png`), which shows how often a shadow gets mistaken for a pothole.
- **How many images** came from public data and how many from your own photos.
- **Optionally,** a model trained on public data only versus public + own photos. The difference shows why your own cane-view photos matter.
