r"""
Task 3: topographic (en-face) maps from the stacked B-scans of one eye.
x = column (mm), y = B-scan (mm), value = depth below the top of the image (um) for each of the 6 boundaries, or thickness (um)
for each of the 5 layers and the total retina. For GT and IOWA, plus IOWA - GT.
Per run it writes, in week2\maps\<eye>_<a>-<b>\ :
  heatmap_<name>.png   three panels: GT | IOWA | IOWA - GT (grey = not usable, see below)
  surface_<name>.png   3D surface of GT and IOWA (depth maps have the z axis flipped so deeper = lower)
  depth_gt.npy, depth_iowa.npy (6, n_bscans, 304) um;  thickness_gt.npy, thickness_iowa.npy (6, n_bscans, 304) um
  mask_iowa_invalid.npy, mask_gt_invalid.npy (n_bscans, 304) bool
Not usable (NaN, grey) = a boundary missing, or boundaries crossing / out of order at that column (IOWA or GT), or no
chunk covers that B-scan. tables\map_coverage.csv lists the share of masked columns per run.

    python -I week2\scripts\t3_maps.py [xml ...]
    python -I week2\scripts\t3_maps.py --stitch xml_chunk1 xml_chunk2 ...   # overlapping chunks of ONE full volume
Chunks (only if IOWA runs out of memory on 304 B-scans): e.g. B-scans 1-80, 77-156, 153-232, 229-304 (4-scan overlap), made
with step3_make_mhd.py --range a b; overlapping B-scans are averaged and the disagreement is saved in tables\chunk_overlap.csv.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).parent))
import w2common as W

OUT = W.W2 / "maps"
SIDE_MM = 3.0 / 304
SEQ = "Blues"                                                    # one hue, light -> dark (magnitude)
DIV = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#ececea", "#eb6834"])   # IOWA < GT blue, IOWA > GT orange
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": MUTED})

NAMES = [("depth", i, f"{nm} depth") for i, nm in enumerate(W.GT_BOUNDARIES)] + \
        [("thickness", i, nm) for i, nm in enumerate(W.LAYER_NAMES + [W.TOTAL])]


def invalid_mask(b):
    """(6, nB, 304) boundaries in px -> (nB, 304) True where unusable (missing or out of order)."""
    return ~W.quality_mask(b)


def stitched_run(runs):
    """Several chunk runs of one eye -> one run dict covering 1..304 (IOWA stitched, GT read directly)."""
    eye = runs[0]["eye"]
    full, ov = W.stitch_chunks([(r["a"], r["b"], r["iowa"]) for r in runs])
    gt = W.gt_layers(eye, 1, 304)
    W.upsert_csv(W.TABLES / "chunk_overlap.csv",
                 [dict(eye=eye, chunks=";".join(f"{r['a']}-{r['b']}" for r in runs),
                       overlap_mean_abs_diff_um=(ov * runs[0]["um"]) if ov is not None else "")], ["eye"])
    r0 = dict(runs[0])
    r0.update(a=1, b=304, gt=gt, iowa=full, variant="original")
    return r0


def maps_for(r):
    gt, io, um = r["gt"], r["iowa"], r["um"]
    bad_i, bad_g = invalid_mask(io), invalid_mask(gt)
    # NaN wherever any boundary of that column is unusable (strict: a thickness needs both of its boundaries)
    pg = np.where(bad_g[None], np.nan, gt)           # depth in pixels, masked
    pi = np.where(bad_i[None], np.nan, io)
    return dict(depth_gt=pg * W.UM_DEPTH, depth_iowa=pi * um, thickness_gt=W.thickness_um(pg, W.UM_DEPTH),
                thickness_iowa=W.thickness_um(pi, um), mask_gt_invalid=bad_g, mask_iowa_invalid=bad_i)


def heatmap(m, kind, i, label, title, a, path):
    g, p = m[f"{kind}_gt"][i], m[f"{kind}_iowa"][i]
    d = p - g
    y0, y1 = (a - 1) * SIDE_MM, (a - 1 + g.shape[0]) * SIDE_MM
    both = np.concatenate([g[np.isfinite(g)], p[np.isfinite(p)]])
    lo, hi = (np.percentile(both, [1, 99]) if both.size else (0, 1))
    dl = max(np.nanpercentile(np.abs(d), 99) if np.isfinite(d).any() else 1.0, 1.0)
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6 if g.shape[0] < 100 else 4.6), constrained_layout=True)
    for k, (arr, ttl, cm, vl) in enumerate([(g, "GT", SEQ, (lo, hi)), (p, "IOWA", SEQ, (lo, hi)), (d, "IOWA - GT", DIV, (-dl, dl))]):
        cmap = (plt.get_cmap(cm) if isinstance(cm, str) else cm).copy()
        cmap.set_bad("#bdbdb8")
        im = ax[k].imshow(np.ma.masked_invalid(arr), cmap=cmap, vmin=vl[0], vmax=vl[1], aspect="equal",
                          extent=(0, 304 * SIDE_MM, y1, y0), interpolation="nearest")
        ax[k].set_title(ttl)
        ax[k].set_xlabel("Column position (mm)")
        if k == 0:
            ax[k].set_ylabel("B-scan position (mm)")
        fig.colorbar(im, ax=ax[k], shrink=0.85).set_label("um" if k < 2 else "difference (um)")
    fig.suptitle(f"{title} - {label}   (grey = not usable)", fontsize=10)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def surface(m, kind, i, label, title, a, path):
    fig = plt.figure(figsize=(12, 4.8))
    ny, nx = m[f"{kind}_gt"][i].shape
    X, Y = np.meshgrid(np.arange(nx) * SIDE_MM, (a - 1 + np.arange(ny)) * SIDE_MM)
    allv = np.concatenate([m[f"{kind}_{s}"][i][np.isfinite(m[f"{kind}_{s}"][i])] for s in ("gt", "iowa")])
    lo, hi = (allv.min(), allv.max()) if allv.size else (0, 1)
    st = max(1, ny // 80), max(1, nx // 80)
    for k, src in enumerate(("gt", "iowa")):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        Z = m[f"{kind}_{src}"][i]
        ax.plot_surface(X, Y, np.ma.masked_invalid(Z), cmap=SEQ, vmin=lo, vmax=hi, rstride=st[0], cstride=st[1],
                        linewidth=0, antialiased=False)
        ax.set_zlim(hi, lo) if kind == "depth" else ax.set_zlim(lo, hi)
        ax.set_xlabel("Column (mm)")
        ax.set_ylabel("B-scan (mm)")
        ax.set_zlabel("Depth (um)" if kind == "depth" else "Thickness (um)")
        ax.set_title("GT" if src == "gt" else "IOWA", fontsize=10)
        ax.view_init(elev=28, azim=-60)
    fig.suptitle(f"{title} - {label}", fontsize=10)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def render(r):
    d = OUT / W.run_tag(r)
    d.mkdir(parents=True, exist_ok=True)
    grp = {"other": "61-scan test volume, not one of the 30 images"}.get(r["group"], r["group"])
    title = f"Eye {r['eye']}, B-scans {r['a']}-{r['b']} ({grp}{', Cyst config' if r['config'] == 'cyst' else ''})"
    m = maps_for(r)
    for key, arr in m.items():
        np.save(d / f"{key}.npy", arr if arr.dtype == bool else arr.astype(np.float32))
    for kind, i, label in NAMES:
        tag = f"{kind}_{i}_{label.split(' (')[0].replace('->', '_to_').replace(' ', '_')}"
        heatmap(m, kind, i, label, title, r["a"], d / f"heatmap_{tag}.png")
        surface(m, kind, i, label, title, r["a"], d / f"surface_{tag}.png")
    seg = np.isfinite(r["iowa"]).any(axis=(0, 2))                    # B-scans that IOWA actually segmented
    idx = np.flatnonzero(seg)
    runs_ = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1) if idx.size else []
    ranges = ";".join(f"{r['a'] + int(q[0])}-{r['a'] + int(q[-1])}" for q in runs_)
    used = m["mask_iowa_invalid"][seg]
    W.upsert_csv(W.TABLES / "map_coverage.csv",
                 [dict(eye=r["eye"], a=r["a"], b=r["b"], variant=r["variant"], iowa_bscan_ranges=ranges,
                       iowa_bscans=int(seg.sum()), map_bscans=int(seg.size),
                       iowa_share_of_304_pct=100 * seg.sum() / 304,
                       iowa_y_from_mm=(r["a"] - 1 + idx[0]) * SIDE_MM if idx.size else "",
                       iowa_y_to_mm=(r["a"] + idx[-1]) * SIDE_MM if idx.size else "",
                       iowa_unusable_pct_of_segmented=100 * used.mean() if used.size else "",
                       gt_invalid_pct=100 * m["mask_gt_invalid"].mean(),
                       undefined_regions_in_xml=r["n_undefined"])], ["eye", "a", "b", "variant"])
    print(f"{r['eye']} {r['a']}-{r['b']}: {2 * len(NAMES)} PNG + 6 npy -> {d}   unusable columns: IOWA "
          f"{100 * m['mask_iowa_invalid'].mean():.2f}% (of the map), GT {100 * m['mask_gt_invalid'].mean():.2f}%; IOWA B-scans {ranges}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    runs = [W.load_run(p, volume="--stitch" in sys.argv) for p in (args or [x["path"] for x in W.find_results()])]
    if not runs:
        sys.exit("No Final XML found")
    if "--stitch" in sys.argv:
        runs = [stitched_run(runs)]
    for r in runs:
        if r["image_mode"]:
            print(f"[skip] {W.run_tag(r)}: a single B-scan (30-image protocol) has no map; maps need a volume")
            continue
        render(r)
