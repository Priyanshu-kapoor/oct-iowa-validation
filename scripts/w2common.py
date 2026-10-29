"""
Shared helpers for the week-2 scripts (loading GT and IOWA surfaces, layer names, eye groups, run discovery).
Nothing here modifies the original data. Import with:  sys.path.insert(0, <this folder>); import w2common as W

Final protocol (supervisor): 30 B-scans from 30 different eyes. For each eye a 21-scan volume centred on the chosen B-scan is
segmented by IOWA and ONLY the chosen B-scan is scored ("image mode", see tables\\image_selection.csv). Runs that are not in
that table (the 61-scan 10301 test, full volumes, chunks) are scored over all their B-scans ("volume mode").
Default configuration runs live in mhd\\, Cyst-configuration runs in mhd_cyst\\<eye>\\.
"""
import csv
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import scipy.io as sio

ROOT = Path(r"C:\octa500")
GT_DIR = ROOT / "Label" / "GT_Layers"
OCT_DIR = ROOT / "OCTA_3mm" / "OCT"
MHD = ROOT / "mhd"
MHD_CYST = ROOT / "mhd_cyst"
W2 = ROOT / "week2"
TABLES = W2 / "tables"
FIGS = W2 / "figures"

UM_DEPTH = 2000.0 / 640        # 3.125 um per pixel (depth)
UM_SIDE = 3000.0 / 304         # 9.868 um per pixel (sideways)

# GT boundary g (0..5) <-> IOWA surface name; see CLAUDE.md (matched by minimum mean |diff|)
GT_BOUNDARIES = ["ILM", "IPL-INL", "OPL-HFL", "BMEIS", "IB_RPE", "OB_RPE"]
# Layer k lies between boundary k and k+1. Names follow the IOWA surface names used for the two edges.
LAYER_NAMES = ["ILM->IPL-INL", "IPL-INL->OPL-HFL", "OPL-HFL->BMEIS", "BMEIS->IB_RPE", "IB_RPE->OB_RPE"]
TOTAL = "Total retina (ILM->OB_RPE)"

# Colours for outline images (RGB 0-255), one per boundary
BOUNDARY_RGB = [(214, 39, 40), (255, 127, 14), (44, 160, 44), (31, 119, 180), (148, 103, 189), (140, 86, 75)]

DISEASED_KNOWN = ["10306", "10335"]
FULL_VOLUMES = {"normal": "10387", "diseased": "10335"}          # topographic maps (separate from the 30 images)
PILOT = ("10301", 140, 160, 150)                                  # eye, a, b, centre: times a run, compares 21 vs 61 scans


# ---------------------------------------------------------------- selection (30 images)
def selection():
    """tables\\image_selection.csv as {(eye, a, b): row}; empty dict if the table does not exist yet."""
    p = TABLES / "image_selection.csv"
    if not p.exists():
        return {}
    with open(p, newline="") as f:
        return {(r["eye"], int(r["a"]), int(r["b"])): r for r in csv.DictReader(f)}


def groups():
    """{'normal': [eyes], 'diseased': [eyes]} from the selection table."""
    g = {"normal": [], "diseased": []}
    for r in selection().values():
        g[r["group"]].append(r["eye"])
    return g


def group_of(eye):
    for g, eyes in groups().items():
        if eye in eyes:
            return g
    return "other"      # e.g. 10301's 61-scan test volume, full volumes: not one of the 30 images


def run_tag(r):
    """File-name tag of a run: <eye>_<bscan> (image) or <eye>_<a>-<b> (volume), plus _cyst for the Cyst configuration."""
    base = f"{r['eye']}_{r['a']}" if r["a"] == r["b"] else f"{r['eye']}_{r['a']}-{r['b']}"
    return base + ("_cyst" if r.get("config") == "cyst" else "")


def gt_layers(eye, a=1, b=304):
    """GT boundaries in depth pixels, shape (6, n_bscans, 304), for 1-based inclusive B-scan range a..b."""
    lay = sio.loadmat(GT_DIR / f"{eye}.mat")["Layer"].astype(float)
    return lay[:, a - 1:b, :]


