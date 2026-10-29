r"""
Task 2: outline-only export (boundary curves only, no OCT image), for GT and IOWA.
Per run it writes under week2\outlines\<tag>\ (<tag> = <eye>_<bscan> for the 30-image protocol, where only the chosen
B-scan is exported; <eye>_<a>-<b> for a volume; _cyst added for Cyst-configuration runs):
  gt\bscan_<n>.png, iowa\bscan_<n>.png   304 wide x 640 high, white background, one colour per boundary (n = absolute B-scan number)
  gt.npy, iowa.npy                        float32 (6, n_bscans, 304): depth in pixels (x 3.125 = um), first axis = boundary
  gt.csv, iowa.csv                        same numbers: columns eye,bscan,boundary,c1..c304
and one shared week2\outlines\legend.csv (boundary -> colour). Re-running overwrites the same files.

    python -I week2\scripts\t2_outlines.py [--no-png] [--thick N] [xml ...]
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

OUT = W.W2 / "outlines"
argv = sys.argv[1:]
thick = int(argv[argv.index("--thick") + 1]) if "--thick" in argv else 1
paths = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--thick")]
paths = paths or [x["path"] for x in W.find_results()]
if not paths:
    sys.exit("No Final XML found")


def draw(curves):
    """curves (6, 304) depth px -> BGR image 640 x 304, white background."""
    img = np.full((640, 304, 3), 255, np.uint8)
    xs = np.arange(304)
    for g in range(6):
        pts = np.stack([xs, np.round(curves[g])], axis=1).astype(np.int32).reshape(-1, 1, 2)
        rgb = W.BOUNDARY_RGB[g]
        cv2.polylines(img, [pts], False, (rgb[2], rgb[1], rgb[0]), thick, cv2.LINE_8)
    return img


def write_csv(path, eye, a, arr):
    with open(path, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["eye", "bscan", "boundary"] + [f"c{i + 1}" for i in range(304)])
        for k in range(arr.shape[1]):
            for g, nm in enumerate(W.GT_BOUNDARIES):
                wr.writerow([eye, a + k, nm] + [f"{v:.2f}" for v in arr[g, k]])


OUT.mkdir(parents=True, exist_ok=True)
with open(OUT / "legend.csv", "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["boundary_index", "boundary", "R", "G", "B"])
    for g, nm in enumerate(W.GT_BOUNDARIES):
        wr.writerow([g, nm, *W.BOUNDARY_RGB[g]])

for p in paths:
    r = W.load_run(p)
    d = OUT / W.run_tag(r)
    for src, arr in (("gt", r["gt"]), ("iowa", r["iowa"])):
        (d / src).mkdir(parents=True, exist_ok=True)
        np.save(d / f"{src}.npy", arr.astype(np.float32))
        write_csv(d / f"{src}.csv", r["eye"], r["a"], arr)
        if "--no-png" not in argv:
            for k in range(arr.shape[1]):
                cv2.imwrite(str(d / src / f"bscan_{r['a'] + k}.png"), draw(arr[:, k, :]))
    n = r["gt"].shape[1]
    print(f"{W.run_tag(r)}: {n} B-scan(s) -> {d}  (PNG {'skipped' if '--no-png' in argv else f'{2 * n} files'}, npy, csv)")
