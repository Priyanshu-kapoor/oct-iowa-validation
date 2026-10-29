"""
Gate (AGENTS.md rule 4): reproduce 3.84 um overall RMSE for eye 10301, B-scans 120-180, from the existing original-volume XML,
using the week-2 shared code (w2common). Writes tables\\gate_10301.csv. Exit code 1 if it does not match to 2 decimals.

    python -I week2\\scripts\\gate_check.py
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

XML = W.MHD / "10301_120-180_Surfaces_Retina-JEI-Final.xml"
EXPECTED = 3.84

pairs, info = W.iowa_boundaries(XML)
gt = W.gt_layers("10301", 120, 180)
assert pairs.shape == gt.shape, (pairs.shape, gt.shape)
um = info["um_depth"]

rows = []
for g, nm in enumerate(W.GT_BOUNDARIES):
    rows.append(dict(item=nm, kind="boundary RMSE (um)", value=np.sqrt((((pairs[g] - gt[g]) * um) ** 2).mean())))
all_rmse = np.sqrt((((pairs - gt) * um) ** 2).mean())
rows.append(dict(item="ALL", kind="boundary RMSE (um)", value=all_rmse))
for k, nm in enumerate(W.LAYER_NAMES):
    rows.append(dict(item=nm, kind="layer Dice", value=W.dice_band(gt[k], gt[k + 1], pairs[k], pairs[k + 1])))
rows.append(dict(item="whole retina", kind="layer Dice", value=W.dice_band(gt[0], gt[-1], pairs[0], pairs[-1])))

out = W.TABLES / "gate_10301.csv"
with open(out, "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=["item", "kind", "value"])
    wr.writeheader()
    for r in rows:
        wr.writerow(dict(r, value=f"{r['value']:.4f}"))

for r in rows:
    print(f"{r['kind']:<20}{r['item']:<22}{r['value']:.4f}")
ok = round(all_rmse, 2) == EXPECTED
print(f"\nGATE {'PASSED' if ok else 'FAILED'}: overall RMSE {all_rmse:.4f} um (expected {EXPECTED}); saved {out}")
sys.exit(0 if ok else 1)
