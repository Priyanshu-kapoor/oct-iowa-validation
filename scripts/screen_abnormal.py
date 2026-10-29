r"""
Screening for the 30-image protocol: for every eye (10301-10400 minus the duplicate pair 10333/10388) and every B-scan 92-212
(+/- 60 around the centre, about +/- 0.6 mm), measure from the GROUND TRUTH only (never from IOWA, that would be circular):
  band_um    largest thickness of the IPL-INL -> OPL-HFL band (cysts/fluid enlarge it)           [um]
  total_um   largest total retina thickness (ILM -> OB_RPE)                                      [um]
  rpe_um     largest |OB_RPE - smooth curve|; the smooth curve is a 3rd-order polynomial fit of that B-scan [um]
             (an elevated / detached RPE bulges away from a smooth curve)
  fovea_bscan  B-scan of the foveal pit: minimum of the Gaussian-smoothed total thickness in the central area
Saves tables\abnormal_screening.csv (one row per eye: max over B-scans, and which B-scan gave it).
There is no diagnosis spreadsheet, so these numbers only HELP to find candidates; the final normal/diseased call is visual
(see make_selection.py).

    python -I week2\scripts\screen_abnormal.py
"""
import csv
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

LO, HI = 92, 212
DUPLICATES = {"10333", "10388"}          # same scan stored twice (identical images and GT)
cols = np.arange(304)
rows = []
for d in sorted(W.OCT_DIR.iterdir()):
    eye = d.name
    if eye in DUPLICATES:
        continue
    gt = W.gt_layers(eye)                                   # (6, 304, 304) all B-scans
    tot = (gt[5] - gt[0]) * W.UM_DEPTH
    band = (gt[2] - gt[1]) * W.UM_DEPTH
    rpe = np.zeros(304)
    for k in range(LO - 1, HI):
        c = np.polyfit(cols, gt[5, k], 3)
        rpe[k] = np.abs(gt[5, k] - np.polyval(c, cols)).max() * W.UM_DEPTH
    sl = slice(LO - 1, HI)
    sm = gaussian_filter(tot, 3)
    sub = sm[100:205, 76:228]
    fb = 100 + int(np.unravel_index(sub.argmin(), sub.shape)[0]) + 1       # 1-based B-scan number
    rows.append(dict(eye=eye,
                     band_um=band[sl].max(), band_bscan=LO + int(band[sl].max(axis=1).argmax()),
                     total_um=tot[sl].max(), total_bscan=LO + int(tot[sl].max(axis=1).argmax()),
                     rpe_um=rpe[sl].max(), rpe_bscan=LO + int(rpe[sl].argmax()),
                     fovea_bscan=fb, fovea_total_um=sm[fb - 1, 76:228].min()))

out = W.TABLES / "abnormal_screening.csv"
with open(out, "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    wr.writeheader()
    wr.writerows([{k: (f"{v:.1f}" if isinstance(v, float) else v) for k, v in r.items()} for r in rows])
print(f"saved {out} ({len(rows)} eyes)")

def z(key):
    v = np.array([r[key] for r in rows])
    return (v - np.median(v)) / (1.4826 * np.median(np.abs(v - np.median(v))) + 1e-9)

score = np.maximum.reduce([z("band_um"), z("total_um"), z("rpe_um")])
order = np.argsort(-score)
print("\nmost abnormal 45 (eye, band um @bscan, total um @bscan, rpe um @bscan, fovea bscan)")
for i in order[:45]:
    r = rows[i]
    print(f"  {r['eye']}  band {r['band_um']:5.0f}@{r['band_bscan']:3d}  total {r['total_um']:5.0f}@{r['total_bscan']:3d}  "
          f"rpe {r['rpe_um']:5.1f}@{r['rpe_bscan']:3d}  fovea {r['fovea_bscan']}")
print("\nmost regular 25")
for i in order[::-1][:25]:
    r = rows[i]
    print(f"  {r['eye']}  band {r['band_um']:5.0f}  total {r['total_um']:5.0f}  rpe {r['rpe_um']:5.1f}  fovea {r['fovea_bscan']}")
