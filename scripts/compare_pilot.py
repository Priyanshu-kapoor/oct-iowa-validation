r"""
Pilot check (run 1): does IOWA on 21 B-scans give the same answer as on 61 B-scans for the SAME B-scan?
Eye 10301, B-scan 150. 61-scan result = mhd\10301_120-180_Surfaces_Retina-JEI-Final.xml (existing, Default config),
21-scan result = mhd\10301_140-160_Surfaces_Retina-JEI-Final.xml (new). Both are scored against GT on B-scan 150, and the two
IOWA outputs are compared with each other. Saves tables\pilot_21_vs_61.csv.

Working criterion (mine, to be confirmed by the supervisor): 21 scans are fine if the overall RMSE of the 21-scan run is
within 0.5 um of the 61-scan run AND the two IOWA outputs differ by less than 1 um on average. Otherwise propose a larger volume.

    python -I week2\scripts\compare_pilot.py
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

C = 150
x61 = W.MHD / "10301_120-180_Surfaces_Retina-JEI-Final.xml"
x21 = W.MHD / "10301_140-160_Surfaces_Retina-JEI-Final.xml"
if not x21.exists():
    sys.exit(f"pilot result not found yet: {x21.name} (run it in OCTExplorer first)")
p61, i61 = W.iowa_boundaries(x61)
p21, i21 = W.iowa_boundaries(x21)
a61 = p61[:, C - 120, :]
a21 = p21[:, C - 140, :]
gt = W.gt_layers("10301", C, C)[:, 0, :]
um = i61["um_depth"]
rows = []
for g, nm in enumerate(W.GT_BOUNDARIES + ["ALL"]):
    s = slice(g, g + 1) if g < 6 else slice(0, 6)
    r61 = np.sqrt((((a61[s] - gt[s]) * um) ** 2).mean())
    r21 = np.sqrt((((a21[s] - gt[s]) * um) ** 2).mean())
    d = np.abs(a21[s] - a61[s]).mean() * um
    rows.append(dict(boundary=nm, rmse_61scan_um=r61, rmse_21scan_um=r21, rmse_change_um=r21 - r61, mean_abs_diff_between_runs_um=d))
with open(W.TABLES / "pilot_21_vs_61.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    wr.writeheader()
    wr.writerows([{k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()} for r in rows])
print(f"10301, B-scan {C}: 61-scan vs 21-scan IOWA run, error against GT (um)")
for r in rows:
    print(f"  {r['boundary']:<8} 61-scan {r['rmse_61scan_um']:5.2f}   21-scan {r['rmse_21scan_um']:5.2f}   "
          f"change {r['rmse_change_um']:+5.2f}   runs differ by {r['mean_abs_diff_between_runs_um']:.2f}")
al = rows[-1]
ok = abs(al["rmse_change_um"]) <= 0.5 and al["mean_abs_diff_between_runs_um"] < 1.0
print("\nVERDICT by the working criterion:", "21 scans are fine" if ok else "21 scans differ from 61 scans: propose a larger volume (e.g. 41 or 61)")
print("saved", W.TABLES / "pilot_21_vs_61.csv")