def parse_name(path):
    """'<eye>_<a>-<b>_...' or '<eye>_...' -> (eye, a, b, variant)."""
    name = Path(path).name
    m = re.match(r"(\d+)_(\d+)-(\d+)", name)
    if m:
        eye, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        variant = name.split("_Surfaces")[0][len(m.group(0)):].lstrip("_") or "original"
        return eye, a, b, variant
    m = re.match(r"(\d+)", name)
    if m:
        return m.group(1), 1, None, (name.split("_Surfaces")[0][len(m.group(1)):].lstrip("_") or "original")
    return None


def read_iowa(path):
    """Read an IOWA Surfaces XML -> dict(names, surf (12, nB, 304) depth px, um_depth, n_undefined)."""
    root = ET.parse(path).getroot()
    names = [s.find("name").text.split("(")[-1].rstrip(")") for s in root.findall("surface")]
    surf = np.array([[[float(y.text) for y in bs.findall("y")] for bs in s.findall("bscan")]
                     for s in root.findall("surface")])
    um = float(root.find("scan_characteristics/voxel_size/y").text) * 1000.0
    und = root.find("undefined_region")
    return dict(names=names, surf=surf, um_depth=um, n_undefined=len(list(und)) if und is not None else 0)


def iowa_boundaries(path):
    """The 6 IOWA surfaces that correspond to the GT boundaries, shape (6, nB, 304) in depth pixels, + info."""
    d = read_iowa(path)
    cols = [d["names"].index(nm) for nm in GT_BOUNDARIES]
    return d["surf"][cols], d


def thickness_um(bound, um_depth=UM_DEPTH):
    """(6, ...) boundaries in PIXELS -> (6, ...) thickness: 5 layers then total retina, in um."""
    layers = np.diff(bound, axis=0) * um_depth
    total = (bound[-1] - bound[0]) * um_depth
    return np.concatenate([layers, total[None]], axis=0)


def quality_mask(bound):
    """True where IOWA output is usable: finite and boundaries in non-decreasing depth order (no crossing).
    Shape (nB, 304). The XML <undefined_region> list is counted separately (its format is unknown, empty so far)."""
    ok = np.isfinite(bound).all(axis=0)
    ok &= (np.diff(bound, axis=0) >= 0).all(axis=0)
    return ok


def dice_band(a0, a1, b0, b1):
    inter = np.clip(np.minimum(a1, b1) - np.maximum(a0, b0), 0, None).sum()
    return 2 * inter / ((a1 - a0).sum() + (b1 - b0).sum())


# ---------------------------------------------------------------- runs (one IOWA result file = one run)
def find_results(kind="Final", pattern=None, variants=("original",)):
    """All IOWA result XMLs under mhd\\ (Default config) and mhd_cyst\\ (Cyst config), sub-folders included, but not any
    folder starting with _old. Returns dicts {path, eye, a, b, variant, config}. variants=None keeps denoised variants too."""
    pat = pattern or f"*_Surfaces_Retina-JEI-{kind}.xml"
    out = []
    for root, config in ((MHD, "default"), (MHD_CYST, "cyst")):
        if not root.exists():
            continue
        for p in sorted(root.rglob(pat)):
            if any(part.startswith("_old") for part in p.relative_to(root).parts[:-1]):
                continue
            info = parse_name(p)
            if info is None:
                continue
            eye, a, b, variant = info
            if variants is not None and variant not in variants:
                continue
            out.append(dict(path=p, eye=eye, a=a, b=b, variant=variant, config=config))
    return out


def config_of(path):
    return "cyst" if MHD_CYST in Path(path).parents else "default"


