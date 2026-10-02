# Paper outline

**Working title:** *AURALIS: A Self-Mapping Smart Cane with Spatio-Temporal Hazard Memory and Neural Sensor Fusion for Risk-Aware Navigation of Visually Impaired Pedestrians*

## Claimed contributions
1. **Spatio-temporal hazard memory.** Risk is computed as `severity × (1 − e^(−count/2)) × 0.5^(age/7 days) × confidence`. It combines repeated evidence with temporal decay, and the user can confirm a hazard is gone.
2. **Infrastructure-free self-mapping.** The app builds a pedestrian graph from the user's own GPS breadcrumbs, so no map data is needed.
3. **Risk-aware A*** on that graph: `cost = len·(1+λ·risk)`.
4. **Neural late fusion** of ultrasonic, vision and memory features into a 4-level alert, designed for high recall on urgent cases.
5. A low-cost (< ₹2k) phone + ESP32 design with multilingual voice for Indian languages and an offline fallback.

## Sections
1. Introduction: the problem, plus why reactive-only canes fail on repeated routes.
2. Related work: ultrasonic canes, YOLO canes, risk-aware routing, crowdsourced accessibility maps. Point out the gap: none of them combine memory, decay, a self-built graph and fusion.
3. System architecture: the diagram from the README, hardware and BLE protocol.
4. Method: features (8), MLP, risk formula, graph building, A*.
5. Experiments (see below).
6. Results, limitations and future work: custom pothole YOLO, multi-user shared memory, learned risk.

## Experiments you can actually run in a day
| # | Experiment | Metric |
|---|---|---|
| E1 | Ultrasonic accuracy at 0.5/1/2/3 m, 10 readings each | mean abs error, std |
| E2 | Fusion MLP vs rule baseline on your labelled field rows (80/20 split) | accuracy, **urgent recall**, confusion matrix |
| E3 | Alert latency: obstacle appears → voice starts (slow-mo video) | ms |
| E4 | Memory pre-warning: walk a route 5× with a fixed obstacle; record the distance at which you are warned (reactive ≈1–2 m vs memory ≈15–25 m) | warning distance, lead time |
| E5 | Routing: shortest vs safest on 2 routes for λ = 0, 1, 2, 4, 8 | path length, accumulated risk |
| E6 | Decay: plot risk vs days for count = 1, 3, 5 (from formula) | figure |
| E7 | Multilingual: 5 listeners rate intelligibility per language (1–5) | mean score |

Bootstrap result to report (synthetic data, 4,000 test rows): **accuracy 0.895, urgent recall 0.939**.
