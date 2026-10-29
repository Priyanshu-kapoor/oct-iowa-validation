r"""
Final protocol (supervisor): 30 B-scans, each from a DIFFERENT eye (10301-10400), scored from a 21-scan volume centred on it.
This script writes tables\image_selection.csv: one row per eye with group, chosen B-scan, volume range, the rule used, run
order (batch of 10 runs) and whether it also gets a Cyst-configuration run.

The eye lists below are my visual judgement (no diagnosis spreadsheet exists; see screen_abnormal.py and the montages I looked
at): DISEASED = visible cysts, fluid, exudate or a lifted RPE within +/-60 B-scans of the centre. Only 9 such eyes exist in
the 98 usable eyes, so the set is 21 normal + 9 diseased, not 15 + 15. NORMAL = no visible pathology, clear foveal pit.
10333/10388 are the same scan stored twice and are not used.

Chosen B-scan (GT only, never IOWA):
  normal    foveal pit = B-scan with the minimum of the Gaussian-smoothed GT total retina thickness in the central area
            (B-scans 100-205, columns 77-228)
  diseased  most informative = the B-scan (92-212) with the largest GT abnormality; the measure is the cyst-band thickness
            (IPL-INL -> OPL-HFL) for eyes with cysts/fluid, the total retina thickness for the two eyes with a raised dome
            (10310, 10367)
Volume = chosen B-scan +/- 10 (21 B-scans). IOWA output is scored on the chosen B-scan only.

    python -I week2\scripts\make_selection.py
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

NORMAL = ["10307", "10320", "10330", "10399", "10314", "10398", "10372", "10340", "10323", "10343", "10377",
          "10395", "10334", "10366", "10315", "10304", "10357", "10396", "10363", "10383", "10356"]
DISEASED = {            # eye -> measure used for "most informative"
    "10380": "band", "10306": "band", "10325": "band", "10335": "band", "10302": "band", "10373": "band",
    "10317": "band", "10310": "total", "10367": "total",
}
CYST_EYES = ["10306", "10335", "10325", "10380"]          # side experiment: Configuration-Cyst.json
HALF = 10                                                   # 21 B-scans = centre +/- 10

screen = {r["eye"]: r for r in csv.DictReader(open(W.TABLES / "abnormal_screening.csv"))}
rows = []
for eye in NORMAL:
    c = int(screen[eye]["fovea_bscan"])
    rows.append(dict(eye=eye, group="normal", bscan=c, rule="foveal pit (min smoothed GT total thickness)",
                     central_offset=c - 152))
for eye, how in DISEASED.items():
    c = int(screen[eye][f"{how}_bscan"])
    rows.append(dict(eye=eye, group="diseased", bscan=c,
                     rule=("largest GT cyst-band thickness" if how == "band" else "largest GT total retina thickness (raised dome)"),
                     central_offset=c - 152))

# order the runs: interleave diseased and normal so that every batch of 10 holds both; 10306 and 10335 early
dis = sorted([r for r in rows if r["group"] == "diseased"], key=lambda r: (r["eye"] not in ("10306", "10335"), r["eye"]))
nor = sorted([r for r in rows if r["group"] == "normal"], key=lambda r: r["eye"])
order = []
while dis or nor:
    for _ in range(1):
        if dis:
            order.append(dis.pop(0))
    for _ in range(2):
        if nor:
            order.append(nor.pop(0))
# run 1 = pilot (10301_140-160); then the 30 eyes (runs 2-31); then the 4 cyst runs (32-35). Batches of 10 runs.
for i, r in enumerate(order):
    r["default_run_no"] = i + 2
    r["a"], r["b"] = r["bscan"] - HALF, r["bscan"] + HALF
    r["cyst_run"] = int(r["eye"] in CYST_EYES)
    r["volume"] = f"{r['eye']}_{r['a']}-{r['b']}"
cyst_sorted = [r for r in order if r["cyst_run"]]
for j, r in enumerate(cyst_sorted):
    r["cyst_run_no"] = 32 + j
for r in order:
    r.setdefault("cyst_run_no", "")
    r["batch_default"] = (r["default_run_no"] - 1) // 10 + 1
    r["batch_cyst"] = ((r["cyst_run_no"] - 1) // 10 + 1) if r["cyst_run_no"] != "" else ""
    assert 1 <= r["a"] and r["b"] <= 304, r

cols = ["default_run_no", "batch_default", "eye", "group", "bscan", "a", "b", "volume", "rule", "central_offset",
        "cyst_run", "cyst_run_no", "batch_cyst"]
out = W.TABLES / "image_selection.csv"
with open(out, "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=cols)
    wr.writeheader()
    wr.writerows([{k: r[k] for k in cols} for r in order])
print(f"saved {out}: {len(order)} eyes, {sum(r['group'] == 'normal' for r in order)} normal + "
      f"{sum(r['group'] == 'diseased' for r in order)} diseased")
for r in order:
    print(f"run {r['default_run_no']:2d} (batch {r['batch_default']})  {r['eye']} {r['group']:<8} B-scan {r['bscan']:3d} "
          f"(offset {r['central_offset']:+3d})  volume {r['a']}-{r['b']}  {'CYST too' if r['cyst_run'] else ''}")
print("pilot (run 1): 10301_140-160, centre B-scan 150 (compare 21 vs the 61-scan result)")