def load_run(path, volume=False):
    """One IOWA result vs GT. volume=True keeps every B-scan of the file even for a 30-image volume (used to stitch maps).
    Image mode (volume listed in image_selection.csv, or the pilot): arrays are cut down to the chosen B-scan, so a = b = that
    B-scan and only it is scored. Volume mode (anything else): all B-scans of the file (range from the file name; a full volume
    has b from the XML size).
    Returns dict: eye, a, b, vol_a, vol_b, variant, config, group, image_mode, gt (6,n,304) px, iowa (6,n,304) px,
    um (depth um/px), n_undefined, nudge (True if a NudgeLines file sits beside the XML = manual edits possible)."""
    path = Path(path)
    eye, a, b, variant = parse_name(path)
    iowa, info = iowa_boundaries(path)
    n = iowa.shape[1]
    if b is None:
        b = a + n - 1
    gt = gt_layers(eye, a, b)
    if gt.shape != iowa.shape:
        raise ValueError(f"{path.name}: GT {gt.shape} vs IOWA {iowa.shape}")
    sel = selection().get((eye, a, b))
    centre = int(sel["bscan"]) if sel else (PILOT[3] if (eye, a, b) == PILOT[:3] else None)
    image_mode = centre is not None and not volume
    vol_a, vol_b = a, b
    if image_mode:
        k = centre - a
        gt, iowa, a, b = gt[:, k:k + 1, :], iowa[:, k:k + 1, :], centre, centre
    stem = path.name.split("_Surfaces")[0]
    nudge = any(path.parent.glob(f"{stem}_NudgeLines_*.xml"))
    return dict(path=path, eye=eye, a=a, b=b, vol_a=vol_a, vol_b=vol_b, variant=variant, config=config_of(path),
                group="pilot" if (eye, vol_a, vol_b) == PILOT[:3] else group_of(eye), image_mode=int(image_mode), gt=gt, iowa=iowa, um=info["um_depth"],
                n_undefined=info["n_undefined"], nudge=nudge)


def upsert_csv(path, new_rows, key_cols):
    """Insert/replace rows in a CSV keyed by key_cols, then write atomically (temp file + replace), so re-runs never
    duplicate rows and a crash never leaves a half-written table. Rows are dicts of strings/numbers."""
    import os
    path = Path(path)
    old = []
    if path.exists():
        with open(path, newline="") as f:
            old = list(csv.DictReader(f))
    cols = list(new_rows[0].keys()) if new_rows else (list(old[0].keys()) if old else [])
    if old and set(old[0].keys()) != set(cols):
        raise ValueError(f"{path.name}: columns changed ({sorted(set(old[0]) ^ set(cols))}); delete the table and re-run")
    keys = {tuple(str(r[k]) for k in key_cols) for r in new_rows}
    rows = [r for r in old if tuple(str(r[k]) for k in key_cols) not in keys] + [
        {k: (f"{v:.4f}" if isinstance(v, (float, np.floating)) else str(v)) for k, v in r.items()} for r in new_rows]
    rows.sort(key=lambda r: tuple((int(r[k]) if str(r[k]).isdigit() else str(r[k])) for k in key_cols))
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        wr.writerows(rows)
    os.replace(tmp, path)


def stitch_chunks(parts, n_total=304):
    """Join overlapping chunk results of one eye into one full volume.
    parts = [(a, b, boundaries (6, nB, 304) px), ...] with 1-based inclusive ranges. Overlapping B-scans are averaged.
    Returns (full (6, n_total, 304) with NaN where no chunk covers, overlap_mean_abs_diff_px or None)."""
    acc = np.zeros((6, n_total, 304))
    cnt = np.zeros(n_total)
    first = {}
    diffs = []
    for a, b, arr in parts:
        for k in range(arr.shape[1]):
            i = a - 1 + k
            if i in first:
                diffs.append(np.abs(first[i] - arr[:, k, :]).mean())
            else:
                first[i] = arr[:, k, :]
            acc[:, i, :] += arr[:, k, :]
            cnt[i] += 1
    full = np.where(cnt[None, :, None] > 0, acc / np.maximum(cnt, 1)[None, :, None], np.nan)
    return full, (float(np.mean(diffs)) if diffs else None)
