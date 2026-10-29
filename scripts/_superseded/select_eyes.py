"""
Screen all 100 available eyes (10301-10400) for the 8-eye protocol, from GT + artifact-detector flags ONLY (never from IOWA
output, which would be circular). No diagnosis spreadsheet exists on this machine, so "normal-looking" / "diseased-looking"
is a screening judgement, not a clinical label. Known diseased (AGENTS.md): 10306, 10335.

Per eye, over B-scans 120-180 (the protocol window):
  mean_total_um   mean total retina thickness (GT ILM -> OB_RPE)
  sd_total_um     SD of total thickness over all columns/B-scans (large = uneven retina)
  rough_um        mean |second difference| of the GT ILM along the B-scan, in um (large = bumpy surface)
  max_layer_um    largest GT thickness of the IPL-INL -> OPL-HFL band (cysts/edema enlarge the inner retina)
  flags_120_180   number of detector flags (motion/shadow/edge/low_signal) among B-scans 120-180
Saves tables\\eye_screening.csv.

    python -I week2\\scripts\\select_eyes.py
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

flags = {}
with open(W.ROOT / "out" / "artifacts_flags.csv") as f:
    for r in csv.DictReader(f):
        b = int(r["bscan"])
        if 120 <= b <= 180 and any(int(r[k]) for k in ("low_signal", "motion", "shadow", "edge")):
            flags[r["eye"]] = flags.get(r["eye"], 0) + 1

rows = []
for d in sorted(W.OCT_DIR.iterdir()):
    eye = d.name
    gt = W.gt_layers(eye, 120, 180)
    total = (gt[5] - gt[0]) * W.UM_DEPTH
    ilm = gt[0] * W.UM_DEPTH
    rough = np.abs(np.diff(ilm, n=2, axis=1)).mean()
    band = (gt[2] - gt[1]) * W.UM_DEPTH
    rows.append(dict(eye=eye, mean_total_um=total.mean(), sd_total_um=total.std(), rough_um=rough,
                     max_layer_um=band.max(), flags_120_180=flags.get(eye, 0)))

out = W.TABLES / "eye_screening.csv"
with open(out, "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    wr.writeheader()
    for r in rows:
        wr.writerow({k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in r.items()})
print(f"saved {out} ({len(rows)} eyes)")

# robust z-score of the unevenness measures, to rank eyes from most regular to most irregular
cols = ["sd_total_um", "rough_um", "max_layer_um"]
z = np.zeros(len(rows))
for c in cols:
    v = np.array([r[c] for r in rows])
    z += (v - np.median(v)) / (1.4826 * np.median(np.abs(v - np.median(v))) + 1e-9)
order = np.argsort(z)
print("\nmost regular 12 (normal-looking candidates)  eye, sd_total, rough, max_band, flags")
for i in order[:12]:
    r = rows[i]
    print(f"  {r['eye']}  {r['sd_total_um']:6.1f} {r['rough_um']:6.2f} {r['max_layer_um']:6.1f} {r['flags_120_180']:3d}")
print("most irregular 12 (diseased-looking candidates)")
for i in order[::-1][:12]:
    r = rows[i]
    print(f"  {r['eye']}  {r['sd_total_um']:6.1f} {r['rough_um']:6.2f} {r['max_layer_um']:6.1f} {r['flags_120_180']:3d}")
for e in W.DISEASED_KNOWN:
    i = [r["eye"] for r in rows].index(e)
    print(f"known diseased {e}: rank {list(order[::-1]).index(i) + 1} of {len(rows)} (1 = most irregular)")
