r"""
Is a 21-scan volume enough? Evidence available BEFORE any 21-scan IOWA run: in the existing 61-scan result of eye 10301
(B-scans 120-180), B-scans near the two ends of the volume have 3D context on one side only. If their error is not larger
than that of central B-scans, limited context is not hurting IOWA at the 10-scan level used here.
Uses tables\scores_per_bscan.csv (10301, volume mode). Saves tables\edge_effect_10301.csv: mean RMSE (um) by distance of the
B-scan from the nearest volume end (0 = first/last B-scan; the centre of a 21-scan volume has 10 scans on each side).

    python -I week2\scripts\edge_effect.py
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

rows = [r for r in csv.DictReader(open(W.TABLES / "scores_per_bscan.csv"))
        if r["eye"] == "10301" and r["image_mode"] == "0" and r["config"] == "default" and r["variant"] == "original"
        and r["vol_a"] == "120" and r["vol_b"] == "180"]
if not rows:
    sys.exit("run score_runs.py first")
dist = np.array([min(int(r["bscan"]) - 120, 180 - int(r["bscan"])) for r in rows])
rmse = np.array([float(r["rmse_ALL"]) for r in rows])
bins = [(0, 0), (1, 2), (3, 5), (6, 9), (10, 14), (15, 30)]
out = []
for lo, hi in bins:
    m = (dist >= lo) & (dist <= hi)
    out.append(dict(distance_from_end=f"{lo}-{hi}" if lo != hi else f"{lo}", n_bscans=int(m.sum()),
                    mean_rmse_um=rmse[m].mean(), sd_rmse_um=rmse[m].std(ddof=1) if m.sum() > 1 else float("nan")))
with open(W.TABLES / "edge_effect_10301.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    wr.writeheader()
    wr.writerows([{k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()} for r in out])
print("10301, 61-scan volume: overall RMSE (um) by distance of the B-scan from the nearest end of the volume")
for r in out:
    print(f"  distance {r['distance_from_end']:>5}: n = {r['n_bscans']:2d}  mean RMSE {r['mean_rmse_um']:.2f}  SD {r['sd_rmse_um']:.2f}")
print("saved", W.TABLES / "edge_effect_10301.csv")
